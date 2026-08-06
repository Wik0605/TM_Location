# Journal des actions de sécurité — TM_Location

Historique des fixes appliqués sur les vulnérabilités identifiées dans `securite.md`.

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

## À venir

Voir `securite.md` §5 — plan de correction priorisé. Prochains fixes :
- 🔴 Changer `ADMIN_PASSWORD` dans `.env` (à faire par l'utilisateur)
- 🔴 Crasher si secrets == valeurs par défaut en prod (`config.py`)
- 🟡 Rotation session au login (`session.clear()`)
- 🟡 `max_age` SessionMiddleware en dev
- 🟡 Vérif historique Git pour `.env`
