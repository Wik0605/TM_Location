# Affichage des noms de quartiers sur la carte

## Contexte

Sur la carte Leaflet de l'app (`static/js/itineraire/map.js`), les noms de
quartiers (fokontany) n'apparaissent pas. L'investigation a montré qu'aucun
code ni donnée ne les affiche actuellement — seuls les labels des tuiles
Carto `voyager_only_labels` sont visibles, et ce style n'inclut pas les
fokontany de Madagascar.

Objectif : afficher les noms de quartiers sur la carte à partir des données
OSM, tout en gardant la main sur les noms et le périmètre affiché.

---

## Les 3 approches possibles

### A. Utiliser les tuiles OSM telles quelles

Les tuiles Carto actuelles contiennent déjà des noms OSM, mais :

- Le style `voyager_only_labels` n'affiche **pas les fokontany**
  (niveau admin trop fin pour ce style).
- Aucun contrôle sur le style, le contenu ou le zoom d'apparition.

**Limite** : dépendance totale au choix de Carto.

### B. Interroger OSM en direct via Overpass API

```overpassql
[out:json];
relation["admin_level"="10"](area:Madagascar);
out geom;
```

- Zéro import, toujours à jour.
- Lent, quotas publics, pas fiable en prod.
- Aucune possibilité de corriger ou enrichir les noms.

### C. Importer OSM dans la base PostgreSQL (recommandé)

```
OSM (Overpass / extrait .osm.pbf de Madagascar)
       ↓  import une seule fois
Table PostgreSQL `quartiers`
       ↓
Endpoint /api/quartiers
       ↓
Carte Leaflet
```

On utilise bien les données OSM, mais on en garde une **copie locale
maîtrisée**.

**Avantages combinés :**

- Profite du travail OSM (polygones + noms existants).
- Correction / ajout / masquage de quartiers sans toucher à OSM.
- Rapide (base locale) et fiable (pas de dépendance réseau).
- Re-synchronisation possible via script d'update.
- Permet de lier la logique métier : voitures par quartier, tarifs
  livraison, zones desservies, etc.

**Analogie** : télécharger un modèle Word gratuit — on part du modèle (OSM)
mais on l'adapte dans son propre fichier.

---

## Ce que l'approche C permet de contrôler

1. **Nom affiché** — orthographe libre (`Analakely` → `Analakely Centre`),
   malgache / français au choix.
2. **Périmètre** — masquer, fusionner, ajouter des zones hors OSM
   (ex. "Zone aéroport Ivato").
3. **Métadonnées** — enrichir librement :

   | id | nom              | nom_court | type      | actif | prix_zone |
   |----|------------------|-----------|-----------|-------|-----------|
   | 1  | Analakely Centre | Analakely | fokontany | true  | A         |
   | 2  | Ivandry          | Ivandry   | quartier  | true  | B         |

4. **Modification sans redéploiement** — un `UPDATE` SQL suffit.
5. **Logique métier** — jointures avec voitures, réservations, tarifs.

---

## Plan d'exécution (quand prêt à implémenter)

1. **Préparer PostGIS** sur la base PostgreSQL
   (`CREATE EXTENSION postgis;`).
2. **Modèle SQLAlchemy** `Quartier` dans `app/models/` : `id`, `nom`,
   `nom_court`, `type`, `actif`, `source_osm_id`, `geometrie` (polygon).
3. **Script d'import** depuis Overpass (ou extrait Geofabrik Madagascar) →
   insertion dans la table `quartiers`.
4. **Endpoint** `GET /api/quartiers?bbox=minLon,minLat,maxLon,maxLat`
   renvoyant un GeoJSON filtré.
5. **Côté front** (`static/js/itineraire/map.js`) : fetch sur
   `map.on('moveend')`, overlay `L.geoJSON` avec `bindTooltip` pour les
   noms.

### Fichiers concernés

- `app/models/` — nouveau modèle `Quartier`.
- `app/routers/` ou `app/client/itineraire/routes.py` — nouvel endpoint.
- `app/database.py` — activation PostGIS.
- `scripts/` — script d'import OSM (à créer).
- `static/js/itineraire/map.js` — overlay quartiers.

### Vérification end-to-end

- `curl /api/quartiers?bbox=47.4,-18.95,47.6,-18.85` renvoie du GeoJSON
  valide avec ≥ 1 feature.
- Ouvrir la carte dans le navigateur, zoomer sur Antananarivo, vérifier
  l'apparition des noms de quartiers en tooltip ou label permanent.
- Modifier un `nom` en base via SQL et recharger → changement visible.

---

## Prérequis à valider avant implémentation

- PostGIS installé sur le PostgreSQL local.
- Choix de la source d'import : Overpass live vs extrait Geofabrik
  `.osm.pbf`.
- Périmètre géographique : Antananarivo seul ou Madagascar entier.
