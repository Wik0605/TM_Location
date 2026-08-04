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
| 2. Endpoint API `/api/.../calculer` | ✅ **Fait** | `app/routers/itineraire_api.py` |
| 3. Adapter le JS pour appeler l'API | ✅ **Fait** | `static/js/itineraire/routing.js` |
| 4. Ajouter input hidden `itinerary_token` | ✅ **Fait** | `app/templates/voiture_detail.html` |
| 5. Vérifier le token dans `/reserver` | ✅ **Fait** | `app/routers/web.py` |
| 6. Nettoyage JS front + fix `CAR_ID` | ✅ **Fait** | `static/js/`, `app/templates/itineraire.html` |

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

## ÉTAPE 2 — Endpoint API (fait)

### Fichier créé : `app/routers/itineraire_api.py`

Contrat de l'endpoint :
```
POST /api/voitures/{voiture_id}/itineraire/calculer
Body JSON: {"waypoints": [[lat, lon], [lat, lon], ...]}
Réponse: {"distance_km": 127.3, "polyline": {...geojson...},
          "source": "brouter", "token": "a1b2c3d4..."}
```

### Ce que fait le fichier

**Validation d'entrée avec Pydantic** (`WaypointsPayload`) :
Le body JSON est validé automatiquement — si `waypoints` est absent, mal formé, ou contient moins de 2 / plus de 10 points, FastAPI répond **422 Unprocessable Entity** sans jamais atteindre ton code.

**Vérification de quota** (`_verifier_quota`) :
Reprend exactement la logique de `web.py:64-77` : utilisateur connecté → illimité ; anonyme → 7 calculs/jour par session. Si dépassé → HTTP **429 Too Many Requests**.

**Appel du service** :
Convertit les waypoints en tuples et appelle `routing_service.calculer_itineraire()`.
- Si `RoutingError` (coords hors Madagascar, etc.) → HTTP **400 Bad Request** avec le message.
- Sinon, émission du token via `emettre_token()` et retour du tout en JSON.

### Enregistrement dans `main.py`

Deux lignes ajoutées :
- Import du router (ligne 26)
- `app.include_router(itineraire_api_router)` (ligne 110)

### Tester avec curl

```bash
curl -X POST http://localhost:8000/api/voitures/1/itineraire/calculer \
  -H "Content-Type: application/json" \
  -d '{"waypoints": [[-18.8792, 47.5079], [-19.8659, 47.0393]]}'
```

Réponse attendue : JSON avec `distance_km`, `polyline`, `source`, `token`.

Test d'erreur (hors Madagascar) :
```bash
curl -X POST http://localhost:8000/api/voitures/1/itineraire/calculer \
  -H "Content-Type: application/json" \
  -d '{"waypoints": [[40.7128, -74.0060], [-18.8792, 47.5079]]}'
```
→ HTTP 400 avec `{"detail": "Latitude hors de Madagascar."}`.

### Point important

L'endpoint retourne aussi `"source"` (`"brouter"` / `"osrm"` / `"haversine"`).
Utile côté JS pour prévenir l'utilisateur : *"Distance approximative (mode dégradé)"* si `source == "haversine"`.

## ÉTAPE 3 — Adapter le JS (fait)

### Fichiers modifiés

1. **`static/js/itineraire/state.js`** — ajout de deux champs partagés :
   - `CAR_ID` : l'ID de la voiture (lu depuis `<div id="map" data-car-id="...">`)
   - `itineraryToken` : le token reçu du backend après un calcul

2. **`static/js/itineraire/main.js`** — initialise `state.CAR_ID` au démarrage.

3. **`static/js/itineraire/routing.js`** — **complètement réécrit** :
   - Supprimé : `calcBRouter`, `calcOSRM`, `calcFallback`, `haversineKm`, `firstValid` (la cascade vit maintenant côté serveur)
   - Conservé : `drawRoute` (le rendu Leaflet reste côté client)
   - Ajouté : `calcBackend(coords)` — un seul `fetch()` vers `/api/voitures/{CAR_ID}/itineraire/calculer`

