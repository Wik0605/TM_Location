# Update Design — 8 juillet 2026

Refonte UI/UX complète de TM_Location à partir du handoff Claude Design
(`docs/design/`). L'intégration a été découpée en 5 sessions ; les
Sessions 1 à 4 sont terminées, la Session 5 (itinéraire) est à venir.

Stack cible : **FastAPI + Jinja2 + TailwindCSS v4 + HTMX** (mobile-first).

---

## Session 1 — Fondations design (commit `a6681e8`)

**Objectif** : poser la palette, les fonts et la coquille (`base.html`)
partagées par toutes les pages.

### Fichiers créés
- `docs/design/` — extraction du zip Claude Design
  - `README.md` (spec design complète)
  - `TM Location - Prototype.dc.html` (prototype interactif 5 écrans)
  - `TM Location - Accueil (variations).dc.html` (explorations visuelles)

### Fichiers modifiés
- `static/css/theme.css` — nouvelle palette ambre premium :
  - Primaire : `#D97706` (ambre), hover `#B45309`
  - Accent : `#FCD34D` (doré)
  - Ink : `#0A0A0A` (noir profond)
  - Neutres : `#78716C` / `#A8A29E` / `#F5F5F4` / `#F0EFED` / `#E7E5E4`
  - Statuts : `#059669` succès, `#DC2626` erreur, `#4F46E5` indigo-cta
  - Ombres : sm/md/lg/xl calibrées sur la spec
  - Fonts : Inter (corps) + Outfit (titres)
- `static/css/src.css` — tokens exposés à Tailwind via `@theme`
  (primary-tint, ink, indigo-cta, danger, font-display…)
- `app/templates/base.html` :
  - Import Google Fonts (Outfit + Inter)
  - Fix du bloc Jinja `{% block styles %}` cassé dans le CSS inline
  - Header sticky glassmorphism (`bg-white/75 backdrop-blur-xl`)
  - Bouton **RÉSERVER** en pilule ambre (spec)
  - Bottom-nav peaufinée : max-w-md centrée, `text-neutral`,
    tracking-widest sur labels

---

## Session 2 — Page d'accueil (`index.html`, commit `355bf1f`)

**Objectif** : hero premium + card recherche flottante + grille véhicules
vedettes.

### Ce qui change
- **Hero** : dégradé ambre → noir profond avec texture hachurée
  (placeholder photo façon spec), typo Outfit `tracking-tight`,
  accent doré (`#FCD34D`) sur le second membre du titre.
- **Card recherche flottante** :
  - Glassmorphism (`bg-white/95 backdrop-blur-xl`)
  - Débordement de -56px sur la section suivante (overlap voulu)
  - 3 champs : Départ (date), Retour (date), Type de véhicule (select)
  - CTA ambre pilule "Rechercher un véhicule" → GET `/voitures`
- **Grille véhicules vedettes** (verticale, mobile-first) :
  - Cards `rounded-3xl` avec image 120px
  - Placeholder hachuré ambre si pas de photo
  - Badge vert **Disponible** (haut-gauche) + badge noir **places**
    (haut-droite)
  - Nom en Outfit black
  - 3 mini-badges : places / conso L/100 / nombre de forfaits
  - Prix **Dès X Ar** en ambre + bouton **Détails** pilule noire
  - Hover : `-translate-y-1` + ombre plus prononcée

### Adaptation vs spec
Le modèle `Voiture` n'a pas de champs `boîte`/`clim`/`carburant type`.
Les 3 badges de caractéristiques utilisent donc ce qui existe réellement
en base : **places / consommation / forfaits**. Pour matcher la spec à
100 %, il faudrait ajouter ces colonnes via une migration Alembic
(session dédiée à prévoir).

---

## Session 3 — Catalogue (`voitures.html`, commit `c819021`)

**Objectif** : filtres pilule scrollables + grille compacte 2 colonnes.

### Ce qui change
- **Header du catalogue** :
  - Bouton retour rond (fond `neutral-soft`, chevron gauche)
  - Libellé "CATALOGUE" (tracking `0.2em`, gris clair)
  - Titre "Nos véhicules" en Outfit black
- **Filtres pilule horizontaux scrollables** :
  - Options : `Tous` / `SUV / 4x4` / `Citadines` / `Pick-up`
  - Actif = fond **ink** + texte blanc + shadow
  - Inactif = fond `neutral-soft` + hover
  - Scroll horizontal sans scrollbar visible (`no-scrollbar`)
  - Les liens passent `?type=xxx` dans l'URL (URL propre, prête pour
    câblage backend)
- **Grille compacte 2 colonnes** :
  - Image 110px + placeholder hachuré ambre si vide
  - Badge noir places (haut-gauche) + pastille verte dispo (haut-droite,
    ring blanc)
  - Nom Outfit tronqué si trop long
  - Ligne caractéristiques : conso · places · forfaits
  - Prix **Dès X Ar** ambre en bas, séparateur fin au-dessus

