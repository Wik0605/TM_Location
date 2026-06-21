# Calculateur d'itinéraire — Documentation

> Ce document explique la fonctionnalité de calcul d'itinéraire avec pointage interactif sur carte, développée pour Spass Gasy.

---

## Vue d'ensemble

La page itinéraire permet à un client de :
1. **Pointer** son départ, ses escales et son arrivée directement sur une carte interactive
2. **Calculer** la distance réelle par route entre ces points
3. **Estimer** le coût total (location + carburant)
4. **Réserver** le véhicule depuis la même page

**Route** : `/car/{car_id}/itineraire`

---

## Technologies utilisées

| Outil | Rôle |
|-------|------|
| **Leaflet.js** | Affichage de la carte interactive |
| **BRouter** | Calcul d'itinéraire routier (API externe gratuite) |
| **Nominatim** | Géocodage inversé — convertit des coordonnées GPS en nom de lieu |
| **OpenStreetMap** | Tuiles de fond de carte |

---

## Architecture de la page

```
itineraire.html
├── CSS custom (styles inline dans <style>)
├── Bannière flottante (mode pointage)
├── Formulaire gauche
│   ├── Bouton "Pointer le départ" → badge 🟢 après sélection
│   ├── Escales dynamiques (bouton + badge 🔵)
│   ├── Bouton "Pointer l'arrivée" → badge 🔴 après sélection
│   ├── Section carburant (conso + prix)
│   ├── Bouton Calculer
│   └── Carte résultats (distance, carburant, total, CTA réserver)
└── Carte Leaflet (droite / plein écran mobile)
```

---

## Fonctionnement du pointage

### Flux utilisateur

```
Tap "📍 Pointer le départ"
    → Scroll automatique vers la carte (mobile)
    → Bannière flottante apparaît : "Touche la carte pour poser le DÉPART"
    → Curseur crosshair activé sur la carte

Tap sur la carte
    → Marqueur vert posé
    → Vibration haptic (40ms, mobile)
    → Scroll automatique retour au formulaire (mobile)
    → Badge 🟢 affiché avec "Localisation..."
    → Appel Nominatim → nom du lieu affiché dans le badge
```

### Modes de pointage

| Cible | Couleur marqueur | Badge |
|-------|-----------------|-------|
| Départ | `#22c55e` vert | 🟢 fond vert clair |
| Arrivée | `#ef4444` rouge | 🔴 fond rouge clair |
| Escale | `#3b82f6` bleu | 🔵 fond bleu clair |

### Variable `pickingMode`

```javascript
var pickingMode = null;
// Valeurs possibles :
// null          → aucun mode actif
// 'start'       → on pointe le départ
// 'end'         → on pointe l'arrivée
// <element DOM> → on pointe une escale (référence .waypoint-item)
```

---

## Bannière flottante — choix technique

La bannière d'instruction est placée **en dehors de la carte** (`position: fixed`), pas en overlay sur la carte.

**Pourquoi ?**
- Un élément `position: absolute` sur la carte avec `pointer-events: auto` bloquerait les événements touch de Leaflet
- `overflow: hidden` sur le wrapper de carte bloque les touch events sur iOS Safari
- La bannière fixe évite ces conflits tout en restant visible pendant le pointage

```css
#pick-banner {
    position: fixed;
    bottom: 90px;     /* au-dessus de la bottom nav mobile */
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    pointer-events: auto; /* seulement la bannière, pas la carte */
}
```

---

## Initialisation Leaflet

```javascript
var map = L.map('map', {
    tap: true,          // active le support touch natif
    tapTolerance: 15    // tolérance en pixels pour les taps mobiles
}).setView([-18.91, 47.52], 13); // centré sur Antananarivo
```

**`tap: true` et `tapTolerance: 15`** sont essentiels pour que les taps mobiles déclenchent l'événement `click` de Leaflet sur Android et iOS.

---

## Calcul d'itinéraire — BRouter + OSRM en parallèle

Les deux APIs sont lancées **simultanément**. Le premier résultat valide est utilisé, l'autre est ignoré. Cela garantit vitesse et robustesse : OSRM répond en général en moins d'1 seconde, BRouter offre une meilleure qualité de tracé quand il réussit.

```javascript
var distanceKm = await firstValid(calcBRouter(coords), calcOSRM(coords));
```

### BRouter (qualité prioritaire)

```
GET https://brouter.de/brouter
    ?lonlats=lon1,lat1|lon2,lat2|lon3,lat3
    &profile=car-eco
    &alternativeidx=0
    &format=geojson
```

- Séparateur entre points : `|`
- Format coordonnées : `longitude,latitude`
- Distance lue depuis : `geojson.features[0].properties['track-length']` (en mètres)
- **Limite** : peut échouer (HTTP 500) si le réseau routier OSM est incomplet (zones rurales de Madagascar)

### OSRM (fallback rapide)

```
GET https://router.project-osrm.org/route/v1/driving/lon1,lat1;lon2,lat2;lon3,lat3
    ?overview=full
    &geometries=geojson
```

- Séparateur entre points : `;`
- Distance lue depuis : `data.routes[0].distance` (en mètres)
- Meilleure couverture globale, réponse plus rapide
- La géométrie est convertie en FeatureCollection pour rester compatible avec `L.geoJSON()`

### Logique `firstValid`

```javascript
function firstValid(...promises) {
    // Retourne le premier résultat non-null parmi les promises
    // Si toutes retournent null → resolve(null)
}
```

### Important : aller-retour

Les deux APIs calculent **exactement le trajet défini**. Pour un aller-retour A→B→A, mettre A comme point d'arrivée explicitement.

---

## Géocodage inversé via Nominatim

Après chaque pointage, l'app appelle Nominatim pour afficher un nom lisible.

