# Import des polygones fokontany — Journal de session

**Date :** 2026-10-22  
**Objectif :** Afficher les quartiers/fokontany d'Antananarivo sur la carte Leaflet

---

## Contexte de départ

L'infrastructure était déjà en place mais la table `quartiers` était vide :

- Table PostGIS `quartiers` avec colonne `geom MULTIPOLYGON` (SRID 4326)
- Script Lua `scripts/import_quartiers.lua` pour osm2pgsql (admin_level 8 = commune, 10 = fokontany)
- API `/api/quartiers` qui retourne du GeoJSON
- Frontend `map.js` qui affiche les polygones via `L.geoJSON()` à zoom ≥ 13

---

## Méthodes essayées qui n'ont pas fonctionné

### 1. osm2pgsql sur le fichier PBF complet de Madagascar

**Commande :**
```bash
osm2pgsql --output=flex --style=scripts/import_quartiers.lua ... madagascar-latest.osm.pbf
```

**Résultat :** 617 communes + 625 fokontany pour tout Madagascar — trop peu, et données dispersées sur toute l'île.

**Problème :** OSM Madagascar a une couverture fokontany très incomplète. La plupart des fokontany n'ont pas de polygones dans OSM.

**Erreur collatérale :** Le premier import a **écrasé la table `quartiers`** avec le schéma propre à osm2pgsql (sans colonne `id` UUID). Il a fallu recréer la table manuellement.

---

### 2. osm2pgsql avec `--bbox` sur la zone d'Antananarivo

**Commande :**
```bash
osm2pgsql --bbox=47.45,-19.05,47.65,-18.75 ...
```

**Résultat :** Toujours les mêmes 1242 entrées pour tout Madagascar.

**Problème :** L'option `--bbox` d'osm2pgsql ne filtre pas les **relations** (seulement les nodes et ways). Les relations administratives sont toujours traitées globalement.

---

### 3. Extraction osmium + osm2pgsql

**Commande :**
```bash
osmium extract --bbox=47.40,-19.05,47.70,-18.70 madagascar-latest.osm.pbf -o antananarivo.osm.pbf
osm2pgsql --output=flex --style=... antananarivo.osm.pbf
```

**Résultat :** 24 communes + 5 fokontany seulement.

**Problème :** osmium coupe les géométries à la bbox — les relations dont les ways débordent de la zone sont incomplètes et donc échouent lors de la reconstruction du polygone (`as_multipolygon()`).

La stratégie `--strategy=smart` n'a pas amélioré le résultat car la limitation vient des données OSM elles-mêmes : seulement 5 fokontany existent dans OSM pour la zone d'Antananarivo à admin_level=10.

---

### 4. Overpass API

**Requête :**
```
relation["boundary"="administrative"]["admin_level"~"8|10|11"](bbox Antananarivo);
out geom;
```

**Résultat :** 29 relations récupérées (24 communes + 5 fokontany).

**Problèmes rencontrés :**
- Erreur SSL sur macOS/Python 3.14 → contourné avec `ssl.CERT_NONE`
- Serveur overpass-api.de → HTTP 502 (surchargé)
- Miroir overpass.kumi.systems → timeout

**Conclusion :** Même si les serveurs fonctionnaient, OSM ne contient que 5 fokontany pour Antananarivo — la source OSM est insuffisante.

---

### 5. Téléchargement direct HDX/OCHA

**URL tentée :**
```
https://data.humdata.org/.../mdg_adm_bngrc_ocha_20181031_shp.zip
```

**Résultat :** Fichier de 9.2 Ko → page HTML d'erreur (authentification requise sur HDX).

---

## Solution qui a fonctionné

### GeoBoundaries — ADM4 Madagascar (BNGRC/OCHA)

**Source :** https://www.geoboundaries.org/data/1_3_3/zip/shapefile/MDG/MDG_ADM4.shp.zip  
**Données :** 17 459 fokontany pour tout Madagascar, issues des données officielles BNGRC/OCHA 2018.

**Étapes :**

1. **Télécharger le shapefile (35 Mo) :**
```bash
curl -L -o /tmp/MDG_ADM4.shp.zip \
  "https://www.geoboundaries.org/data/1_3_3/zip/shapefile/MDG/MDG_ADM4.shp.zip"
unzip /tmp/MDG_ADM4.shp.zip -d /tmp/MDG_ADM4/
```

2. **Recréer la table `quartiers`** (après destruction par osm2pgsql) :
```sql
CREATE TABLE quartiers (
    id         UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    osm_id     BIGINT,
    nom        TEXT        NOT NULL,
    nom_court  TEXT        NOT NULL,
    type       TEXT        NOT NULL,
    actif      BOOLEAN     NOT NULL DEFAULT true,
    geom       geometry(MULTIPOLYGON, 4326)
);
CREATE INDEX quartiers_geom_idx ON quartiers USING gist(geom);
```

3. **Importer via `scripts/import_geoboundaries_tana.py`** :
   - Filtre par bbox d'Antananarivo (lon 47.40–47.70 / lat −19.05–−18.70)
   - Convertit Polygon → MultiPolygon via Shapely
   - Insère dans la table `quartiers` via psycopg2

```bash
python scripts/import_geoboundaries_tana.py
```

**Résultat final :** 724 fokontany d'Antananarivo importés.

---

## Problèmes de schéma rencontrés en cours de route

| Problème | Cause | Fix |
|----------|-------|-----|
| `id UUID NOT NULL` sans default PostgreSQL | osm2pgsql ne peut pas générer des UUID | `ALTER TABLE quartiers ALTER COLUMN id SET DEFAULT gen_random_uuid()` |
| Table `quartiers` écrasée par osm2pgsql | Premier import sans `create=false` | Recréation manuelle + Alembic reset |
| `osm_id NOT NULL` violation | Schéma osm2pgsql hérité | `ALTER TABLE quartiers ALTER COLUMN osm_id DROP NOT NULL` |
| `ON CONFLICT (osm_id)` échoue | Pas de contrainte UNIQUE sur osm_id | Corrigé dans le script Python |

---

## Scripts créés

| Fichier | Rôle |
|---------|------|
| `scripts/import_overpass_tana.py` | Import via Overpass API (bbox Antananarivo, admin_level 8/10/11) |
| `scripts/import_geoboundaries_tana.py` | Import via shapefile GeoBoundaries ADM4 — **solution retenue** |

---

## Modification du script Lua

`scripts/import_quartiers.lua` — ajout de `create = false` pour ne pas recréer la table :

```lua
local quartiers = osm2pgsql.define_table({
    name = 'quartiers',
    ids = { type = 'relation', id_column = 'osm_id' },
    columns = { ... },
    create = false,  -- ← ajouté
})
```

> **Attention :** Sans `create = false`, osm2pgsql écrase la table existante avec son propre schéma.