### Note importante
Les filtres passent bien `?type=suv` etc. dans l'URL, mais côté serveur,
`car_service.get_available_voitures` **ne filtre pas encore** par
catégorie (pas de champ `categorie` dans le modèle). Filtres visuels
pour l'instant, câblage backend à faire dans une session dédiée
(migration Alembic + service).

---

## Session 4 — Détail véhicule (`voiture_detail.html`, commit `d1bbea4`)

**Objectif** : galerie + specs + choix forfait + formulaire + double CTA.

### Ce qui change
- **Header** :
  - Bouton retour rond → `/voitures`
  - Libellé "VÉHICULE" + nom véhicule en Outfit black tronqué
- **Galerie 220px** :
  - `rounded-3xl` avec fond `primary-tint` si pas de photo
  - Dots pagination : dot actif = **barre allongée blanche** (`w-6 h-1.5`),
    inactifs = petits points blancs semi-transparents
  - Flèches précédent/suivant en glass rond
  - Badge **Disponible** vert (haut-gauche)
  - Carousel + lightbox conservés (JS existant `car_detail.js`)
- **Grille specs 3 colonnes** :
  - Cards `neutral-soft` `rounded-2xl` + emoji + valeur Outfit + label
  - Places 💺 / Conso ⛽ / Forfaits 📋
- **Choix du forfait** :
  - Radios stylisées en cards
  - Sélection : bordure ambre + fond `primary-light` (via
    `has-[:checked]` Tailwind)
- **Card réservation** :
  - Blanche fine avec bordure `border-soft` + shadow douce
  - Inputs en `bg-neutral-soft` qui deviennent blancs au focus + ring
    ambre
  - Champs : Nom / Téléphone / Email (opt.) / Date souhaitée
- **Double CTA (ordre spec)** :
  1. **Ambre pilule** : "📍 Ouvrir le calculateur d'itinéraire" →
     `/voitures/{id}/itineraire`
  2. **Noir pilule** : "Réserver ce véhicule" (submit du form)
- Note bas : "Assistance 24/7 · Assurance incluse"

---

## Session 5 — Calculateur d'itinéraire (`itineraire.html` + `itineraire.css`, commit `511a825`)

**Objectif** : refonte du plus gros écran, avec carte + placement de
points + formulaire + résumé + modal quota — sans casser la logique JS
existante (Leaflet + `itineraire.js`).

### Ce qui change (template)
- **Header** :
  - Bouton retour rond → `/voitures/{id}`
  - Libellé "ITINÉRAIRE" + nom véhicule Outfit
  - **Compteur quota `X/7`** en pilule (haut-droite), classes CSS
    `.low` / `.critical` prêtes pour passage en rouge/ambre
- **Modal quota** :
  - Icône ronde `7/7` sur fond `primary-tint`
  - Titre Outfit + texte tutoyé
  - Bouton Google officiel (SVG assets) + lien discret
    "Continuer plus tard"
  - Overlay `bg-black/60 backdrop-blur-sm`
- **Carte** :
  - `rounded-3xl` clean, hauteur 280px mobile / 55vh desktop
  - Loader avec spinner ambre au lieu d'indigo
