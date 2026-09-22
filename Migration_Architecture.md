# Plan de migration — Architecture monolithique modulaire

## Contexte

L'application TM_Location est déjà un monolithe FastAPI. Cette migration réorganise le code interne pour :

1. **Séparer clairement Admin et Client** (deux dossiers de premier niveau)
2. **Centraliser tous les modèles** dans `app/models/` (source unique)
3. **Fusionner SQLAlchemy + Pydantic** via SQLModel (un modèle = une déclaration)
4. **Faciliter l'ajout de features** (nouveau domaine = nouveau dossier, zéro impact sur l'existant)

Aucune fonctionnalité n'est ajoutée ni supprimée. C'est une refonte de structure à comportement identique.

---

## Arborescence cible

```
app/
├── main.py                     (monte admin + client)
├── config.py
├── database.py                 (UNE seule DB)
├── csrf.py
├── limiter.py
├── templating.py
│
├── models/                     SOURCE UNIQUE (SQLModel)
│   ├── __init__.py
│   ├── base.py
│   ├── voiture.py
│   ├── reservation.py
│   ├── user.py
│   ├── analytics.py
│   └── itineraire.py
│
├── shared/
│   ├── security.py
│   ├── deps.py
│   └── utils/
│       ├── slug.py
│       └── images.py
│
├── admin/
│   ├── main.py                 (router monté sur /admin)
│   ├── auth/       (service.py + routes.py)
│   ├── voitures/
│   ├── reservations/
│   └── stats/
│
├── client/
│   ├── main.py                 (router monté sur /)
│   ├── pages/
│   ├── voitures/
│   ├── reservations/
│   ├── itineraire/
│   ├── auth/
│   │   └── providers/ (google.py, facebook.py)
│   └── analytics/
│
├── templates/
│   ├── base_admin.html
│   ├── base_client.html
│   ├── admin/{auth,voitures,reservations,stats}/
│   ├── client/{pages,voitures,reservations,itineraire,auth}/
│   └── partials/
│
└── static/
```

---

## Règles d'importation

| Zone | Peut importer depuis |
|---|---|
| `models/` | rien (couche la plus basse) |
| `shared/` | `models/` |
| `admin/` | `models/`, `shared/` |
| `client/` | `models/`, `shared/` |

**Interdit** : `admin/` importe `client/` ou l'inverse.

---

## Dépendance à ajouter

```
sqlmodel>=0.0.22
```

SQLAlchemy, Pydantic, Alembic restent — SQLModel les utilise.

---

## Migration en 8 étapes

Chaque étape laisse l'application **fonctionnelle**. Test end-to-end après chaque étape avant de passer à la suivante.

### Étape 1 — Préparation

- Sauvegarder la DB : `cp data/tm_location.db data/tm_location.db.pre_migration`
- Créer une branche : `git checkout -b refonte-architecture`
- Ajouter `sqlmodel>=0.0.22` à `requirements.txt`
- `pip install -r requirements.txt`

### Étape 2 — Créer `app/models/` (source unique)

Créer les fichiers avec les classes SQLModel équivalentes aux modèles actuels :

- `app/models/__init__.py` — ré-exports
- `app/models/base.py` — `SQLModel` importé + mixin `TimestampMixin` si utile
- `app/models/voiture.py` — `Voiture`, `VoitureImage`, `TypeLocation` (+ `VoitureCreate/Update/Read`)
- `app/models/reservation.py` — `Location` (+ `LocationCreate/Read`)
- `app/models/user.py` — `User` (+ `UserRead`)
- `app/models/analytics.py` — `AnalyticsEvent` (+ `EventIn`)
- `app/models/itineraire.py` — schémas non-table (`ItineraireRequest`, `DevisResponse`)

**Important** : garder **exactement les mêmes noms de tables et colonnes** que dans `app/models/models.py` actuel. La DB ne bouge pas.

Vérification : `python -c "from app.models import *"` sans erreur.

### Étape 3 — Adapter `database.py` et Alembic

- `app/database.py` : `create_all` basé sur `SQLModel.metadata`
- `alembic/env.py` :
  ```python
  from sqlmodel import SQLModel
  import app.models  # peuple metadata
  target_metadata = SQLModel.metadata
  ```
