# Cartographie & calcul d'itinéraire — TM_Location

Doc de référence sur le système de calcul de distance/itinéraire.
Pour l'historique de la migration front → back, voir `Carte_migration.md`.

---

## 1. État actuel du système

### Flux (post-migration, en place depuis 2026-08-04)

```
Client clique "Calculer"
  → JS envoie SEULEMENT les waypoints à FastAPI
  → FastAPI appelle le routeur côté serveur (cascade)
  → FastAPI renvoie {distance, polyline, token}
  → JS affiche le résultat + stocke le token
  → POST /reserver avec le token
  → Le back relit la distance depuis son cache (le nombre envoyé
    par le client est ignoré)
```

**Clé de sécurité** : le client n'envoie jamais un nombre de km, seulement des points GPS. Le serveur est seul maître du calcul, et signe le résultat avec un token éphémère (UUID, TTL 15 min).

### Cascade de routeurs

`app/services/routing_service.py` essaie dans l'ordre :

1. **BRouter** (`brouter.de`) — routeur libre, vrai trajet routier
2. **OSRM** (`router.project-osrm.org`) — routeur libre, vrai trajet routier
3. **Haversine local** — SEULEMENT si les 2 précédents échouent

Si le fallback Haversine s'active, une note orange "Distance calculée à vol d'oiseau" prévient l'utilisateur côté front.

---

## 2. Détails techniques

### Formule Haversine

Géométrie sphérique : distance **en ligne droite** entre 2 points GPS sur la surface de la Terre (courbure incluse).

```
Point A (lat1, lon1) ───► Point B (lat2, lon2)
         distance à vol d'oiseau (km)
```

**Aucun appel réseau** — juste sin/cos/arctan. Marche hors ligne.

### Le facteur × 1.3

Une route ne va jamais en ligne droite : elle contourne montagnes, lacs, suit les axes existants. Le facteur 1.3 est une estimation empirique :

| Type de route | Facteur |
|---|---|
| Autoroute (très directe) | ×1.1 à ×1.2 |
| Route normale | ×1.3 à ×1.4 |
| Route sinueuse (RN7 Madagascar) | ×1.5 à ×2.0 |

**Conséquence** : si le fallback Haversine s'active, l'estimation carburant peut être fausse — sous-estimée sur routes sinueuses, sur-estimée sur autoroute.

---

## 3. Évolutions possibles

### 3.1 Améliorer le routeur

**Option A — Auto-héberger OSRM (meilleure long terme).**
Installer OSRM sur le serveur avec les données OpenStreetMap de Madagascar (~200 Mo). Zéro dépendance externe, ultra rapide, précis. Setup Docker : ~1h, tourne ensuite gratuitement.

**Option B — API payante fiable.**
- **Google Maps Distance Matrix** : très précis, ~5$ / 1000 requêtes.
- **Mapbox Directions** : gratuit jusqu'à 100k req/mois.
- **GraphHopper** : gratuit 500 req/jour.

**Option C — Facteur Haversine adaptatif.**
Multiplicateur variable selon région : Tana urbain ×1.4, RN7 ×1.5, côte ×1.3. Mieux que ×1.3 fixe, mais reste une estimation.

**Option D — Retry + timeout intelligents.**
Réessayer 2-3 fois avec timeout court sur BRouter/OSRM avant de tomber en Haversine. Utile pour les micro-coupures.

**Option E (recommandée aujourd'hui) — Mapbox principal + Haversine en secours.**
Fiabilité Mapbox (largement dans le quota gratuit) + Haversine comme filet. Setup ~30 min. Migrer vers OSRM self-hosted plus tard si dépassement.

### 3.2 Durcir le back

**Cache Redis (ou équivalent).**
Aujourd'hui le cache token est un dict en mémoire. Deux clients qui calculent Tana → Antsirabe = 2 appels BRouter. Avec un cache : 1 seul appel, tous les suivants instantanés. Utile aussi pour survivre à un redémarrage sans invalider les tokens en cours.

**Validation des waypoints.**
Le client envoie des coordonnées GPS — il peut envoyer n'importe quoi :
- Points au milieu de l'océan
- 500 waypoints pour DoS le serveur
- Waypoint New York + Tokyo = calcul énorme

À ajouter côté API :
- Limite du nombre de waypoints (max 10)
- Bounding box Madagascar : rejeter si `lat` hors `[-25.7, -11.9]` ou `lon` hors `[43.2, 50.5]`
- Timeout sur l'appel BRouter/OSRM (5s max)

**Rate limit par session/IP.**
Un bot qui spam `/api/voitures/{id}/itineraire/calculer` → l'IP du serveur bannie par BRouter → toute l'app tombe. À protéger via `slowapi` (même dépendance que celle prévue pour l'admin login).

**Token JWT signé au lieu d'UUID + dict.**
Actuellement le token est un UUID stocké en mémoire. Un JWT signé permettrait :
- Aucun état serveur (le token porte la distance)
- Survit aux redémarrages
- Revocation possible via une liste noire courte

---

## 4. Défis résiduels non techniques

- **Offline / mauvaise 3G** : sans back accessible, aucun calcul possible. Peu grave car la réservation elle-même nécessite le back.
- **Coût serveur** : chaque calcul consomme CPU/RAM. Léger, mais ×1000 clients ça compte.
- **Dépendance renforcée au back** : si FastAPI tombe, plus aucun calcul possible.

---

## 5. Verdict

L'architecture actuelle est solide et sécurisée. Les prochaines évolutions sont **optionnelles** et à déclencher selon le trafic :

| Effort | Chantier |
|---|---|
| ~30 min | Mapbox en principal (Option E) |
| ~1 jour | Cache Redis + validation waypoints + rate limit |
| ~1 semaine | OSRM self-hosted en plus |

**Question de priorisation** : facturation au km dans les 6 prochains mois ?
- Oui → prioriser durcissement back (cache Redis, validation, rate limit)
- Non → garder en note, avancer sur OAuth / Mobile Money (impact business immédiat)


 