- **Départ / Arrivée** :
  - Boutons `.pick-cta` avec **pastilles colorées** (rond de couleur au
    lieu d'emoji) : vert `#059669` départ, rouge `#DC2626` arrivée
  - Libellé UPPERCASE tracking-widest
- **Escales** :
  - Bouton "+ Ajouter escale" pleine largeur en **pointillés ambre**
    (spec)
  - Template escale mis à jour (couleurs ambre)
- **Période de location** :
  - Bloc `neutral-soft` `rounded-2xl` avec 4 inputs (date début/fin +
    heure début/fin)
  - Fond blanc + focus `ring-primary`
- **Type de location** :
  - Select stylisé bg `neutral-soft` → blanc au focus
- **CTA principal** :
  - **Indigo `#4F46E5`** (spec) "Calculer l'itinéraire", pilule pleine
    largeur, uppercase tracking-widest
- **Résumé** :
  - Cards stylisées, ligne Total en fond `primary-light` + prix ambre
    Outfit gros
- **CTA "Confirmer la réservation"** :
  - Bouton noir plein bas de card résumé

### Ce qui change (CSS `itineraire.css`)
- `.location-badge.start` : palette émeraude douce (`#ECFDF5` fond,
  `#065F46` texte, `#A7F3D0` bordure)
- `.location-badge.end` : palette rubis douce (`#FEF2F2` fond,
  `#991B1B` texte, `#FCA5A5` bordure)
- `.pick-cta` : uppercase tracking-widest, palette assortie selon le
  point (start/end)
- `#pick-banner` : pilule blanche avec ombre douce et bordure fine
- `.locate-btn` : carré arrondi + icône ambre
- Classes `#quota-counter.low` / `.critical` prêtes (JS n'y touche pas
  encore)

### Ce qui n'a pas été refait (préservation logique)
- `static/js/itineraire.js` **inchangé** — tous les IDs et classes
  attendus par le JS sont préservés dans le template
- Le compteur quota affiche `0/7` en dur pour l'instant — le câblage
  serveur → client se fera plus tard
- Les marqueurs Leaflet en losange colorés de la spec ne sont pas
  appliqués (les icônes actuelles définies dans `itineraire.js`
  restent)

---

## Session 6 — Confirmation réservation (`voiture_confirmation.html`, commit `21f23c6`)

**Objectif** : ticket détachable premium avec bandeau noir dégradé et
total ambre.

### Ce qui change
- **Icône succès** : cercle vert doux (`bg-success/15`) avec check SVG
  épais + titre Outfit "Demande envoyée !" + sous-texte tutoyé
- **Ticket détachable** :
  - **Bandeau haut** dégradé `ink → primary-dark` avec logo TM Location
    deux tons + libellé "TICKET" en accent doré + numéro de référence
    formaté (`#000042`)
  - **Détails** : Véhicule, Forfait, Client, Téléphone, Date, Statut
    (avec pastille verte + point pulsant)
  - **Séparateur pointillé avec encoches semi-circulaires** — deux ronds
    gris sur les côtés donnent l'illusion d'un ticket qu'on peut
    déchirer (effet signature de la spec)
  - **Bloc Total** en fond `primary-light` avec prix ambre Outfit gros
- **Actions** :
  - Bouton **noir** "Nouvelle réservation" → `/` (retour accueil, spec)
  - Bouton **neutre** "Voir d'autres véhicules" → `/voitures`

### Bug corrigé au passage
Le template précédent référençait `voiture.marque`, `voiture.modele` et
`voiture.annee` — **ces champs n'existent pas** dans le modèle `Voiture`
(seul `nom` existe). Corrigé pour utiliser `voiture.nom`.

---

## Refonte design bouclée ✅

Les 6 sessions sont terminées. Récap des commits :

| # | Page                          | Commit    |
|---|-------------------------------|-----------|
| 1 | `base.html` + palette + fonts | `a6681e8` |
| 2 | `index.html`                  | `355bf1f` |
| 3 | `voitures.html`               | `c819021` |
| 4 | `voiture_detail.html`         | `d1bbea4` |
| 5 | `itineraire.html` + CSS       | `511a825` |
| 6 | `voiture_confirmation.html`   | `21f23c6` |

### Câblages backend restant (non demandés dans cette itération)
- Filtres catégories `?type=` côté serveur (`car_service` +
  champ `categorie` sur le modèle + migration Alembic)
- Compteur quota `X/7` lu depuis le serveur côté JS (router expose la
  valeur, `itineraire.js` la lit et applique `.low` / `.critical`)
- Champs boîte / clim / carburant si tu veux 100 % match spec (migration
  Alembic + admin form)
- Marqueurs Leaflet en losange colorés (retoucher `itineraire.js`)

---

## Récap tokens design en usage

| Token             | Valeur           | Usage                          |
|-------------------|------------------|--------------------------------|
| `primary`         | `#D97706`        | Ambre principal, CTA, prix     |
| `primary-dark`    | `#B45309`        | Hover CTA ambre                |
| `primary-light`   | `#FFFBEB`        | Fond selection radio           |
| `primary-tint`    | `#FEF3C7`        | Fond image placeholder         |
| `accent`          | `#FCD34D`        | Accent doré sur hero           |
| `ink`             | `#0A0A0A`        | Texte principal, CTA secondaire|
| `neutral-strong`  | `#78716C`        | Texte secondaire, labels       |
| `neutral`         | `#A8A29E`        | Texte tertiaire, placeholders  |
| `neutral-soft`    | `#F5F5F4`        | Fond inputs, cards specs       |
| `border-soft`     | `#F0EFED`        | Bordures cards fines           |
| `border-strong`   | `#E7E5E4`        | Bordures inputs, séparateurs   |
| `success`         | `#059669`        | Badge Disponible               |
| `danger`          | `#DC2626`        | Erreurs, alertes quota         |
| `indigo-cta`      | `#4F46E5`        | Bouton "Calculer l'itinéraire" |

---

## Vérification / test

Pour visualiser en local :

```bash
cd ~/TM_Location
python run.py
```

Ouvre `http://127.0.0.1:8000` puis active le **mode mobile** de Chrome
(Cmd+Opt+I → toggle device toolbar → iPhone).

Comparer avec la maquette de référence :

```bash
open "docs/design/TM Location - Prototype.dc.html"
```

Rebuild Tailwind après tout changement de tokens ou classes utilisées :

```bash
npx @tailwindcss/cli -i ./static/css/src.css -o ./static/css/dist.css
```
