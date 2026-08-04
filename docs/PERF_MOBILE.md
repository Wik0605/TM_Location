# Optimisations fluidité mobile

Document unique regroupant les étapes du plan de fluidité mobile
(page itinéraire + pages voitures). Chaque étape est datée et documente
ce qui a été fait, comment vérifier, et l'impact mesuré.

Plan complet : `~/.claude/plans/regarde-mon-app-jiggly-volcano.md`

---

## Étape 1 — Compression Gzip & Cache HTTP statique

Date : 2026-08-04
Fichier modifié : `app/main.py`

### Objectif

Réduire le poids téléchargé par les navigateurs (surtout mobiles) et éviter le
re-téléchargement inutile des fichiers statiques (CSS, JS, images) entre les
visites. Aucune dépendance ajoutée, aucun changement de comportement métier.

### Ce qui a été fait

#### 1. Middleware Gzip

Ajout de `GZipMiddleware` (fourni par Starlette, déjà inclus avec FastAPI) :

```python
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

- Compresse automatiquement toute réponse HTTP > 1 KB si le client envoie
  l'en-tête `Accept-Encoding: gzip` (tous les navigateurs modernes le font).
- Gain typique : **70 à 80 %** sur le HTML, CSS, JS et JSON.
- Aucun effet sur les images/fonts (déjà compressés).

#### 2. Cache HTTP sur `/static`

Création d'une sous-classe légère de `StaticFiles` qui ajoute l'en-tête
`Cache-Control` sur chaque fichier servi :

```python
class CachedStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, Response) and response.status_code == 200:
            response.headers["Cache-Control"] = (
                f"public, max-age={STATIC_CACHE_MAX_AGE}"
            )
        return response
