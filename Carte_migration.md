# Documentation — Migration du calcul d'itinéraire vers le backend

## Contexte

Aujourd'hui, ton app calcule les distances **côté navigateur** (JS → brouter.de). Deux problèmes :

1. **Sécurité / facturation** : un client peut modifier la distance dans son navigateur (F12) et payer moins. Le back ne peut pas vérifier.
2. **Bug actuel** : la distance calculée dans le JS **n'est jamais envoyée** au backend. Le champ `itineraire_distance_km` en base est toujours `NULL` (vérifié dans `web.py:99` — le backend l'attend mais le formulaire ne l'envoie pas).

La migration résout donc **deux problèmes en même temps** : brancher la distance ET la rendre incontestable.

---

## Principe général

> **Le client n'envoie plus un nombre, il envoie des points GPS. Le serveur seul calcule et mémorise la distance.**

Au moment de la réservation, le client renvoie juste un **token** (jeton d'identification) que le serveur a émis. Le serveur retrouve la distance qu'il avait lui-même calculée. Impossible à truquer.

### Analogie du taxi

- **Avant** : le client dit "j'ai fait 50 km, voilà l'argent". Le chauffeur doit le croire.
- **Après** : le chauffeur (serveur) allume son propre compteur, note la distance, donne un **ticket numéroté** au client. À l'arrivée, le client rend le ticket, le chauffeur lit sa note. Impossible de mentir.

Le "ticket" = le token éphémère stocké côté serveur.

---

## Progression de la migration

| Étape | Statut | Fichier |
|-------|--------|---------|
| 1. Service backend (calcul + cache token) | ✅ **Fait** | `app/services/routing_service.py` |
| 2. Endpoint API `/api/.../calculer` | ⏳ À faire | `app/routers/itineraire_api.py` |
| 3. Adapter le JS pour appeler l'API | ⏳ À faire | `static/js/itineraire/routing.js` |
| 4. Ajouter input hidden `itinerary_token` | ⏳ À faire | `app/templates/voiture_detail.html` |
| 5. Vérifier le token dans `/reserver` | ⏳ À faire | `app/routers/web.py` |
| 6. Tests bout en bout | ⏳ À faire | — |

---

## ÉTAPE 1 — Service backend (fait)

### Fichier créé : `app/services/routing_service.py`

Ce fichier contient toute la logique côté serveur pour calculer une distance et mémoriser le résultat.

### Structure en 3 blocs

#### Bloc 1 — Validation des waypoints

Fonction : `_valider_waypoints(waypoints)`

Rôle : rejeter les demandes abusives avant tout appel réseau.

Règles :
- Minimum 2 points, maximum 10 points
- Latitude dans `[-25.7, -11.9]` (bornes de Madagascar)
- Longitude dans `[43.2, 50.5]` (bornes de Madagascar)

Si une règle échoue → lève `RoutingError` (sera transformée en HTTP 400 dans l'étape 2).

**Pourquoi côté serveur ?** Un client malin peut envoyer 500 waypoints ou des coordonnées à New York pour faire ramer BRouter. La validation JS ne suffit pas — seul le serveur peut refuser.

#### Bloc 2 — Calcul en cascade

Fonction principale : `async def calculer_itineraire(waypoints)`

Elle tente 3 sources dans l'ordre :

1. **BRouter** (`_appeler_brouter`) : moteur de routing spécialisé, très précis pour la voiture. Externe → peut être lent ou tomber.
2. **OSRM** (`_appeler_osrm`) : router public alternatif. Backup si BRouter échoue.
3. **Haversine × 1.3** (`_fallback_haversine`) : formule mathématique locale (calcul à vol d'oiseau + 30% pour approximer les routes). Toujours disponible, jamais bloquant.

Chaque appel externe a un **timeout de 5 secondes** (`HTTP_TIMEOUT = 5.0`). Si BRouter met 10 secondes → on passe à OSRM sans attendre.

Chaque source retourne le même format :
```python
{
    "distance_km": 127.3,
    "polyline": {...geojson...},
    "source": "brouter"  # ou "osrm" / "haversine"
}
```

**Pourquoi la cascade ?** Ton serveur ne doit **jamais** planter parce que BRouter est en maintenance. Haversine garantit qu'on renvoie toujours un résultat, même dégradé.

#### Bloc 3 — Cache token (le "ticket numéroté")

Deux fonctions publiques :

- `emettre_token(distance_km, waypoints, voiture_id) -> str`
  Génère un UUID (ex: `"a1b2c3d4..."`), stocke les données dans un dict mémoire, TTL 15 minutes. Retourne le token.

- `lire_token(token) -> dict | None`
  Si le token existe et n'est pas expiré → retourne `{distance_km, waypoints, voiture_id, expire_at}`. Sinon `None`.

Structure du cache :
```python
_cache_tokens: dict[str, dict] = {}
# "a1b2c3d4..." → {"distance_km": 127.3, "waypoints": [...],
#                  "voiture_id": 5, "expire_at": 1712345678.0}
```

Purge automatique des tokens expirés à chaque nouvelle émission (`_purger_tokens_expires`).

**Pourquoi un dict Python et pas Redis ?** Zéro dépendance à installer, marche immédiatement. Limitation acceptée : si tu redémarres FastAPI, tous les tokens en cours sont perdus (le client doit recalculer). Pour un MVP c'est OK. Redis viendra en production quand tu auras plusieurs workers.

### Points importants

- **Format des waypoints** : le service attend `[(lat, lon), (lat, lon), ...]` — ordre humain naturel.
  BRouter et OSRM utilisent `lon,lat` (inverse) → la conversion se fait dans les fonctions internes.
- **Aucune exception réseau ne remonte** : si BRouter plante, on retourne `None` et on passe au suivant. Seul `_valider_waypoints` lève `RoutingError`.
- **Constantes en haut du fichier** : `MADAGASCAR_LAT`, `MADAGASCAR_LON`, `MAX_WAYPOINTS`, `TOKEN_TTL_SECONDS`, `HTTP_TIMEOUT`. Faciles à ajuster sans lire tout le code.

### Test rapide (Python REPL)

```python
import asyncio
from app.services.routing_service import calculer_itineraire, emettre_token, lire_token

# Antananarivo → Antsirabe
wp = [(-18.8792, 47.5079), (-19.8659, 47.0393)]
res = asyncio.run(calculer_itineraire(wp))
print(res["distance_km"], res["source"])

tok = emettre_token(res["distance_km"], wp, voiture_id=1)
print(lire_token(tok))
```

---

## ÉTAPES SUIVANTES (résumé rapide)

### Étape 2 — Endpoint API

Créer `app/routers/itineraire_api.py` avec :
```
POST /api/voitures/{voiture_id}/itineraire/calculer
Body: {"waypoints": [[lat, lon], ...]}
Réponse: {"distance_km": ..., "polyline": {...}, "token": "..."}
```

Réutiliser la logique de quota déjà présente dans `web.py:64-77` (7 calculs/jour pour anonyme).

### Étape 3 — Adapter le JS

Dans `static/js/itineraire/routing.js` (lignes 39-51), remplacer le `fetch("https://brouter.de/...")` par `fetch("/api/voitures/{id}/itineraire/calculer", {method: "POST", ...})`.

Stocker le token retourné dans `state.js`.

### Étape 4 — Formulaire de réservation

Dans `app/templates/voiture_detail.html:112`, ajouter :
```html
<input type="hidden" name="itinerary_token" id="itinerary-token" value="">
```

Le JS remplira cette valeur après un calcul réussi.

### Étape 5 — Vérification du token dans `/reserver`

Dans `app/routers/web.py:80-141`, après avoir lu le formulaire :
```python
token = form_data.get("itinerary_token")
if token:
    data = routing_service.lire_token(token)
    if data:
        form.itinerary_distance_km = data["distance_km"]
```

**Point clé** : on **ignore** toute valeur `itinerary_distance_km` envoyée par le client. Seul le token compte.

### Étape 6 — Vérification finale

- Ouvrir `/voitures/{id}/itineraire`, tracer un trajet, cliquer "Calculer"
- Onglet Réseau : la requête doit aller vers `/api/...`, plus vers `brouter.de`
- Réserver la voiture
- Vérifier en BD :
  ```sql
  SELECT id, itineraire_distance_km FROM locations ORDER BY id DESC LIMIT 1;
  ```
  La distance doit être non-NULL.
- Test d'attaque : modifier `itinerary_token` via F12 → la distance stockée doit rester NULL (token invalide ignoré).

---

## Fichiers touchés récapitulatif

**Créés :**
- ✅ `app/services/routing_service.py`
- ⏳ `app/routers/itineraire_api.py`

**Modifiés :**
- ⏳ `static/js/itineraire/routing.js`
- ⏳ `app/templates/voiture_detail.html`
- ⏳ `app/routers/web.py`
- ⏳ `app/main.py` (pour inclure le nouveau router)

**Intacts :**
- `app/models/models.py` — les colonnes `itineraire_*` existent déjà
- `app/schemas.py` — `LocationForm` a déjà `itinerary_distance_km`
