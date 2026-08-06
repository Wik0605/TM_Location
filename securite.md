# Sécurité — TM_Location

**Dernière mise à jour** : 2026-08-06
**Statut global** : 🟠 Correct pour du dev, à durcir avant prod (2 points urgents)

Ce document fusionne l'ancien audit large (28 juillet 2026) et l'audit ciblé du 6 août 2026, croisés avec l'état actuel du code.

---

## 1. Résumé

L'application a été durcie sur plusieurs points depuis fin juillet (CORS, sessions, validation Pydantic). Il reste **2 points urgents** avant toute mise en production :

- 🔴 Pas de rate limit sur le login admin → brute force possible
- 🔴 Mot de passe admin faible (`tafita2000`) et secrets par défaut faibles dans `config.py`

Plus **1 refactor important** pour éviter les futurs oublis de check admin.

---

## 2. Principes de référence

Les 5 règles de sécurité qui pilotent cet audit :

1. **Jeton de connexion** — signé, `HttpOnly + Secure + SameSite`, expiration, rotation au login.
2. **Vérification d'admin** — dépendance centralisée, jamais copiée par route.
3. **Zéro limite au login** — rate limit obligatoire par IP + username.
4. **Compte sans mail vérifié** — double opt-in ou OAuth qui garantit la vérif.
5. **Mot de passe fuité** — bcrypt/argon2 uniquement, jamais en clair, check HaveIBeenPwned.

---

## 3. Vulnérabilités actives

### 🔴 3.1 Aucun rate limit sur `/admin/login`

- **Fichier** : `app/routers/admin_auth.py:27-40`
- **Impact** : brute force possible ; combiné à `tafita2000` (8 caractères, nom + année), cassable en minutes avec `hydra`.
- **Bon point existant** : `secrets.compare_digest` bien utilisé (protection timing attack).
- **Fix** : ajouter `slowapi` — 5 tentatives / 15 min par IP, verrouillage progressif.

### 🔴 3.2 Secrets par défaut faibles

- **Fichier** : `app/config.py:5-11`
  ```python
  secret_key: str = "changeme"
  admin_username: str = "admin"
  admin_password: str = "admin"
  ```
- **Impact** : si `.env` disparaît ou n'est pas chargé en prod, l'app démarre avec des valeurs triviales → prise de contrôle immédiate.
- **Fix** : faire crasher au démarrage si `secret_key == "changeme"` ou si `admin_password in ("admin", "changeme")` **et** `is_production`.
- **Aussi** : changer `ADMIN_PASSWORD` dans `.env` pour une chaîne longue et aléatoire.

### 🟠 3.3 Check admin dupliqué (11+ fois)

- **Fichier** : `app/routers/admin_auth.py:14` (root cause) + `app/routers/admin_cars.py` (11 routes) + probable dans `admin_rentals.py`.
- **Détail** : `require_admin` **retourne** un `RedirectResponse` au lieu de lever, forçant le pattern :
  ```python
  redirect = require_admin(request)
  if redirect:
      return redirect
  ```
- **Impact** : le jour où ces 3 lignes sont oubliées sur **une seule** route → route admin ouverte à internet.
- **Fix** : transformer `require_admin` en dépendance qui lève, puis :
  ```python
  router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])
  ```

### 🟡 3.4 Pas de rotation de session au login

- **Fichier** : `app/routers/admin_auth.py:34-36`
- **Impact** : risque de session fixation (attaque théorique, faible en pratique sur admin unique).
- **Fix** : `request.session.clear()` avant de re-set `admin_logged_in = True`.

### 🟡 3.5 SessionMiddleware laxiste en dev

- **Fichier** : `app/main.py:107-108`
- **Détail** : en dev, ni `same_site` ni `max_age`. Sessions persistantes indéfiniment.
- **Impact** : quasi nul en dev local, mais bonne hygiène.

### 🟡 3.6 Vérifier l'historique Git pour `.env`

- **État** : `.env` est bien dans `.gitignore` aujourd'hui ✅
- **À vérifier** : `git log --all --full-history -- .env` — s'il a été commité par le passé, les secrets sont dans l'historique.
- **Fix si oui** : régénérer tous les secrets (SECRET_KEY, ADMIN_PASSWORD, clés Google OAuth) + réécrire l'historique (`git filter-repo`).

---

## 4. Déjà corrigé (historique)

Les points suivants figuraient dans l'audit du 28 juillet et sont **résolus** aujourd'hui :

| Point | Statut | Preuve |
|---|---|---|
| CORS trop permissif (`allow_origins=["*"]`) | ✅ Corrigé | `app/main.py:100-106` — restreint via `settings.cors_origins` en prod |
| Sessions non sécurisées | ✅ Corrigé | `app/main.py:92-99` — `https_only=True`, `same_site="lax"`, `max_age=3600` en prod |
| Injection SQL sur `date_debut` | ✅ Faux positif | `app/routers/web.py:100-113` — validation via Pydantic `LocationForm`, ORM SQLAlchemy partout |
| Uploads non contrôlés | ✅ Corrigé | `app/routers/admin_cars.py:24-32` — PIL re-encode tout en WEBP, filename UUID, extensions arbitraires détruites |
| `.env` dans Git | ✅ Corrigé | `.gitignore` contient `.env` (historique à vérifier tout de même — voir 3.6) |

---

## 5. Plan de correction

| Priorité | Action | Fichier | Effort |
|---|---|---|---|
| 🔴 Urgent | Rate limit sur `/admin/login` via `slowapi` | `admin_auth.py` | ~30 min |
| 🔴 Urgent | Changer `ADMIN_PASSWORD` pour une chaîne longue aléatoire | `.env` | 2 min |
| 🔴 Urgent | Crasher si secrets == valeurs par défaut en prod | `config.py` | 10 min |
| 🟠 Important | Refactor `require_admin` en dépendance qui lève + `dependencies=[Depends(require_admin)]` sur les routers admin | `admin_auth.py`, `admin_cars.py`, `admin_rentals.py` | ~1h |
| 🟡 Bien | Rotation session au login (`session.clear()`) | `admin_auth.py` | 5 min |
| 🟡 Bien | `max_age` sur SessionMiddleware en dev | `main.py` | 2 min |
| 🟡 Bien | Vérifier historique Git pour `.env` — régénérer secrets si commit passé | — | 5 min |

---

## 6. À prévoir pour les prochaines features

### OAuth social (chantier suivant)

- Google/Facebook garantissent le mail vérifié → couvre le principe #4.
- **Piège** : toujours vérifier `email_verified: true` dans le token retourné (piège classique).
- Régénérer les clés Google OAuth si elles ont été commitées dans l'historique.

### Mobile Money

- Chiffrer les credentials opérateurs en base (ou les garder uniquement en `.env`).
- Logs de transaction : ne jamais logger les numéros de téléphone en clair.

### Si un jour inscription mail/mdp classique

- `passlib[bcrypt]` obligatoire.
- Check HaveIBeenPwned à l'inscription.
- Double opt-in mail.

---

## 7. Ressources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [slowapi (rate limit FastAPI)](https://github.com/laurentS/slowapi)
- [Have I Been Pwned API](https://haveibeenpwned.com/API/v3)