```javascript
fetch('https://nominatim.openstreetmap.org/reverse'
    + '?lat=' + lat
    + '&lon=' + lng
    + '&format=json'
    + '&accept-language=fr')
```

Le nom affiché est limité aux 2 premiers segments de `display_name` :

```javascript
data.display_name.split(',').slice(0, 2).join(', ')
// ex: "Analakely, Antananarivo"
```

**Limite** : Nominatim est gratuit mais limité en requêtes simultanées. Pour la production à grande échelle, envisager une instance auto-hébergée.

---

## Escales dynamiques

Les escales sont créées depuis un `<template>` HTML cloné dynamiquement :

```javascript
document.getElementById('add-waypoint-btn').addEventListener('click', function () {
    var tmpl = document.getElementById('waypoint-template').content.cloneNode(true);
    var item = tmpl.querySelector('.waypoint-item');

    // Données stockées directement sur l'élément DOM
    item._pickedCoord = null;   // coordonnées pointées
    item._pickMarker = null;    // marqueur Leaflet associé

    // Suppression : retire le marqueur de la carte
    item.querySelector('.remove-waypoint-btn').addEventListener('click', function () {
        if (item._pickMarker) map.removeLayer(item._pickMarker);
        if (pickingMode === item) deactivatePickMode();
        item.remove();
    });
});
```

---

## Estimation du coût

Toutes les valeurs de calcul viennent **de la base de données admin** — rien n'est codé en dur côté client.

### Flux de données

```
Admin (formulaire /admin/rental-types)
        ↓
POST FastAPI → validation Pydantic
        ↓
SQLAlchemy → table rental_types (DB)
        ↓
Client ouvre /car/{id}/itineraire
        ↓
FastAPI lit la DB → passe rental_types au template Jinja2
        ↓
Template génère <option data-prix=... data-conso=... data-fuel-price=...>
        ↓
JavaScript lit les data-attributes et calcule
```

### Formule

```javascript
// locationCost : calculé depuis la DB (daily_price × price_multiplier × (1 - discount%))
// conso        : fuel_consumption du type de location (L/100km), lu depuis data-conso
// PRIX_LITRE   : fuel_price du type de location (Ar/L), lu depuis data-fuel-price

var fuelCost = (distanceKm / 100) * conso * PRIX_LITRE;
var total = locationCost + fuelCost;
```

### Data-attributes injectés par Jinja2

```html
<option
  data-prix="{{ (car.daily_price * rt.price_multiplier * (1 - rt.discount_percent / 100)) | int }}"
  data-conso="{{ rt.fuel_consumption }}"
  data-fuel-price="{{ rt.fuel_price }}">
```

- `data-prix` : même formule que le backend de réservation → cohérence garantie
- `data-conso` : consommation configurée dans l'admin (L/100km)
- `data-fuel-price` : prix du carburant configuré dans l'admin (Ar/L), fallback 4900 si non renseigné

Si l'admin modifie le prix du carburant, tous les calculs clients se mettent à jour immédiatement sans toucher au code.

---

## Comportement scroll — carte par-dessus le navbar

Quand l'utilisateur scrolle vers le bas, la carte passe au-dessus du header sticky.

```javascript
window.addEventListener('scroll', function () {
    var rect = mapCol.getBoundingClientRect();

    if (!isFixed && rect.top <= 0) {
        // La carte quitte le viewport → on la fixe en haut
        mapWrapper.style.position = 'fixed';
        mapWrapper.style.top = '0';
        mapWrapper.style.zIndex = '100'; // > header z-40
        isFixed = true;
        map.invalidateSize(); // recalcule la taille Leaflet
    } else if (isFixed && rect.top > 0) {
        // On remonte → la carte reprend sa position normale
        mapWrapper.style.position = '';
        isFixed = false;
        map.invalidateSize();
    }
});
```

Un `placeholder` div est inséré pour éviter le saut de layout quand la carte devient `fixed`.

---

## Route backend

```python
# app/routers/web.py
@router.get("/car/{car_id}/itineraire", response_class=HTMLResponse)
async def car_itineraire(request: Request, car_id: int, db: AsyncSession = Depends(get_db)):
    car = await car_service.get_car_by_id(db, car_id)
    if not car:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("itineraire.html", {
        "request": request,
        "car": car,
    })
```

**Pas de requête `cities`** : les villes ont été supprimées du template itinéraire — uniquement le pointage carte. `city_service` reste utilisé par la page d'accueil uniquement.

---

## Problèmes rencontrés et solutions

### 1. Formateur HTML cassait les templates Jinja2

**Problème** : VS Code reformatait `{{ car.daily_price }}` en deux lignes, rendant le template invalide.

**Solution** : Fichier `.vscode/settings.json` avec `"[html]": { "editor.formatOnSave": false }`.

### 2. Touch events bloqués sur iOS

**Problème** : `overflow: hidden` sur `.map-wrapper` bloquait les événements touch sur iOS Safari.

**Solution** : Suppression de `overflow: hidden`. La carte fonctionne sans.

### 3. Overlay bloquait les taps sur la carte

**Problème** : L'overlay d'instruction en `position: absolute` sur la carte interceptait les touches.

**Solution** : Bannière déplacée hors de la carte en `position: fixed`, avec `pointer-events: none` sur la zone de fond.

### 4. `map.on('click')` ne se déclenchait pas

**Solution** : Ajout de `tap: true, tapTolerance: 15` à l'initialisation de Leaflet.

---

## Compatibilité

| Plateforme | Support |
|------------|---------|
| iOS Safari | ✅ (overflow:hidden retiré + tap:true) |
| Android Chrome | ✅ |
| Android Firefox | ✅ |
| Desktop Chrome/Firefox/Safari | ✅ |
| Tablettes iPad/Android | ✅ |
