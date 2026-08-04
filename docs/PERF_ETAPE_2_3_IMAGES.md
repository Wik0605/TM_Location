# Étapes 2 & 3 — Nettoyage Tailwind + Optimisation des images

Date : 2026-08-04

## Étape 2 — Nettoyage `tailwind.config.js`

L'audit initial pensait que Tailwind n'était pas purgé (`dist.css` estimé à 2,45 MB).
Vérification faite : `dist.css` fait **62 KB**, déjà propre. Le projet utilise
Tailwind **v4** avec `@import "tailwindcss"` dans `static/css/src.css`, qui purge
automatiquement en scannant les templates.

**Action réalisée :** suppression de `tailwind.config.js` (config v3 obsolète,
sans effet réel en v4, source de confusion).

## Étape 3 — Optimisation des images (le vrai gros gain)

### Problème

Dossier `static/uploads/` = **41 MB**, avec des PNG jusqu'à 6,4 MB par photo.
Sur mobile 3G, ça peut représenter 30+ secondes de chargement pour une seule
fiche voiture. Aucun lazy-load, aucun format moderne (WebP), aucune limite
de taille à l'upload.

### Ce qui a été fait

#### 1. `requirements.txt`

Ajout de **Pillow ≥ 10** pour la conversion et le redimensionnement.

#### 2. `scripts/optimize_images.py` (nouveau)

Script one-shot qui parcourt `static/uploads/` et, pour chaque PNG/JPG :

- Redimensionne à **1280 px de large max** (garde les proportions).
- Génère une version `.webp` **qualité 82** à côté de l'original.
- Conserve l'original comme fallback (`<picture>` s'en sert).
- Idempotent : re-exécutable, saute les `.webp` déjà présents.

Gain typique : **80-90 %** sur les PNG haute résolution.

#### 3. `app/routers/admin_cars.py` — upload optimisé

Nouvelle fonction `_save_optimized_image()` :

- Toutes les nouvelles photos uploadées par l'admin sont **converties en WebP**
  à la volée, redimensionnées à 1280 px max, qualité 82.
- Le fichier stocké et l'URL en base ont directement l'extension `.webp`.
- Les uploads non-image ou corrompus sont silencieusement ignorés.

#### 4. Templates — balise `<picture>` + lazy-loading

- Filtre Jinja `to_webp` ajouté dans `app/routers/web.py` : transforme
  `/foo.png` → `/foo.webp` (utilisé pour l'attribut `srcset`).
- `voitures.html` (grille) et `voiture_detail.html` (galerie) utilisent
  maintenant :

  ```html
  <picture>
    <source srcset="{{ photo | to_webp }}" type="image/webp">
    <img src="{{ photo }}" loading="lazy" decoding="async" ...>
  </picture>
  ```

  Le navigateur charge le WebP s'il est dispo (tous les navigateurs modernes),
  sinon fallback sur le PNG original.

- La première photo de la galerie garde `loading="eager"` pour éviter un
  flash blanc au-dessus de la ligne de flottaison.

## À exécuter manuellement (actions à risque)

1. **Installer Pillow** :

   ```
   pip install -r requirements.txt
   ```

2. **Convertir les images existantes** (one-shot, ~1 min pour 41 MB) :

   ```
   python scripts/optimize_images.py
   ```

3. **Vérifier** dans le navigateur (DevTools → Network) : les vignettes de
   voitures doivent se charger en `.webp`.

## Impact attendu

- **Poids page voitures** : de ~5-10 MB à < 500 KB.
- **Poids page detail** : de ~15-25 MB à < 1 MB.
- **Nouveaux uploads** : automatiquement optimisés, plus de PNG géants en DB.

## Résultat mesuré (2026-08-04)

Script exécuté sur les 22 images existantes :

| Format | Taille totale |
| ------ | ------------- |
| PNG originaux | **28 MB** |
| WebP générés  | **1,8 MB** |

**Gain : ~94 %** sur les photos voitures. Les originaux sont conservés
comme fallback (utile pour anciens navigateurs, sinon supprimables plus tard
via un script de nettoyage une fois la stabilité confirmée).

## Prochaine étape

Étape 4 : optimisations JS de la carte (debounce reverse-geocoding, retrait
des vendors inutiles).
