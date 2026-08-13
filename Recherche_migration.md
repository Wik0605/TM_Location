# Migration du moteur de recherche de lieux — TM_Location

Document de planification pour la migration long terme du moteur de recherche
d'adresses/villes utilisé dans les formulaires (itinéraire, réservation).

État actuel : **Photon public (photon.komoot.io)** — service tiers gratuit.
Cible : **Base locale Madagascar + fallback tiers** (Option 3).

---

## 1. Pourquoi migrer

### Problèmes de l'implémentation actuelle

- **Latence variable** : 500 ms à 2 s selon la charge du serveur komoot
- **Latence géographique** : +300 ms de RTT depuis Madagascar vers l'Europe
- **Dépendance externe critique** : une panne komoot casse la recherche
- **Aucune garantie SLA** : c'est un service gratuit, komoot peut le couper
- **Bruit international** : Photon retourne parfois des résultats hors Madagascar
- **Pas de contrôle des données** : impossible d'ajouter des POI métier
  (agences de location, parkings partenaires, hôtels)

### Ce qu'on gagne avec l'Option 3

| Critère | Avant (Photon public) | Après (base locale + fallback) |
|---|---|---|
| Latence typique | 500-2000 ms | **< 30 ms** |
| Coût à 100k utilisateurs | 0 € (mais risque) | 0 € (fiable) |
| Contrôle données | Aucun | Total |
| Ajout de POI métier | Impossible | Possible |
| Résilience | Dépend de komoot | Autonome |
| Optimisation Madagascar | Non | Oui |

---

## 2. Architecture cible

```
┌────────────────────────────────────────────────────┐
│  Utilisateur tape "Antan..." dans un formulaire    │
└────────────────────┬───────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │  1. Endpoint FastAPI    │
        │     /api/search?q=...   │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  2. PostgreSQL local    │  ← < 20 ms
        │     - Table places      │     recherche
        │     - Index pg_trgm     │     floue rapide
        │     - Données OSM MG    │
        └────────────┬────────────┘
                     │ si aucun résultat
        ┌────────────▼────────────┐
        │  3. Fallback Photon     │  ← rare
        │     (ou API tierce)     │
        └─────────────────────────┘
```

---

## 3. Composants à mettre en place

### 3.1 Import des données OSM Madagascar

**Source** : https://download.geofabrik.de/africa/madagascar.html
- Fichier `madagascar-latest.osm.pbf` (~150 Mo)
- Contient tous les nodes, ways, POI de Madagascar
- Mis à jour quotidiennement par Geofabrik

**Outil d'import** : `osm2pgsql`
- Convertit le PBF en tables PostgreSQL
- Installation : `brew install osm2pgsql` (dev), `apt install osm2pgsql` (prod)

**Schéma cible** :
```sql
CREATE TABLE places (
    id BIGINT PRIMARY KEY,
    osm_type CHAR(1),           -- 'N' node, 'W' way, 'R' relation
    name TEXT NOT NULL,
    name_normalized TEXT,       -- sans accents, minuscules (pour recherche)
    place_type TEXT,            -- city, town, village, suburb, poi
    admin_level INT,            -- 4=région, 6=district, 8=commune
    city TEXT,                  -- ville parente
    district TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    bbox_west DOUBLE PRECISION,
    bbox_east DOUBLE PRECISION,
    bbox_south DOUBLE PRECISION,
    bbox_north DOUBLE PRECISION,
    popularity INT DEFAULT 0,   -- score pour trier les résultats
    tags JSONB,                 -- tags OSM bruts (extension future)
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Extension pour recherche floue rapide
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Index de recherche
CREATE INDEX idx_places_name_trgm ON places USING gin (name_normalized gin_trgm_ops);
CREATE INDEX idx_places_popularity ON places (popularity DESC);
CREATE INDEX idx_places_type ON places (place_type);
```

### 3.2 Table pour POI métier (indépendante d'OSM)

```sql
CREATE TABLE business_places (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    name_normalized TEXT,
    category TEXT,              -- 'agence', 'parking_partenaire', 'hotel_partenaire'
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    partner_id INT,             -- FK vers un futur système de partenaires
    priority INT DEFAULT 100,   -- toujours en tête des résultats
    active BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_business_name_trgm ON business_places USING gin (name_normalized gin_trgm_ops);
```

### 3.3 Endpoint FastAPI

**Nouveau fichier** : `app/routers/search.py`

```python
from fastapi import APIRouter, Query
from sqlalchemy import text
from app.database import get_session

router = APIRouter(prefix="/api", tags=["search"])

@router.get("/search")
async def search_places(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(10, ge=1, le=20),
):
    normalized = normalize_query(q)  # sans accents, minuscule

    # 1. POI métier prioritaires
    # 2. Places OSM triées par similarité + popularité
    # 3. Fallback Photon uniquement si aucun résultat local

    async with get_session() as s:
        rows = await s.execute(text("""
            SELECT id, name, city, district, lat, lon,
                   bbox_west, bbox_east, bbox_south, bbox_north,
                   similarity(name_normalized, :q) AS score
            FROM places
            WHERE name_normalized % :q
            ORDER BY score DESC, popularity DESC
            LIMIT :limit
        """), {"q": normalized, "limit": limit})

        results = rows.mappings().all()

    if not results:
        results = await fallback_photon(q)

    return {"results": results}
```