- `alembic revision --autogenerate -m "sqlmodel migration check"` → doit générer une migration **vide** (preuve d'équivalence). Si non vide, corriger `app/models/` jusqu'à équivalence.

### Étape 4 — Créer `app/shared/`

Déplacer :

- `app/utils/slug.py` → `app/shared/utils/slug.py`
- Créer `app/shared/utils/images.py` (extraire la logique Pillow de `admin_cars.py`)
- Créer `app/shared/security.py` (auth admin, `get_current_user` OAuth)
- Créer `app/shared/deps.py` (`get_db`, `csrf_check`)

Mettre à jour les imports dans les fichiers qui utilisaient ces utils.

### Étape 5 — Migrer le domaine `auth/` (le plus petit)

**Admin auth** :
- `app/admin/auth/routes.py` ← contenu de `app/routers/admin_auth.py`
- Imports : `from app.models.user import User`, `from app.shared.security import ...`

**Client auth (OAuth)** :
- `app/client/auth/routes.py` ← routes OAuth de `app/routers/auth.py`
- `app/client/auth/providers/google.py` ← logique Google
- `app/client/auth/providers/facebook.py` ← logique Facebook
- `app/client/auth/service.py` ← `create_or_update_user`

Mettre à jour `app/main.py` pour monter ces nouveaux routers. Supprimer `app/routers/admin_auth.py` et `app/routers/auth.py` **uniquement après validation**.

**Test manuel** : login admin OK, OAuth Google OK, OAuth Facebook OK.

### Étape 6 — Migrer les autres domaines (un à un)

Ordre suggéré (du plus simple au plus complexe) :

1. **Analytics** → `admin/stats/` + `client/analytics/`
   - Depuis : `app/routers/analytics_api.py`, `app/routers/admin_stats.py`, `app/services/analytics_service.py`, `app/services/analytics_admin_service.py`

2. **Voitures** → `admin/voitures/` + `client/voitures/`
   - Depuis : `app/routers/admin_cars.py`, parties voitures de `app/routers/web.py`, `app/services/admin_service.py`, `app/services/car_service.py`

3. **Réservations** → `admin/reservations/` + `client/reservations/`
   - Depuis : `app/routers/admin_rentals.py`, parties réserver de `app/routers/web.py`, `app/services/reservation_service.py`, `app/services/type_location_rules.py` (→ `client/reservations/rules.py`)

4. **Itinéraire** → `client/itineraire/`
   - Depuis : `app/routers/itineraire_api.py`, `app/services/routing_service.py`
   - Créer `client/itineraire/external.py` pour clients httpx (BRouter, OSRM, Nominatim)

5. **Pages** → `client/pages/`
   - Depuis : parties accueil/profile/robots/sitemap de `app/routers/web.py`

Pour chaque domaine migré :
- Créer `service.py` + `routes.py` (et sous-modules si besoin)
- Mettre à jour les imports dans `app/main.py`
- Tester manuellement les endpoints concernés
- Supprimer les anciens fichiers `app/routers/xxx.py` et `app/services/xxx.py`

### Étape 7 — Réorganiser les templates

Déplacer les templates dans la nouvelle structure :

```
templates/
├── base_client.html         (ex base.html)
├── base_admin.html          (déjà existant)
├── admin/{auth,voitures,reservations,stats}/
├── client/{pages,voitures,reservations,itineraire,auth}/
└── partials/
```

Mettre à jour les chemins dans les `templates.TemplateResponse(...)` de chaque `routes.py`.

Idem pour `static/js/` : créer `static/js/admin/` et `static/js/client/` si pertinent.

### Étape 8 — Nettoyage final

- Supprimer les dossiers vides : `app/routers/`, `app/services/`, `app/models/models.py`, `app/schemas.py`
- `alembic revision --autogenerate -m "post migration check"` → doit être vide
- Lancer l'app : `python run.py` — vérifier absence de warnings
- Passer en revue les imports morts avec `ruff check` ou équivalent

---

## Fichiers critiques (à ne pas casser)

| Fichier actuel | Devient |
|---|---|
| `app/main.py` | reste — monte `admin.main.router` + `client.main.router` |
| `app/config.py` | reste identique |
| `app/database.py` | adapté pour `SQLModel.metadata` |
| `app/csrf.py`, `app/limiter.py`, `app/templating.py` | restent identiques |
| `app/models/models.py` | supprimé (remplacé par `app/models/*.py`) |
| `app/schemas.py` | supprimé (fusionné dans `app/models/*.py`) |
| `app/routers/*.py` | supprimés (répartis dans `admin/` et `client/`) |
| `app/services/*.py` | supprimés (déplacés dans les domaines respectifs) |
| `alembic/env.py` | 2 lignes modifiées (import + `target_metadata`) |
| `data/tm_location.db` | intact (schéma DB inchangé) |

---

## Vérification end-to-end (à faire après chaque étape)

**Parcours client** :
1. `GET /` → accueil affiche 6 voitures
2. `GET /voitures` → catalogue
3. `GET /voitures/{slug}` → détail
4. `GET /voitures/{slug}/itineraire` → carte Leaflet fonctionne
5. Calcul itinéraire → devis affiché
6. `POST /voitures/{slug}/reserver` → réservation créée
7. OAuth Google → login OK
8. OAuth Facebook → login OK

**Parcours admin** :
1. `GET /admin/login` → login
2. `GET /admin` → dashboard avec stats
3. `GET /admin/voitures` → liste voitures
4. Créer / éditer / supprimer une voiture → OK
5. Upload image → WebP + resize OK
6. Créer / supprimer un type de location → OK
7. `GET /admin/reservations` → liste
8. Changer statut → OK
9. `GET /admin/stats` → graphiques + heatmap OK

**DB** :
- `alembic upgrade head` sans erreur
- `alembic revision --autogenerate` → doit être vide

---

## Rollback

Chaque étape est un commit isolé. En cas de problème :

```bash
git log --oneline
git reset --hard <commit-avant-etape>
cp data/tm_location.db.pre_migration data/tm_location.db  # si DB touchée
```

La branche `refonte-architecture` reste isolée de `main` jusqu'à validation complète.

---

## Après la migration : ajout d'une nouvelle feature

Exemple — Paiement Mobile Money :

1. Créer `app/models/paiement.py` (SQLModel)
2. `alembic revision --autogenerate -m "add paiement"`
3. Créer `app/client/paiements/` (routes + service + providers Mvola/Orange/Airtel)
4. Créer `app/admin/paiements/` (supervision)
5. Créer `templates/client/paiements/` et `templates/admin/paiements/`
6. Enregistrer les routers dans `app/admin/main.py` et `app/client/main.py`

Aucune modification des domaines existants.
