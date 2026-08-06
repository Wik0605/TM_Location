# Journal des actions de sécurité — TM_Location

Historique des fixes appliqués sur les vulnérabilités identifiées dans `securite.md`.

## Récapitulatif

| # | Fix | Commit | Vuln (`securite.md`) | Statut |
|---|---|---|---|---|
| 1 | Centralisation `require_admin` | `4781fa6` | §3.3 | ✅ |
| 2 | Rate limit `/admin/login` (5/15min) | `29d2690` | §3.1 | ✅ |
| 3 | Changer `ADMIN_PASSWORD` dans `.env` | — | §3.2 | ⏳ à faire par l'utilisateur |
| 4 | Crash en prod si secrets par défaut | `f77a24d` | §3.2 | ✅ |
| 5 | Rotation session au login | `95fc972` | §3.4 | ✅ |
| 6 | SessionMiddleware dev durci | `56d24e7` | §3.5 | ✅ |
| 7 | Vérif historique `.env` (rien commité) | — | §3.6 | ✅ |
| 8 | Durcissement OAuth Google (state, email_verified, erreurs) | `0c0e62a` | §6 | ✅ |
| 9 | Middleware security headers (X-Frame, nosniff, HSTS, ...) | `b998cf7` | hors `securite.md` | ✅ |
| 10 | Rate limit sur `/reserver` (10/h) et `/auth/google` (20/h) | `4bb4061` | hors `securite.md` | ✅ |
| 11 | Validation waypoints (bounding box, max 10, timeout) | déjà fait | `CARTE.md §3.2` | ✅ |
| 12 | Limite de taille upload image (8 MB, 40 Mpixels) | `d9e2539` | hors `securite.md` | ✅ |
| 13 | Logs des évènements sensibles (login, rate limit, OAuth) | `4a8751d` | hors `securite.md` | ✅ |
| 14 | Protection CSRF sur les routes POST | `9fa38c0` | hors `securite.md` | ✅ |

**13/14 fixes techniques appliqués.** Reste 1 action manuelle : changer `ADMIN_PASSWORD` dans `.env` (voir "Statut final" en bas).

---

## 2026-08-06

### Fix #1 — Centralisation de `require_admin` (commit `4781fa6`)

**Vuln traitée** : `securite.md` §3.3 — check admin dupliqué 14 fois dans `admin_cars.py` et `admin_rentals.py`.

**Changements** :
- `app/routers/admin_auth.py` : `require_admin` lève désormais `HTTPException(status_code=302, headers={"Location": "/admin/login"})` au lieu de retourner un `RedirectResponse`. Supprime aussi le retour `None` inutile.
- `app/routers/admin_cars.py` : ajout de `dependencies=[Depends(require_admin)]` sur le `APIRouter`. Suppression des 11 blocs :
  ```python
  redirect = require_admin(request)
  if redirect:
      return redirect
  ```
- `app/routers/admin_rentals.py` : même chose pour les 3 routes du router.

**Résultat** :
- 14 blocs dupliqués (3 lignes chacun) supprimés.
- Impossible d'oublier le check sur une future route admin : la protection est portée par le router lui-même.
- Vérifié via `TestClient` : `GET /admin`, `/admin/voitures`, `/admin/reservations` renvoient tous `302 → /admin/login` sans session.

**Diff net** : 3 fichiers, +13 / −39 lignes.

---

### Fix #2 — Rate limit sur `/admin/login` (commit `29d2690`)

**Vuln traitée** : `securite.md` §3.1 — aucune limite au login admin, brute force possible.

**Changements** :
- `requirements.txt` : ajout `slowapi>=0.1.10`.
- `app/limiter.py` (nouveau) : instance `Limiter` partagée, clé = IP client (`get_remote_address`).
- `app/main.py` : enregistrement du limiter (`app.state.limiter`) et du handler `RateLimitExceeded`.
- `app/routers/admin_auth.py` :
  - `@limiter.limit("5/15minutes")` sur `POST /admin/login`.
  - Handler `login_rate_limit_handler` qui renvoie la page de login avec message "Trop de tentatives, réessayez dans quelques minutes" et status `429`.

**Résultat** :
- 5 tentatives max par IP toutes les 15 min sur le login admin.
- Vérifié via `TestClient` : les 5 premières tentatives renvoient `200`, la 6ᵉ et suivantes `429`.

**Diff net** : 4 fichiers, +29 / −2 lignes.

---

### Fix #4 — Refus de démarrer en prod avec secrets par défaut (commit `f77a24d`)

**Vuln traitée** : `securite.md` §3.2 — si `.env` disparaît ou n'est pas chargé en prod, l'app démarrait avec `secret_key="changeme"` et `admin/admin`.

