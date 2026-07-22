# Calcul d'itinéraire — Analyse et alternatives

## 1. Comment ça marche actuellement

Le code (`static/js/itineraire.js`) essaie **dans l'ordre** :

1. **BRouter** (https://brouter.de) — routeur libre, calcule un vrai trajet routier
2. **OSRM** (https://router.project-osrm.org) — autre routeur libre, vrai trajet routier
3. **Haversine (fallback local)** — SEULEMENT si les 2 premiers échouent

Donc si BRouter ou OSRM répondent, on a la vraie distance routière (précise). Le fallback Haversine ne s'active QUE si les deux serveurs sont morts/inaccessibles.

Quand le fallback s'active, une **note orange "Distance calculée à vol d'oiseau"** s'affiche pour prévenir l'utilisateur (`itineraire.js:249`).

## 2. C'est quoi la formule Haversine ?

Formule mathématique de géométrie sphérique qui calcule la distance **en ligne droite entre 2 points GPS sur la surface de la Terre** (en tenant compte de la courbure du globe).

```
Point A (lat1, lon1) ───► Point B (lat2, lon2)
         distance à vol d'oiseau (km)
```

**Aucun appel réseau** — juste des maths locales (sin, cos, arctan). Marche même hors ligne.

## 3. Pourquoi le × 1.3 ?

Une route ne va jamais en ligne droite : elle contourne montagnes, lacs, suit les axes existants. Le facteur **1.3 est une estimation empirique** :

- Route très directe (autoroute) : ×1.1 à ×1.2
- Route normale : ×1.3 à ×1.4
- Route très sinueuse (montagne, RN7 Madagascar) : ×1.5 à ×2.0

**Donc oui, si le fallback s'active, l'estimation carburant peut être fausse** — sous-estimée sur routes sinueuses, sur-estimée sur autoroute.

## 4. Solutions alternatives (par ordre de recommandation)

### Option A — Auto-héberger OSRM (meilleure long terme)
Installer OSRM sur ton serveur avec les données OpenStreetMap de Madagascar (~200 Mo). Zéro dépendance externe, ultra rapide, précis. Setup Docker : ~1h de config, tourne ensuite indéfiniment gratuitement.

### Option B — API payante fiable
- **Google Maps Distance Matrix API** : très précis, ~5$ pour 1000 requêtes, fonctionne parfaitement à Madagascar
- **Mapbox Directions API** : gratuit jusqu'à 100k requêtes/mois, très fiable
- **GraphHopper** : offre gratuite 500 req/jour

### Option C — Améliorer le fallback Haversine avec un facteur adaptatif
Utiliser un multiplicateur variable selon la région/distance :
- Trajets urbains Tana : ×1.4
- RN7 (Tana → Fianarantsoa) : ×1.5
- Côte : ×1.3

Mieux que ×1.3 fixe mais reste une estimation.

### Option D — Retry + timeout intelligents sur BRouter/OSRM
Réessayer 2-3 fois avec timeout court avant de tomber en fallback. Les serveurs publics ont parfois juste des micro-coupures.

### Option E — Combo : Mapbox en principal + Haversine en secours
Fiabilité Mapbox (gratuit dans la volumétrie de démarrage) + Haversine comme filet de sécurité.

## Recommandation

Pour le stade actuel (app en dev, faible trafic) : **Option E — Mapbox**. Setup en 30 min, 100k requêtes gratuites/mois = largement assez, élimine complètement le problème de fiabilité BRouter/OSRM depuis Madagascar. Passer à OSRM auto-hébergé (Option A) plus tard si dépassement du quota.
