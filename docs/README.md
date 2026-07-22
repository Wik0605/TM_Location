# Handoff : TM Location — UI/UX refonte

## Aperçu
Refonte premium de l'application de location de voitures **TM Location** (Madagascar). Le prototype couvre le parcours complet mobile-first : Accueil → Catalogue → Détail véhicule → Calculateur d'itinéraire interactif → Confirmation de réservation.

Stack cible déclarée par l'utilisateur : **FastAPI + Jinja2 + TailwindCSS + HTMX**, navigation mobile-first.

## À propos des fichiers de design
Les fichiers `.dc.html` de ce dossier sont des **maquettes de référence** créées en HTML (React interne au générateur), pas du code à copier-coller tel quel. L'objectif est de **recréer ces écrans dans l'environnement cible** :
- Structure des pages → templates Jinja2 (un template par écran : `index.html`, `voitures.html`, `voiture_detail.html`, `itineraire.html`, `voiture_confirmation.html`, partagés via un layout de base avec header + bottom-nav).
- Style → classes TailwindCSS équivalentes aux styles inline documentés ci-dessous.
- Interactivité (navigation entre écrans, filtres, placement de points sur la carte, quota/modal) → attributs `hx-get`/`hx-post`/`hx-target`/`hx-swap` HTMX, avec des fragments serveur retournés par FastAPI. Le prototype simule ces échanges côté client (React state) ; en prod, chaque transition d'écran devient un appel HTMX vers une route FastAPI qui rend un fragment Jinja2.
- Carte Leaflet : le prototype utilise une carte **stylisée simulée** (dégradé + grille, sans dépendance réseau) pour éviter de charger des tuiles OpenStreetMap dans l'environnement de maquettage. En production, remplacer par une vraie carte **Leaflet.js** avec tuiles OSM, marqueurs personnalisés (icônes divIcon) et gestion de clics `map.on('click', ...)`.

## Fidélité
**Haute fidélité (hifi)** : couleurs, typographie, espacements et micro-interactions sont définitifs et doivent être repris au pixel près. Les photos de véhicules et le logo sont des **placeholders stylés** (hachures diagonales + libellé texte) — à remplacer par les vrais visuels du client.

## Système de design

### Couleurs
- Primaire (ambre premium) : `#D97706` — hover/actif : `#B45309`
- Accent clair (texte sur fond sombre) : `#FCD34D`
- Fond teinté primaire (cards claires) : `#FFFBEB`, `#FEF3C7`, `#FDE68A`
- Noir profond : `#0A0A0A` (texte, boutons secondaires, header hero)
- Gris neutres : `#78716C` (texte secondaire), `#A8A29E` (texte tertiaire/placeholder), `#F5F5F4` (fond badges), `#F0EFED` / `#E7E5E4` (bordures)
- Statuts : vert émeraude `#059669` (disponible), rouge rubis `#DC2626` (alerte/arrivée), indigo `#4F46E5` (action secondaire — bouton "Calculer l'itinéraire")
- Marqueurs carte : vert `#059669` (départ), rouge `#DC2626` (arrivée), ambre `#D97706` (escale)

> **Tweak couleur** : le prototype expose une prop `primaryColor` (voir section Tweaks) qui recalcule automatiquement toutes les nuances dérivées (hover, tint clair, tint très clair) via HSL. Si le client change de couleur de marque, réutiliser cette même logique de dérivation de teintes côté Tailwind (ex. générer une palette `amber`/`emerald`/`indigo` custom dans `tailwind.config.js`).

### Typographie
- Titres : **Outfit**, graisses 700–900, `letter-spacing:-0.02em` à `-0.04em` (tracking très serré, façon `tracking-tighter font-black`)
- Corps de texte : **Inter**, 400–700
- Échelle : titres hero 26–34px, titres de section 15–20px, corps 11–13px, labels/badges 8.5–11px (tout en majuscules avec `letter-spacing` pour les labels de nav et forfaits)