**Changements** :
- `app/config.py` :
  - Constante `INSECURE_DEFAULTS = {"changeme", "admin", ""}`.
  - Méthode `Settings.assert_production_ready()` : en prod uniquement, vérifie que `secret_key` ≥ 32 chars et hors défauts, `admin_password` ≥ 12 chars et hors défauts, `admin_username` ≠ "admin".
  - Appel de `assert_production_ready()` au chargement du module → l'import échoue si config invalide en prod.
- En dev : aucun check (démarrage local rapide conservé).

**Résultat** (testé avec 3 scénarios) :
- Dev avec défauts : passe ✅
- Prod avec défauts : `RuntimeError` avec liste des problèmes ✅
- Prod avec valeurs correctes : passe ✅

**Diff net** : 1 fichier, +19 lignes.

---

### Fix #5 — Rotation de session au login (commit `95fc972`)

**Vuln traitée** : `securite.md` §3.4 — pas de rotation de session au login, risque de session fixation.

**Changements** :
- `app/routers/admin_auth.py` : `request.session.clear()` avant de poser `admin_logged_in = True`.

**Diff net** : 1 fichier, +1 ligne.

---

### Fix #6 — SessionMiddleware dev durci (commit `56d24e7`)

**Vuln traitée** : `securite.md` §3.5 — en dev, ni `same_site` ni `max_age` sur le middleware de session.

**Changements** :
- `app/main.py` : ajout de `same_site="lax"` et `max_age=3600` dans la branche `else` (dev). Aligne le comportement dev sur prod (sauf `https_only`).

**Diff net** : 1 fichier, +6 / −1 lignes.

---

### Fix #7 — Vérification historique Git pour `.env`

**Vuln traitée** : `securite.md` §3.6 — vérifier si `.env` a jamais été commité.

**Commande exécutée** :
```
git log --all --full-history --oneline -- .env
```

**Résultat** : sortie vide → `.env` **n'a jamais été commité**. Aucune action nécessaire, pas de secrets à régénérer, pas de réécriture d'historique.

**Diff net** : aucun (vérification seule).

---

### Fix #8 — Durcissement du flow OAuth Google (commit `0c0e62a`)

**Vuln traitée** : `securite.md` §6 "à prévoir pour OAuth" — le flow Google existait mais sans les protections critiques.

**Changements** (`app/routers/auth.py`) :
- **CSRF `state`** : `secrets.token_urlsafe(32)` généré et stocké en session à `/auth/google`, vérifié avec `compare_digest` au callback. Rejette avec `400` si absent ou différent.
- **`email_verified` obligatoire** : la réponse Google doit contenir `email_verified: true`, sinon `403`. Bouche le piège classique où un provider mal configuré permettrait de s'inscrire avec l'email d'un tiers.
- **Gestion d'erreurs** : timeout 10s, `raise_for_status()`, `try/except httpx.HTTPError` → `502`. Réponses vides ou profil incomplet → `502`.
- **Config absente** : si `GOOGLE_CLIENT_ID` ou `GOOGLE_CLIENT_SECRET` sont vides, `/auth/google` renvoie `503` au lieu de rediriger vers une URL cassée.
- **URL propre** : `urlencode()` au lieu d'une f-string.

**Résultat** (testé via `TestClient`) :
- Sans `client_id` → `503` ✅
- Callback sans `state` → `400` ✅
- Callback avec `state` pourri → `400` ✅

**Diff net** : 1 fichier, +60 / −25 lignes.

---

### Fix #9 — Middleware security headers (commit `b998cf7`)

**Contexte** : ces headers ne figuraient pas dans `securite.md` mais sont des protections défensives standards (OWASP Secure Headers).

**Changements** (`app/main.py`) :
- Nouveau `SecurityHeadersMiddleware` (`BaseHTTPMiddleware`) qui pose sur chaque réponse :
  - `X-Content-Type-Options: nosniff` — bloque MIME sniffing
  - `X-Frame-Options: DENY` — bloque clickjacking (iframe)
  - `Referrer-Policy: strict-origin-when-cross-origin` — fuite d'URL limitée
  - `Permissions-Policy: geolocation=(self), microphone=(), camera=()` — désactive APIs sensibles sauf géoloc (utilisée par la carte)
- En prod uniquement : `Strict-Transport-Security: max-age=31536000; includeSubDomains` (1 an).

**Note** : CSP volontairement omise. Les templates (`voiture_detail.html`, `admin/voitures.html`) contiennent des `onclick=""` inline qu'il faudrait migrer vers des event listeners externes avant d'activer une CSP stricte. À prévoir si on veut boucher les XSS.