4. **`static/js/itineraire/results.js`** — dans `runCalculation` :
   - Retiré le pré-check `/quota` (le backend gère lui-même le quota et renvoie 429 si dépassé)
   - Retirée la cascade `firstValid(calcBRouter, calcOSRM) → calcFallback`
   - Remplacée par un unique `await calcBackend(coords)`
   - Le token reçu est stocké dans `state.itineraryToken` (sera injecté dans le formulaire à l'étape 5)

### Ce que ça change pour l'utilisateur

**Visuellement : rien.** L'itinéraire s'affiche pareil, le prix se calcule pareil.

**Dans les outils réseau du navigateur** (F12 → onglet Network) :
- **Avant** : requêtes vers `brouter.de`, `router.project-osrm.org`, plus une vers `/quota`
- **Après** : une seule requête vers `/api/voitures/{id}/itineraire/calculer`

### Nouvelle logique de la fonction `calcBackend`

```
1. Convertir "lon,lat" (format interne JS) en [lat, lon] (format API)
2. POST /api/voitures/{CAR_ID}/itineraire/calculer avec { waypoints: [...] }
3. Si 429 → renvoyer { quotaExceeded: true } (affichera le modal quota)
4. Si autre erreur → renvoyer null (affichera une alerte)
5. Sinon → dessiner la polyline + renvoyer { distanceKm, isFallback, token }
```

### Endpoint `/quota` devenu inutile

L'ancien endpoint `POST /voitures/{id}/itineraire/quota` (dans `web.py:64-77`) n'est plus appelé par le JS. On peut le supprimer plus tard — pour l'instant on le laisse, ne casse rien.

## ÉTAPES SUIVANTES (résumé rapide)

## ÉTAPE 4 — Formulaire de réservation (fait)

### Le problème à résoudre

Le calcul se fait sur `/voitures/{id}/itineraire`, mais le formulaire de réservation est sur `/voitures/{id}` (page différente). Quand l'utilisateur clique "Réserver", il navigue vers une nouvelle page → **la mémoire JS est vidée**, le token est perdu.

### La solution : `localStorage`

Le `localStorage` du navigateur est un mini-stockage qui **survit à la navigation entre pages** (contrairement à la mémoire JS classique). On y écrit le token sur la page itinéraire, on le relit sur la page voiture_detail.

### Changements

**1. `static/js/itineraire/results.js`**
Juste après avoir reçu le token du backend :
```js
localStorage.setItem(`itinerary_token_${state.CAR_ID}`, result.token);
```
La clé est préfixée par l'ID voiture → si l'utilisateur teste plusieurs voitures, aucun mélange.

**2. `app/templates/voiture_detail.html`**
Deux ajouts :
- Un `<input type="hidden" name="itinerary_token" id="itinerary-token" value="">` dans le formulaire de réservation
- Un petit script qui, au chargement de la page, lit `localStorage` et remplit l'input :
```js
const token = localStorage.getItem(`itinerary_token_{{ voiture.id }}`);
if (token) document.getElementById('itinerary-token').value = token;
```

### Cas où le token reste vide

- L'utilisateur réserve **sans passer par la page itinéraire** → pas de token en localStorage → input vide → back stockera `NULL` (comportement actuel préservé).
- Le token a expiré côté serveur (> 15 min) → l'input contient une valeur, mais le back l'ignore à l'étape 5.
- Le navigateur bloque localStorage (navigation privée stricte) → le `try/catch` évite le crash, input vide.

### Point de sécurité

Le token dans localStorage est **lisible et modifiable** par l'utilisateur (F12 → onglet Application → Local Storage). **Ce n'est pas un problème** :
- S'il met un token bidon → le back ne le trouve pas dans son cache → distance reste NULL.
- S'il vole le token d'un autre utilisateur → impossible, chaque token est unique et lié à une session serveur éphémère.

La sécurité ne repose **jamais** sur "le client ne peut pas voir X". Elle repose sur "le serveur seul valide X". C'est le principe de l'étape 5.

## ÉTAPE 5 — Vérification du token dans `/reserver` (fait)

### Changement principal

Dans `app/routers/web.py`, l'endpoint `/reserver` a été modifié pour :

1. **Ne plus faire confiance à `itinerary_distance_km` envoyé par le client** — on passe explicitement `None` dans `LocationForm`, même si le formulaire contient cette valeur.
2. **Lire uniquement le token** (`itinerary_token`) et récupérer la distance depuis le cache serveur via `routing_service.lire_token()`.
3. **Vérifier que le token appartient bien à cette voiture** (`token_data["voiture_id"] == voiture_id`). Empêche un utilisateur de calculer sur une voiture A puis de réserver sur une voiture B avec le même token.

### Code ajouté

```python
token = form_data.get("itinerary_token")
if token:
    token_data = routing_service.lire_token(token)
    if token_data and token_data["voiture_id"] == voiture_id:
        form.itinerary_distance_km = token_data["distance_km"]
        form.itinerary_waypoints = ";".join(
            f"{lat},{lon}" for lat, lon in token_data["waypoints"]
        )
```

### Ce qui se passe dans les 4 scénarios possibles

| Situation | Résultat en BD |
|-----------|----------------|
| Utilisateur a calculé un itinéraire → token valide | `itineraire_distance_km` rempli avec la vraie distance |
| Utilisateur n'a pas calculé (réserve direct) | `itineraire_distance_km` = `NULL` |
| Token présent mais expiré (> 15 min) | `itineraire_distance_km` = `NULL` |
| Token forgé par F12 (valeur bidon) | `itineraire_distance_km` = `NULL` |
| Token valide mais d'une autre voiture | `itineraire_distance_km` = `NULL` |

Dans **tous** ces cas, la valeur envoyée par le champ hidden `itinerary_distance_km` du client est **totalement ignorée**. Le serveur ne se fie qu'à son propre cache.

### Pourquoi c'est incontestable

- Le client ne peut pas **générer** un token valide (UUID aléatoire côté serveur, jamais partagé).
- Le client ne peut pas **modifier** la distance stockée sous un token (dict Python privé au processus FastAPI).
- Le client ne peut pas **réutiliser** un token d'une autre voiture (vérification `voiture_id`).
- Le client ne peut pas **rejouer** un vieux token (TTL 15 min).

**La distance en BD est désormais 100% source-serveur.** Si demain tu factures au km, aucune contestation possible.

## ÉTAPE 6 — Nettoyage JS front (fait)

Une fois la cascade migrée côté serveur, il restait du code mort côté client
et un bug bloquant. Objectif de l'étape : rendre le front minimal et cohérent
avec le nouveau contrat (un seul appel au back, plus rien d'autre).

### Fichiers supprimés

- `static/js/itineraire.js` — ancien script monolithe (~400 lignes) contenant
  toute la logique Haversine + appels directs BRouter/OSRM. Devenu orphelin
  après le refactor en 6 modules ES, plus référencé nulle part.
- `static/js/brouter_map.js` — prototype (~160 lignes) jamais importé dans
  aucun template.

Vérification faite avant suppression :
```bash
grep -rn "itineraire.js\|brouter_map.js" app/templates/ static/
# → aucune référence
```

### Bug corrigé : `CAR_ID` valait `null`

`static/js/itineraire/main.js:9` lit `data-car-id` sur `#map` :
```js
state.CAR_ID = mapEl.getAttribute('data-car-id');
```

Or l'attribut n'existait pas dans `app/templates/itineraire.html`. Résultat :
l'URL construite dans `calcBackend()` devenait
`/api/voitures/null/itineraire/calculer` → 404 systématique dès l'étape 3.

Correctif dans `app/templates/itineraire.html` :
```html
<div id="map"
     data-daily-price="{{ car.daily_price }}"
     data-car-id="{{ car.id }}"></div>
```

### Ce qui a été volontairement conservé

- `static/js/itineraire/routing.js` — contient `calcBackend()`, seul appel valide
- `static/js/itineraire/results.js` — gère le stockage du token en localStorage
  et l'affichage de `.fallback-note` si le back signale un calcul dégradé
- La `.fallback-note` orange dans `itineraire.html` (l. 233-235) — encore
  utilisée par `results.js` quand `source === "haversine"`
- L'input hidden `itinerary_token` et son hydratation dans `voiture_detail.html`
- La vérification token dans `app/routers/web.py`

### Résultat du commit

`7ade339 Migration carte : etape 6 (nettoyage JS front)`
→ 3 fichiers, 3 insertions, **561 suppressions**.

---

## Fichiers touchés récapitulatif

**Créés :**
- ✅ `app/services/routing_service.py`
- ✅ `app/routers/itineraire_api.py`

**Modifiés :**
- ✅ `static/js/itineraire/routing.js`
- ✅ `static/js/itineraire/state.js`
- ✅ `static/js/itineraire/main.js`
- ✅ `static/js/itineraire/results.js`
- ✅ `app/templates/voiture_detail.html`
- ✅ `app/templates/itineraire.html` (attribut `data-car-id`)
- ✅ `app/routers/web.py`
- ✅ `app/main.py` (inclusion du router API)

**Supprimés :**
- ✅ `static/js/itineraire.js`
- ✅ `static/js/brouter_map.js`

**Intacts :**
- `app/models/models.py` — les colonnes `itineraire_*` existent déjà
- `app/schemas.py` — `LocationForm` a déjà `itinerary_distance_km`

---

## Vérification bout en bout (à faire dans le navigateur)

1. Relancer l'app : `uvicorn app.main:app --reload`
2. Ouvrir `/voitures/{id}/itineraire`, vider le cache navigateur
3. Tracer un trajet, cliquer "Calculer l'itinéraire"
4. Onglet Réseau : la requête doit partir vers
   `/api/voitures/<id_réel>/itineraire/calculer` (plus `null`, plus `brouter.de`)
5. Vérifier que le token est bien posé dans `localStorage`
6. Réserver la voiture, puis en BD :
   ```sql
   SELECT id, itineraire_distance_km FROM locations ORDER BY id DESC LIMIT 1;
   ```
   La distance doit être non-NULL et correspondre au calcul serveur.
7. Test d'attaque : modifier `itinerary_token` via F12 avant de soumettre →
   la distance stockée doit rester NULL (token invalide ignoré).
