# Auto-héberger ma carte OSM — Comprendre les principes

Document pédagogique — auto-hébergement du fond de carte de `TM_Location`,
en commençant par Antananarivo, avec possibilité d'ajouter des POI métier
(magasins, restaurants, agences).

**Ce document explique le principe et le stack, pas les étapes d'implémentation.**
Il complète `Recherche_migration.md` (qui traite de la recherche d'adresses).

---

## Contexte

Aujourd'hui `TM_Location` affiche une carte Leaflet qui charge :
- des **tuiles satellite Esri** (`server.arcgisonline.com`)
- des **labels CartoDB** (`basemaps.cartocdn.com`)
- une **recherche via Photon public** (komoot)

→ Trois dépendances externes gratuites, aucune SLA, aucune donnée métier possible dessus.

**Objectif** : héberger soi-même le fond de carte pour :
1. Ne plus dépendre de services tiers
2. Ajouter ses propres POI (magasins, restaurants, agences, parkings partenaires)
3. Améliorer la donnée en interne (corrections locales de Tana)
4. Commencer petit (Antananarivo) puis étendre

---

## 1. Le principe d'une carte web (à comprendre d'abord)

Une carte web n'est **pas une image**. C'est un puzzle de **tuiles** (`tiles`) — de petits carrés de 256×256 pixels — qu'un client (Leaflet, MapLibre) assemble à l'écran en fonction :

- **z** = niveau de zoom (0 = monde entier, 19 = niveau rue)
- **x, y** = coordonnées de la tuile dans une grille

À chaque déplacement/zoom, le navigateur demande les tuiles manquantes à une URL du type :
`https://mon-serveur/tiles/{z}/{x}/{y}.png`

**Deux familles de tuiles** :

| | Raster (PNG/JPG) | Vectoriel (MVT/PBF) |
|---|---|---|
| Contenu | Image pré-rendue | Données géométriques + style appliqué côté client |
| Poids Tana zoom 0-19 | 2-5 Go | ~50-100 Mo |
| Style modifiable | Non (faut re-générer) | Oui, en direct dans le JS |
| Client JS | Leaflet | MapLibre GL JS (WebGL) |
| CPU serveur | Faible (fichier statique) | Faible aussi |
| Rotation/3D | Non | Oui |

**Le monde pro va aujourd'hui vers le vectoriel** (Mapbox, MapLibre, Protomaps). C'est ce que tu devrais viser à terme.

---

## 2. Le stack à maîtriser

### 2.1 Les données brutes : OpenStreetMap

- **Source unique** : https://download.geofabrik.de/africa/madagascar.html
- Fichier `madagascar-latest.osm.pbf` (~150 Mo, MAJ quotidienne)
- Contient TOUT : routes, bâtiments, POI, limites administratives
- Format `.pbf` = Protocol Buffer, binaire compact
- Pour Antananarivo seule : on peut extraire avec `osmium extract` (~10-20 Mo)

**Principe** : OSM = base de données mondiale collaborative. On télécharge un extrait, on l'importe dans PostgreSQL, on génère des tuiles à partir de là.

### 2.2 La base de données : PostgreSQL + PostGIS

- **PostGIS** = extension géo pour PostgreSQL (types `geometry`, index spatiaux `GIST`)
- **osm2pgsql** = outil qui lit un `.pbf` et remplit PostgreSQL avec les tables `planet_osm_point`, `planet_osm_line`, `planet_osm_polygon`
- C'est la MÊME base qui servira pour :
  - le rendu des tuiles
  - la recherche `/api/search` (déjà planifiée dans `Recherche_migration.md`)
  - tes POI métier (table séparée `business_places`)

**Principe à retenir** : une seule base PostGIS = carte + recherche + POI métier. Pas de duplication.

### 2.3 Le générateur de tuiles

Trois approches, du plus simple au plus flexible :

**A. Tuiles raster pré-générées (le plus simple)**
- Outil : `mod_tile` + `renderd` + `mapnik`, ou plus moderne `tilemaker`
- On génère UNE FOIS toutes les tuiles PNG de Tana (zoom 12→19) → dossier de fichiers
- Nginx sert les fichiers, point.
- Avantage : zéro CPU en production, simple à sauvegarder
- Inconvénient : re-générer prend des heures quand tu changes le style

**B. Tuiles vectorielles pré-générées (recommandé long terme)**
- Outil : `tilemaker` (lit directement le .pbf, produit un fichier `.mbtiles` ou `.pmtiles`)
- **PMTiles** = format récent, un SEUL fichier qui contient toutes les tuiles, servi par un simple bucket ou Nginx
- Style défini dans un JSON côté client (MapLibre)
- Avantage : ultra léger, style modifiable sans re-générer, hébergeable même sur un CDN statique

**C. Rendu dynamique à la demande**
- Outil : `martin` (Rust) ou `pg_tileserv`
- Génère la tuile à la volée depuis PostGIS quand elle est demandée
- Avantage : les modifs de POI apparaissent instantanément
- Inconvénient : consomme CPU/RAM en continu

**Recommandation** : **B (vectoriel + PMTiles + tilemaker + MapLibre)**. C'est le stack 2026 le plus léger et le plus évolutif. Mais il faut migrer Leaflet → MapLibre côté front.

### 2.4 Le serveur HTTP

- **Nginx** devant tout : sert les tuiles statiques, gère le cache, le HTTPS (Let's Encrypt)
- **Cache navigateur** : header `Cache-Control: public, max-age=2592000` (30 j) sur les tuiles
- **CORS** : autoriser ton domaine à charger les tuiles depuis le navigateur

### 2.5 Le client (front)

Deux options selon le choix 2.3 :
- Raster → **Leaflet** (déjà en place, aucun changement)
- Vectoriel → **MapLibre GL JS** (remplace Leaflet, ~200 Ko, WebGL)

### 2.6 Les POI métier (ta valeur ajoutée)

Table PostgreSQL séparée d'OSM, ne se fait jamais écraser par les MAJ :

```
business_places (id, name, category, lat, lon, description, photo_url,
                 owner_id, verified, priority, created_at)
```

Deux façons de les afficher :
- **Superposés en JS** : appel API `/api/pois?bbox=...` → markers Leaflet/MapLibre
- **Intégrés au rendu** : injectés dans la génération de tuiles (plus complexe, mais propre)

Le premier est largement suffisant pour commencer.

---

## 3. L'infrastructure (VPS dédié)

**Choix : VPS Hetzner ou Contabo** (rapport qualité/prix imbattable, data centers Europe = ~150 ms depuis Tana, acceptable pour du CDN statique).

**Dimensionnement pour Antananarivo seule** :

| Ressource | Besoin | Coût |
|---|---|---|
| CPU | 2 vCPU | inclus |
| RAM | 4 Go (import osm2pgsql confortable) | inclus |
| Disque | 40 Go SSD (PBF + PostGIS + tuiles) | inclus |
| Bande passante | 20 To/mois inclus généralement | inclus |
| **Total** | **~5-8 €/mois** | Hetzner CX22 ou Contabo VPS S |

**Pour Madagascar entière** : passer à 8 Go RAM / 80 Go SSD (~15 €/mois).

**Système** : Ubuntu 24.04 LTS, Docker Compose recommandé pour isoler PostgreSQL, tilemaker, Nginx.

---

## 4. Les principes/concepts à maîtriser

Dans l'ordre d'apprentissage :

1. **Systèmes de coordonnées** : WGS84 (lat/lon) vs Web Mercator (EPSG:3857). Toutes les tuiles web sont en Web Mercator. Comprendre les projections évite 90 % des bugs.

2. **Le schéma XYZ** : comment `z/x/y` correspond à un carré au sol. Une tuile z=15 fait ~1 km × 1 km à Tana.

3. **Formats OSM** : `.osm.pbf` (compact), `.osm.xml` (lisible), `.osm.bz2` (obsolète). Toujours travailler en PBF.

4. **osm2pgsql en mode `--slim`** : garde les tables intermédiaires pour permettre les mises à jour incrémentales (`osm2pgsql-replication`).

5. **Le style de carte** : fichier CartoCSS (Mapnik) ou JSON MapLibre. C'est là que tu contrôles les couleurs, les icônes, la visibilité par zoom.

6. **Le cycle de vie des tuiles** : pré-génération → stockage → cache HTTP → invalidation quand la donnée change.

7. **La différence tuiles / recherche / POI métier** : trois systèmes indépendants qui partagent la même base PostGIS mais ont chacun leur endpoint et leur cycle de vie.

8. **Rate limiting et sécurité** : même des tuiles publiques doivent être protégées (referer check, quota par IP) pour éviter que quelqu'un pompe tout ton serveur.

---

## 5. Le chemin recommandé (progression pédagogique)

Pas une roadmap d'implémentation — une progression pour apprendre.

**Étape 1 — Comprendre en local (1 semaine)**
- Installer PostgreSQL + PostGIS sur ton Mac
- Télécharger `madagascar-latest.osm.pbf`
- Extraire Tana avec `osmium extract --bbox 47.4,-19.0,47.6,-18.8`
- Importer avec `osm2pgsql`
- Faire des requêtes SQL : "combien de restaurants dans Tana ?" (`SELECT count(*) FROM planet_osm_point WHERE amenity='restaurant'`)
- **But** : sentir la donnée dans tes doigts.

**Étape 2 — Générer des tuiles en local (1 semaine)**
- Installer `tilemaker`
- Générer un `.pmtiles` de Tana
- Ouvrir avec https://pmtiles.io pour visualiser
- Modifier un style MapLibre pour changer les couleurs
- **But** : comprendre le pipeline PBF → tuiles → rendu.

**Étape 3 — Louer un VPS et servir (1 semaine)**
- VPS Hetzner CX22
- Nginx + fichier `.pmtiles` + certificat Let's Encrypt
- Charger dans un HTML de test avec MapLibre
- **But** : servir tes propres tuiles sur un vrai domaine.

**Étape 4 — Intégrer à `TM_Location` (2 semaines)**
- Migrer Leaflet → MapLibre dans `static/js/itineraire/map.js`
- Remplacer les URL Esri par ton domaine
- Garder Esri en fallback pendant 3 mois
- **But** : mettre en prod sans casser l'app.

**Étape 5 — Ajouter les POI métier (ouvert)**
- Table `business_places`
- Endpoint FastAPI `/api/pois?bbox=...`
- Interface admin pour ajouter/modifier
- **But** : la valeur ajoutée que personne d'autre n'aura.

---

## 6. Ressources à lire (ordre pédagogique)

1. **Switch2OSM** — https://switch2osm.org/ — Le tutoriel de référence, écrit par les gens qui font OSM
2. **Tilemaker** — https://github.com/systemed/tilemaker — Lire le README
3. **MapLibre** — https://maplibre.org/maplibre-gl-js/docs/ — Le remplaçant open-source de Mapbox
4. **PMTiles** — https://protomaps.com/docs/pmtiles — Format de tuiles moderne
5. **Geofabrik** — https://download.geofabrik.de/africa/madagascar.html — Ta source de données

Un seul livre si tu veux : **"OpenStreetMap: Using and Enhancing the Free Map of the World"** (Ramm, gratuit en PDF).

---

## 7. Ce que ce document **ne fait pas**

- Il ne modifie **aucun fichier** de l'app
- Il ne propose pas de code à copier
- Il n'engage pas de dépense
- Il ne remplace pas `Recherche_migration.md` (qui reste valide pour la recherche `/api/search`)

Quand tu voudras passer à l'action, on écrira un vrai plan d'implémentation, étape par étape, avec le code adapté à `TM_Location`.

---

## 8. Question à te poser avant d'aller plus loin

- **Est-ce urgent ?** Non. Tant que Esri et Photon tiennent, l'app fonctionne.
- **Combien d'utilisateurs actifs ?** En-dessous de 500/mois, ce n'est pas rentable en temps.
- **Quel gain réel ?** Le vrai gain = les POI métier. Le fond de carte, c'est du confort.

Recommandation personnelle : **fais d'abord la migration recherche** (`Recherche_migration.md`), tu apprendras 80 % du stack (PostGIS, osm2pgsql, PBF) sans avoir besoin de louer un VPS. Le tile-server viendra naturellement après.