**Résultat** (testé via `TestClient` en dev) :
- Les 4 headers de base sont présents sur `GET /` ✅
- HSTS bien absent en dev ✅

**Diff net** : 1 fichier, +23 lignes.

---

### Fix #10 — Rate limit `/reserver` et `/auth/google` (commit `4bb4061`)

**Contexte** : hors `securite.md`, extension du rate limit `slowapi` déjà en place.

**Changements** :
- `app/routers/web.py` : `@limiter.limit("10/hour")` sur `POST /voitures/{id}/reserver` (protège contre le spam de réservations depuis une même IP).
- `app/routers/auth.py` : `@limiter.limit("20/hour")` sur `GET /auth/google` (protège contre le flood du flow OAuth).
- `app/routers/admin_auth.py` : le handler `login_rate_limit_handler` devient contextuel — page HTML de login pour `/admin/login`, réponse texte `429` générique pour les autres endpoints.

**Résultat** (testé via `TestClient`) :
- `/auth/google` : 20 tentatives → `307`, la 21ᵉ → `429` avec body "Trop de requêtes..." ✅

**Diff net** : 3 fichiers, +16 / −6 lignes.

---

### Fix #11 — Validation waypoints (déjà couvert)

**Vuln** : `CARTE.md §3.2` — protéger `/api/voitures/{id}/itineraire/calculer` contre les waypoints malicieux (DoS via 500 points, coordonnées hors Madagascar, timeout serveur).

**État** : **déjà en place** dans le code après la migration carte du 4 août 2026.

Preuves :
- `app/services/routing_service.py:9-13` : constantes `MADAGASCAR_LAT`, `MADAGASCAR_LON`, `MAX_WAYPOINTS = 10`, `HTTP_TIMEOUT = 5.0`.
- `app/services/routing_service.py:22-31` : `_valider_waypoints()` vérifie min 2, max 10, chaque point dans la bounding box.
- `app/routers/itineraire_api.py:14-19` : validation Pydantic `conlist` en amont (structure + longueur).

**Diff net** : aucun (rien à ajouter).

---

### Fix #12 — Limite de taille sur les uploads d'images (commit `d9e2539`)

**Contexte** : hors `securite.md`. Auparavant, `await file.read()` chargeait le fichier entier en RAM sans limite. Un fichier de 2 GB → app OOM. Un PNG "bomb" (petit fichier qui décompresse en plusieurs GB) → même problème via Pillow.

**Changements** (`app/routers/admin_cars.py`) :
- Constantes : `IMAGE_MAX_BYTES = 8 * 1024 * 1024` (8 MB) et `IMAGE_MAX_PIXELS = 40_000_000`.
- `Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS` — configure Pillow pour bloquer les decompression bombs.
- Nouvelle helper `_lire_upload_limite(file)` : lit `IMAGE_MAX_BYTES + 1` octets, renvoie `None` si dépassé (jamais plus de 8 MB en RAM).
- `add_voiture_images` : passe par le lecteur borné, skip silencieux si trop gros (comme pour les non-images).

**Diff net** : 1 fichier, +15 / −1 lignes.

---

### Fix #13 — Logs des évènements sensibles (commit `4a8751d`)

**Contexte** : hors `securite.md`. Sans logs, impossible de détecter une attaque en cours ni d'auditer après coup qui s'est connecté.

**Changements** :
- `app/main.py` : `logging.basicConfig(level=INFO, format=...)` — aucun handler n'était configuré avant, les warnings partaient nulle part.
- `app/routers/admin_auth.py` :
  - Logger `security` créé.
  - Helper `_client_ip(request)` qui gère `X-Forwarded-For` (pour le futur proxy en prod).
  - Log `admin_login_success` (INFO) et `admin_login_failure` (WARNING) avec `user=` et `ip=`.
  - Log `rate_limit_exceeded` (WARNING) avec `path=` et `ip=` dans le handler d'erreur.
- `app/routers/auth.py` :
  - Log `oauth_state_mismatch` (WARNING) → détecte les tentatives CSRF sur le callback Google.
  - Log `oauth_email_not_verified` (WARNING) → détecte les tentatives d'inscription avec email non vérifié.

**Résultat** (testé via `TestClient`) :
```
WARNING security admin_login_failure user=attacker ip=testclient
WARNING security admin_login_failure user=tafita ip=testclient
WARNING security oauth_state_mismatch ip=testclient
```

**Diff net** : 3 fichiers, +30 lignes.

---

### Fix #14 — Protection CSRF sur les routes POST (commit `9fa38c0`)