### Effets
- Rayons : `rounded-xl` à `rounded-3xl` (12px à 32px) selon la taille du composant
- Ombres : douces et diffuses, `box-shadow: 0 4-12px 16-30px rgba(0,0,0,.04-.25)` (plus la carte est "flottante", plus l'ombre est prononcée)
- Verre trempé (glassmorphism) : `backdrop-filter: blur(14-20px)` + fond blanc/noir semi-transparent — utilisé sur le header sticky, la bottom-nav, et la carte de recherche flottante du hero
- Transitions : `transition: all .3s` sur tous les éléments interactifs (hover translateY, changement de couleur, scale léger sur CTA)

## Écrans

### 1. Accueil (`isAccueil`)
- **Header sticky** translucide avec logo "TM Location" (deux tons noir/ambre) + bouton "RÉSERVER" pilule ambre.
- **Hero** : fond dégradé ambre→noir sur texture hachurée (placeholder photo), titre H1 gras 30px, sous-texte. Une carte glassmorphism en overlay (position absolute, débordant sur la section suivante de -56px) contient Départ/Retour (deux champs) + Type de véhicule + CTA "Rechercher un véhicule".
- **Grille véhicules vedettes** : liste verticale de cards (image 120px hachurée + badge "Disponible" vert + badge catégorie noir, nom, 3 badges caractéristiques — boîte/clim/carburant, prix + bouton "Détails" pilule noire). Clic sur la card → écran Détail.
- **Bottom nav fixe** : 3 onglets Accueil 🏠 / Devis 📋 / Profil 👤, actif = ambre, inactif = gris.

### 2. Catalogue (`isCatalogue`)
- Même header, remplacé par bouton retour "ACCUEIL".
- **Filtres pilule horizontaux scrollables** : Tous / SUV-4x4 / Citadines / Pick-up — actif = fond noir/texte blanc.
- **Grille responsive** de cards véhicule (variante compacte, image 110px, catégorie en badge, transmission/clim/carburant/places sur une ligne).

### 3. Détail véhicule (`isDetail`)
- Header avec bouton retour rond + titre.
- **Galerie image** 220px (placeholder) avec indicateurs de pagination (dots).
- **Grille de specs** 3 colonnes (boîte, carburant, places) en cards grises arrondies.
- **Formulaire de réservation rapide** : départ/retour + total estimé, dans une card blanche à bordure fine + ombre.
- **CTA principal ambre** "📍 Ouvrir le calculateur d'itinéraire" → écran Itinéraire.
- CTA secondaire noir "Réserver ce véhicule".

### 4. Calculateur d'itinéraire (`isItineraire`)
- Header avec retour + compteur de quota ("X/7 calculs", vire au rouge si ≤2 restants).
- **Carte stylisée** (280px, cliquable) avec routes simulées (lignes blanches), contrôles zoom +/− en haut à droite, marqueurs en losange colorés (vert départ / rouge arrivée / ambre escales) placés en `left/top` %.
- **Bannière de guidage** flottante ("Touche la carte pour placer le point") avec point pulsant, visible seulement en mode placement (`placingMode`).
- **Boutons Départ / Arrivée** : rangée cliquable avec pastille de couleur + libellé dynamique ("Pointer" → "placé ✓") ; **escales** ajoutées dynamiquement avec bouton "+ Ajouter une escale" en pointillés ambre.
- **Formulaire de réservation** : Date début/fin + Heure début/fin (inputs natifs `type="date"`/`type="time"`), **Type de location en liste déroulante** (`<select>` : Journée / Demi-jour / Semaine), bouton indigo "Calculer l'itinéraire", puis récap Distance estimée (km) + Prix total (calcul dynamique : `distance × 3500 Ar + prix véhicule × multiplicateur forfait`).
- CTA final "Confirmer la réservation" (désactivé/gris tant que départ+arrivée non placés).
- **Modal de quota** : overlay flou, icône "7/7", titre + texte explicatif, bouton officiel "Se connecter avec Google" (pastille G bleue + texte), lien "Continuer plus tard".

### 5. Confirmation (`isConfirmation`)
- Icône check vert circulaire + titre + sous-texte.
- **Reçu style ticket** : bandeau noir dégradé avec logo + libellé "TICKET", mini-carte avec marqueurs, puis détails (véhicule, date/heure, forfait, distance), séparateur pointillé avec encoches semi-circulaires (effet détachable), total en gros ambre.
- Bouton noir "Nouvelle réservation" → retour Accueil (reset complet du state).

## Interactions & état
- Navigation entre écrans = changement d'un seul état `screen` (accueil/catalogue/detail/itineraire/confirmation) → en HTMX/FastAPI, chaque CTA de nav devient `hx-get="/route" hx-target="#app" hx-swap="innerHTML"` retournant le fragment Jinja2 correspondant.
- Sélection de véhicule = state `selectedCarIdx`/`selectedCar` → passer l'id du véhicule en paramètre de route (`/voitures/{id}`).
- Placement des points sur la carte (`depart`, `arrivee`, `escales[]`) : capture des coordonnées relatives au clic (%) ; en prod avec Leaflet, remplacer par `map.on('click', e => …)` et `e.latlng`.
- Quota (`quotaUsed`, max 7/jour) : compteur qui déclenche la modal quand atteint ; state à faire persister côté serveur (session ou cookie) plutôt que client.
- Calcul prix/distance : recalcul réactif dès que départ+arrivée sont posés ou que le forfait change.
- Tous les boutons désactivés (`disabled`) ont un style grisé explicite (`background:#E7E5E4; color:#A8A29E`).

## Design Tokens (résumé)
- Rayons : 10px / 12px / 14px / 18px / 20px / 22px / 32px
- Ombres : `0 2px 10px rgba(0,0,0,.04)` (repos) → `0 12px 28px rgba(0,0,0,.1)` (hover)
- Police titres : Outfit 700–900 ; police texte : Inter 400–700
- Espacement de base : multiples de 4px (gap 6/8/10/12/14/16/18/20px)

## Assets
Aucun asset image réel — toutes les photos véhicules/logo sont des placeholders (fond hachuré diagonal + libellé). À remplacer par les vraies photos détourées et le logo officiel TM Location.

## Fichiers inclus
- `TM Location - Prototype.dc.html` — prototype interactif complet (5 écrans, navigation cliquable, thème couleur personnalisable via tweak `primaryColor`).
- `TM Location - Accueil (variations).dc.html` — 3 explorations visuelles de la page d'accueil (Glass Premium retenu = option 1a, Split Editorial, Minimal Bold) pour référence de direction artistique.

Pour visualiser ces fichiers : les ouvrir dans un navigateur (ce sont des pages HTML autonomes qui embarquent leur propre moteur de rendu React).
