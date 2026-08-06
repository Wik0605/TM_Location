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

## À venir

Voir `securite.md` §5 — plan de correction priorisé. Prochain fix prévu :
- 🔴 Rate limit sur `/admin/login` via `slowapi`