**Contexte** : hors `securite.md`. Sans CSRF, un site tiers pouvait forcer le navigateur d'un admin connecté à envoyer une requête POST vers `/admin/*` avec ses cookies de session, causant des actions non voulues (suppression de voiture, changement de statut...).

**Approche** : implémentation maison, pas de dépendance externe (~40 lignes).

**Nouveaux fichiers** :
- `app/csrf.py` :
  - `get_or_create_csrf_token(request)` : génère un token `secrets.token_urlsafe(32)` en session s'il n'existe pas.
  - `csrf_input(request)` : helper Jinja qui produit `<input type="hidden" name="csrf_token" value="...">`.
  - `require_csrf(request)` : dependency FastAPI qui skip les méthodes safe (GET/HEAD/OPTIONS), puis vérifie le champ `csrf_token` du form OU l'en-tête `X-CSRF-Token` (HTMX). `compare_digest` pour éviter timing attack.
- `app/templating.py` : `Jinja2Templates` centralisé avec les globals `csrf_input` et `csrf_token` enregistrés une seule fois (évite la duplication dans les 4 routers).

**Application** :
- `POST /admin/login` : dependency `require_csrf` + `{{ csrf_input(request) }}` dans `login.html`.
- `POST /voitures/{id}/reserver` : dependency + input dans `voiture_detail.html`.
- Tous les `POST /admin/*` (cars, rentals) : dependency posée sur le router. Pour HTMX, `hx-headers='{"X-CSRF-Token": "{{ csrf_token(request) }}"}'` sur `<body>` de `base_admin.html` → toutes les requêtes HTMX admin l'héritent automatiquement, sans toucher chaque `hx-post` individuel.

**Résultat** (testé via `TestClient`, 5 scénarios) :
- POST /admin/login sans token → `403` ✅
- POST /admin/login avec token valide → `200` ✅
- POST /admin/login avec token pourri → `403` ✅
- POST /voitures/1/reserver sans token → `403` ✅
- GET /admin/login pose bien un token en session ✅

**Diff net** : 9 fichiers, +66 / −11 lignes.

---

## Statut final

Tous les fixes techniques identifiés dans `securite.md` sont appliqués + 7 durcissements complémentaires (OAuth, headers, rate limits, uploads, logs, CSRF).

### Ce que l'app gagne

- Auth admin centralisée (impossible d'oublier le check `require_admin`)
- Rate limit sur `/admin/login` (5/15min), `/reserver` (10/h), `/auth/google` (20/h)
- Refus de démarrer en prod avec `SECRET_KEY`/`ADMIN_PASSWORD` par défaut
- Rotation session au login admin
- OAuth Google durci : CSRF `state`, `email_verified` obligatoire, gestion d'erreurs, config manquante détectée
- Security headers globaux : `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `HSTS` (prod)
- Uploads bornés à 8 MB + protection Pillow contre decompression bombs (40 Mpixels max)
- Logger `security` qui trace login (success/failure), rate limit exceeded, OAuth state mismatch, OAuth email non vérifié — avec IP
- Protection CSRF sur tous les POST (form classique via `csrf_input`, HTMX via `X-CSRF-Token` posé sur `<body>` du template admin)

### Reste à faire

- 🔴 **Changer `ADMIN_PASSWORD` dans `.env`** pour une chaîne longue et aléatoire (ex. `openssl rand -base64 24`). Le fix #4 imposera de le faire au plus tard au passage en production.
- 🟡 **CSP stricte** : impossible tant que les templates contiennent des `onclick=""` inline (`voiture_detail.html`, `admin/voitures.html`). À prévoir dans un chantier séparé — migration vers event listeners externes.

### Tests navigateur nécessaires

Tous les fixes ont été validés via `TestClient`. Une session dans le vrai navigateur reste indispensable pour confirmer qu'aucun workflow n'est cassé, notamment par la CSRF. Lancer :

```
uvicorn app.main:app --reload
```

Puis vérifier :

- [ ] Login admin (`/admin/login`) → redirection dashboard OK
- [ ] Login admin avec mauvais mdp × 5 → 6ᵉ tentative bloquée (429)
- [ ] Création d'une voiture (form admin)
- [ ] Upload d'images de voiture (< 8 MB → OK, > 8 MB → ignoré)
- [ ] Édition d'une voiture (HTMX PUT)
- [ ] Suppression d'un type de location (HTMX POST)
- [ ] Changement de statut d'une réservation (HTMX POST)
- [ ] Réservation côté client (form public `/voitures/{id}/reserver`)
- [ ] OAuth Google `/auth/google` (nécessite les vraies clés dans `.env`)
- [ ] Tests d'attaque de la migration carte (voir mémoire projet — pas encore fait)
