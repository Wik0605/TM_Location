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

**9/10 fixes techniques appliqués.** Reste 1 action manuelle : changer `ADMIN_PASSWORD` dans `.env` (voir "Statut final" en bas).

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

## Statut final

Tous les fixes techniques identifiés dans `securite.md` sont appliqués + OAuth Google durci. Reste **1 action manuelle** côté utilisateur :

- 🔴 **Changer `ADMIN_PASSWORD` dans `.env`** pour une chaîne longue et aléatoire (ex. `openssl rand -base64 24`). Le fix #4 imposera de le faire au plus tard au passage en production.
