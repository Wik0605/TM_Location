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

## À venir — Session 5 (itinéraire)

Refonte de `itineraire.html` :
- Compteur quota `X/7 calculs` (rouge si ≤2)
- Carte stylisée 280px cliquable + contrôles zoom
- Bannière de guidage flottante en mode placement
- Boutons Départ / Arrivée / Escales avec pastilles colorées
- Formulaire Date début/fin + Heure début/fin + Type location (select)
- Bouton indigo "Calculer l'itinéraire" + récap distance/prix
- CTA "Confirmer la réservation" désactivé tant que départ+arrivée
  non placés
- Modal de quota avec bouton Google

Puis Session 6 : `voiture_confirmation.html` (ticket détachable).

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