```

- `STATIC_CACHE_MAX_AGE = 60 * 60 * 24 * 7` → **7 jours**.
- Le navigateur conserve les fichiers en cache local pendant une semaine :
  la 2ᵉ visite ne redemande plus le CSS/JS/images.
- Le montage `/static` utilise maintenant cette classe :

```python
app.mount("/static", CachedStaticFiles(directory=str(STATIC_DIR)), name="static")
```

### Comment vérifier

Lancer l'app :

```
uvicorn app.main:app --reload
```

Puis dans un autre terminal :

```
curl -I -H "Accept-Encoding: gzip" http://localhost:8000/static/dist.css
```

Réponse attendue :

- `content-encoding: gzip`
- `cache-control: public, max-age=604800`

### Impact attendu

- **Première visite** : téléchargement plus léger (gzip sur HTML/CSS/JS).
- **Visites suivantes** : les fichiers statiques ne sont plus re-téléchargés
  pendant 7 jours → chargement quasi instantané.
- Bénéfice particulièrement fort sur mobile 3G / réseau lent.

### À noter

- Si un fichier statique change, il faut invalider le cache. Deux options
  possibles à l'avenir :
  - Ajouter un hash dans le nom du fichier (`dist.abc123.css`) — méthode
    standard mais demande un pipeline de build.
  - Utiliser un query-string versionné (`dist.css?v=2`) dans les templates.
- Pour l'instant, en dev, un `Cmd+Shift+R` force le rechargement.

---

## Étape 2 — Nettoyage `tailwind.config.js`

Date : 2026-08-04

L'audit initial pensait que Tailwind n'était pas purgé (`dist.css` estimé à 2,45 MB).
Vérification faite : `dist.css` fait **62 KB**, déjà propre. Le projet utilise
Tailwind **v4** avec `@import "tailwindcss"` dans `static/css/src.css`, qui purge
automatiquement en scannant les templates.

**Action réalisée :** suppression de `tailwind.config.js` (config v3 obsolète,
sans effet réel en v4, source de confusion).

---

## Étape 3 — Optimisation des images (le vrai gros gain)

Date : 2026-08-04

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

### À exécuter manuellement (actions à risque)

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

### Impact attendu

- **Poids page voitures** : de ~5-10 MB à < 500 KB.
- **Poids page detail** : de ~15-25 MB à < 1 MB.
- **Nouveaux uploads** : automatiquement optimisés, plus de PNG géants en DB.

### Résultat mesuré (2026-08-04)

Script exécuté sur les 22 images existantes :

| Format | Taille totale |
| ------ | ------------- |
| PNG originaux | **28 MB** |
| WebP générés  | **1,8 MB** |

**Gain : ~94 %** sur les photos voitures. Les originaux sont conservés
comme fallback (utile pour anciens navigateurs, sinon supprimables plus tard
via un script de nettoyage une fois la stabilité confirmée).

---

---

## Étape 4 — Optimisations JS de la carte

Date : 2026-08-04

### Ce qui a été fait

#### 1. `static/js/itineraire/main.js` — init carte plus fiable

Avant :
```js
setTimeout(() => map.invalidateSize(), 200);
```

Après :
```js
map.whenReady(() => map.invalidateSize());
```

- Supprime la race condition (le `200 ms` était arbitraire, trop long sur
  desktop, parfois trop court sur mobile lent).
- Leaflet appelle le callback dès que la carte est vraiment prête, une seule
  fois, sans timer.

#### 2. `static/js/itineraire/pick.js` — annulation des requêtes Nominatim

Utilise un `AbortController` par élément DOM (départ, arrivée, chaque escale).
Si l'utilisateur clique une nouvelle fois avant que la requête précédente
soit revenue, on annule l'ancienne. Empêche :

- Les résultats d'anciennes requêtes qui écrasent la nouvelle adresse.
- La saturation de Nominatim (limité à 1 req/s) sur des clics rapprochés.

#### 3. `app/templates/base.html` — HTMX en `defer`

Ajout de l'attribut `defer` sur `<script src=".../htmx.min.js">`. Effet :

- Le script ne bloque plus le parsing HTML (au lieu de bloquer, il télécharge
  en parallèle et s'exécute juste avant `DOMContentLoaded`).
- HTMX continue de fonctionner normalement (il s'auto-initialise sur
  `DOMContentLoaded`).
- Gain concret : le premier rendu visuel (First Contentful Paint) arrive
  plus tôt, surtout sur mobile lent.

### Impact attendu

- Carte itinéraire : disparition d'un éventuel flash de 200 ms au premier
  rendu, plus de désynchronisation sur mobile lent.
- Reverse-geocoding : plus de "flash" d'adresse obsolète, moins de risque
  de rate-limit Nominatim.
- Toutes les pages : FCP amélioré grâce au `defer` sur HTMX.

### Ce qui n'a pas été fait (et pourquoi)

- **Retrait complet de HTMX sur la page itinéraire** : HTMX est utilisé
  dans l'ensemble de l'app (admin, formulaires) via `base.html`. Le
  supprimer conditionnellement ajouterait de la complexité pour un gain
  marginal (47 KB, désormais mis en cache 7 jours grâce à l'étape 1).
- **Alpine.js** : l'audit initial mentionnait Alpine mais il n'est pas
  chargé dans `base.html`. Rien à retirer.

---

## Étape 5 — Media queries mobile (< 480 px)

Date : 2026-08-04
Fichier modifié : `static/css/itineraire.css`

### Ce qui a été fait

Ajout d'une media query `@media (max-width: 480px)` à la fin du fichier
pour cibler les téléphones bas de gamme et compacts :

- **Hauteur carte** : `55vh` (au lieu de `62vh`) avec `min-height: 320px`.
  Laisse plus de place aux contrôles (bandeau de sélection, badges départ/
  arrivée) sans obliger à scroller.
- **Cibles tactiles** : `min-height: 44px` sur tous les boutons d'action
  (départ, arrivée, escale, géolocalisation, annuler, CTA sticky, ajouter
  escale). Conforme aux guidelines Apple (44 px) et Google (48 px, on est
  à la limite basse acceptable).
- **CTA sticky** : padding et taille de police réduits pour éviter le
  débordement sur écran étroit.
- **Bannière et badges** : taille de police légèrement réduite (0.82-0.85
  rem) pour rester lisible sans casser le layout.

### Comment vérifier

1. DevTools → mode responsive → choisir un preset < 480 px
   (ex : iPhone SE 375 px, Galaxy S8+ 360 px).
2. La carte doit occuper ~55 % de la hauteur écran.
3. Tous les boutons doivent être facilement cliquables au doigt.
4. Pas de scroll horizontal, pas de texte tronqué.

### Impact attendu

Meilleure ergonomie sur les petits écrans (Antananarivo = beaucoup d'Android
bas/moyen gamme avec écrans 5-6 pouces). Moins de mauvais clics, meilleure
lisibilité, moins de scroll pour atteindre les contrôles.

---

## Récapitulatif

Les 5 étapes du plan sont terminées :

| Étape | Domaine  | Impact |
| ----- | -------- | ------ |
| 1     | Back-end | Gzip + cache 7j → -70/80 % sur le texte, 2e visite quasi instantanée |
| 2     | Build    | Nettoyage `tailwind.config.js` (v3 obsolète) |
| 3     | Images   | WebP + lazy-load → **-94 %** mesuré (28 MB → 1,8 MB) |
| 4     | JS       | `whenReady`, AbortController, HTMX `defer` → init fiable, FCP amélioré |
| 5     | CSS      | Media queries < 480 px → ergonomie mobile bas de gamme |

Pour valider globalement : Lighthouse Mobile avant/après sur les pages
`/voitures`, `/voitures/<id>` et `/voitures/<id>/itineraire`.
Cible : Performance > 85, LCP < 2,5 s, poids total < 1 MB.