### 3.4 Frontend

**Modifier** : `static/js/itineraire/search.js`
- Remplacer `PHOTON_URL` par `/api/search`
- Adapter le parsing de la réponse (format unifié)
- Garder le debounce + le cache mémoire

### 3.5 Job de mise à jour mensuelle

**Nouveau fichier** : `scripts/update_osm.sh`

```bash
#!/bin/bash
set -e
cd /var/data/osm
curl -O https://download.geofabrik.de/africa/madagascar-latest.osm.pbf
osm2pgsql -d tm_location -U tm_user \
    --create --slim --hstore \
    --style /path/to/custom.style \
    madagascar-latest.osm.pbf
```

**Cron** : `0 3 1 * *` (le 1er de chaque mois à 3h du matin)

---

## 4. Plan d'implémentation (4 semaines)

### Semaine 1 — Préparation données
- [ ] Installer `osm2pgsql` en dev
- [ ] Télécharger extrait Madagascar Geofabrik
- [ ] Créer schéma `places` + `business_places`
- [ ] Écrire script d'import et le tester en local
- [ ] Valider les volumes (nombre de lignes, taille disque)

### Semaine 2 — Backend
- [ ] Créer `app/routers/search.py`
- [ ] Ajouter fonction `normalize_query()` (accents, casse)
- [ ] Implémenter la requête SQL avec `pg_trgm`
- [ ] Ajouter le fallback Photon (garder l'URL actuelle)
- [ ] Tests unitaires sur des cas typiques
- [ ] Mesurer les latences (objectif < 50 ms p95)

### Semaine 3 — Frontend + intégration
- [ ] Adapter `search.js` pour appeler `/api/search`
- [ ] Uniformiser le format de résultat (title, sub, coords, bbox)
- [ ] Ajouter cache mémoire côté client (10 dernières requêtes)
- [ ] Tester sur mobile (réseau lent)
- [ ] Rollback plan : garder Photon en flag env `USE_LOCAL_SEARCH=true/false`

### Semaine 4 — Production
- [ ] Setup `osm2pgsql` sur serveur prod
- [ ] Import initial (peut prendre 30-60 min)
- [ ] Cron de mise à jour mensuelle
- [ ] Monitoring : latence endpoint, taux de fallback
- [ ] Documentation d'exploitation (que faire si un import échoue)

---

## 5. Points d'attention

### Sécurité
- Endpoint `/api/search` **public** (comme la carte) mais **rate-limiter** (ex: 30 req/min/IP)
- Valider `q` (longueur, caractères) pour éviter injection SQL même via ORM

### Performance
- `pg_trgm` avec index GIN → recherche floue instantanée jusqu'à plusieurs millions de lignes
- Prévoir `VACUUM ANALYZE places` après chaque import
- Si trop de résultats : ajouter filtre par proximité (distance à la position utilisateur)

### Qualité des données
- OSM contient parfois des noms bizarres ("Inconnu", tests, etc.)
- Prévoir une table `places_blacklist` pour cacher certains IDs OSM
- Alternative : script de nettoyage post-import

### Fallback Photon
- Le garder actif au moins 6 mois après migration
- Logger chaque appel fallback pour détecter les données OSM manquantes
- Objectif : < 5 % de fallback à terme

---

## 6. Références utiles

- **Geofabrik Madagascar** : https://download.geofabrik.de/africa/madagascar.html
- **osm2pgsql docs** : https://osm2pgsql.org/doc/manual.html
- **pg_trgm** : https://www.postgresql.org/docs/current/pgtrgm.html
- **Photon (fallback)** : https://github.com/komoot/photon
- **Nominatim (alternative auto-hébergement)** : https://nominatim.org/

---

## 7. Alternatives évaluées et rejetées

### Google Places / Mapbox / HERE API
- Rejeté : coût qui explose (~500-2000 $/mois à 10k utilisateurs actifs)
- Rejeté : vendor lock-in
- Rejeté : données Madagascar souvent moins bonnes qu'OSM

### Auto-hébergement Photon/Nominatim mondial
- Rejeté : infrastructure lourde (8-16 Go RAM, 100 Go disque)
- Rejeté : overkill pour un usage 100 % Madagascar
- Rejeté : complexité DevOps disproportionnée

### Garder Photon public en production
- Rejeté : dépendance critique à un service tiers gratuit sans SLA
- Rejeté : performance médiocre depuis Madagascar
- Rejeté : impossible d'ajouter des POI métier

---

## 8. Décision d'activation

Cette migration devient prioritaire quand **une** des conditions est remplie :

- [ ] 500 utilisateurs actifs mensuels atteints
- [ ] Retours utilisateurs récurrents sur la lenteur de la recherche
- [ ] Panne komoot ayant impacté la production
- [ ] Besoin d'ajouter des POI métier (partenariats)

En attendant, mesures palliatives sur le code actuel :
- Debounce réduit à 200 ms
- Cache mémoire des 10 dernières recherches côté client
