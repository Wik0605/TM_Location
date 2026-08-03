# Architecture de l'application Spass Gasy

> Ce document explique l'architecture de l'application et les choix techniques effectués.

## Vue d'ensemble

```
TM_Location/
├── app/                          # Code principal de l'application
│   ├── __init__.py
│   ├── main.py                   # Point d'entrée FastAPI + seed données initiales
│   ├── database.py               # Configuration SQLAlchemy async + SQLite
│   ├── schemas.py                # Schémas Pydantic (validation API)
│   ├── models/                   # Modèles SQLAlchemy (tables DB)
│   │   ├── __init__.py           # Exports : Car, City, RentalType, CarImage...
│   │   └── models.py             # Définitions des tables + données initiales
│   ├── routers/                  # Routes FastAPI
│   │   ├── __init__.py
│   │   └── web.py                # Routes pages web HTML
│   ├── services/                 # Logique métier (requêtes DB)
│   │   ├── __init__.py
│   │   ├── car_service.py        # CRUD voitures
│   │   ├── city_service.py       # Lecture villes (utilisé par page d'accueil)
│   │   └── rental_service.py    # Types de location
│   ├── templates/                # Templates Jinja2
│   │   ├── base.html             # Template de base (navbar, footer, bottom nav)
│   │   ├── index.html            # Page d'accueil
│   │   ├── cars.html             # Liste des voitures
│   │   ├── car_detail.html       # Détail d'un véhicule
│   │   ├── itineraire.html       # Calculateur d'itinéraire (Leaflet + BRouter)
│   │   ├── booking.html          # Réservation
│   │   ├── rental_types.html     # Tarifs
│   │   ├── contact.html          # Contact
│   │   ├── 404.html              # Page non trouvée
│   │   └── partials/             # Fragments HTMX
│   │       ├── _car_grid.html
│   │       └── _car_list.html
│   └── static/                   # Fichiers statiques servis par FastAPI
├── alembic/                      # Migrations base de données
│   └── versions/                 # Fichiers de migration
├── data/                         # Base de données SQLite
│   └── spass_gasy.db
├── docs/                         # Documentation
├── .vscode/
│   └── settings.json             # formatOnSave:false pour HTML (protège Jinja2)
├── run.py                        # Script de lancement
└── requirements.txt              # Dépendances Python
```

## Stack technique

### Backend : FastAPI

**Pourquoi FastAPI ?**

FastAPI est un framework web moderne pour Python qui offre :
- **Performance** : Très rapide grâce à Starlette et Pydantic
- **Typage automatique** : Validation et sérialisation automatiques
- **Documentation** : Swagger UI et ReDoc générés automatiquement
- **Async** : Support natif de l'asynchrone

**Exemple concret** :

```python
# Route simple avec validation
@router.get("/cars/{car_id}")
async def get_car(car_id: int):  # car_id est automatiquement validé comme entier
    ...
```

### Frontend : HTMX + Tailwind CSS

**Pourquoi HTMX ?**

HTMX permet de créer des interfaces dynamiques sans JavaScript complexe :

```html
<!-- Ce bouton remplace le contenu de #results avec la réponse du serveur -->
<button hx-get="/api/cars/search" hx-target="#results">
    Rechercher
</button>
```

**Avantages** :
- Pas de framework JavaScript lourd
- Code serveur simple (retourne du HTML)
- SEO-friendly (le contenu est dans le HTML)

**Pourquoi Tailwind CSS ?**

Tailwind est un framework CSS "utility-first" qui permet de :
- Prototyper rapidement
- Maintenir une cohérence visuelle
- Personnaliser facilement

### Base de données : SQLAlchemy + SQLite

**Pourquoi SQLAlchemy ?**

- ORM puissant et mature
- Support de l'async (avec aiosqlite)
- Migrations faciles avec Alembic

**Pourquoi SQLite en développement ?**

- Pas d'installation requise
- Fichier unique facile à sauvegarder
- Parfait pour le prototypage

**Migration vers PostgreSQL** :

Pour passer en production, il suffit de changer la connection string :

```python
# Développement
DATABASE_URL = "sqlite+aiosqlite:///./data/spass_gasy.db"

# Production
DATABASE_URL = "postgresql+asyncpg://user:password@host:5432/dbname"
```

## Modèles de données

### Diagramme Entité-Association

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  CarImage   │     │    Car      │     │  RentalType │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ id          │     │ id          │────►│ id          │
│ car_id      │────►│ brand       │     │ name        │
│ url         │     │ model       │     │ duration    │
│ position    │     │ daily_price │     │ multiplier  │
└─────────────┘     │ is_available│     │ discount    │
                    │ seats       │     └─────────────┘
                    └──────┬──────┘            │
                           │                   │
                           ▼                   │
                    ┌─────────────┐            │
                    │   Rental    │◄───────────┘
                    ├─────────────┤
                    │ id          │
                    │ car_id      │
                    │ rental_type │
                    │ customer    │
                    │ start_date  │
                    │ end_date    │
                    │ total_price │
                    └─────────────┘
```

### Relations

- **Car → CarImage** : Une voiture peut avoir plusieurs photos (one-to-many)
- **Car → Rental** : Une voiture peut avoir plusieurs locations (one-to-many)
- **RentalType → Rental** : Un type de location peut avoir plusieurs locations (one-to-many)

## Flux de données

### Page d'accueil

```
Utilisateur → GET /
    ↓
router.web.home()
    ↓
1. Récupérer RentalType depuis DB
2. Récupérer Cars disponibles depuis DB (avec images)
    ↓
Template index.html + données
    ↓
HTML → Navigateur
```

### Recherche dynamique (HTMX)

```
Utilisateur → Applique un filtre (prix, places...)
    ↓
HTMX → GET /api/cars/search?...
    ↓
router.web.search_cars()
    ↓
Filtrer Cars selon les critères
    ↓
Template _car_grid.html (fragment)
    ↓
HTML → HTMX remplace #car-results
```

## Décisions architecturales

### 1. Séparation Models/Schemas

**Problème** : Les modèles SQLAlchemy et les schémas API ont des besoins différents.

**Solution** : Séparer les deux.

```python
# models.py - Représentation DB
class Car(Base):
    __tablename__ = "cars"
    id: Mapped[int] = mapped_column(primary_key=True)
    # ... champs DB

# schemas.py - Représentation API
class CarCreate(BaseModel):
    brand: str
    model: str
    # ... champs API (validation)
```

**Avantage** : On peut masquer des champs sensibles (mot de passe) ou ajouter des champs calculés.

### 2. Templates partiels pour HTMX

**Problème** : HTMX a besoin de fragments HTML, pas de pages complètes.

**Solution** : Créer des templates partiels.

```html
<!-- index.html -->
<div hx-get="/api/cars/popular" hx-trigger="load">
    <!-- Le contenu sera remplacé par _car_grid.html -->
</div>

<!-- _car_grid.html -->
<!-- Juste le fragment HTML, pas de <html> ou <body> -->
<div class="grid">
    {% for car in cars %}
    ...
    {% endfor %}
</div>
```

### 3. Navigation mobile en bas

**Problème** : Les applications mobiles modernes ont la navigation en bas.

**Solution** : Barre de navigation fixe en bas.

```html
<nav class="fixed bottom-0 ...">
    <a href="/">Accueil</a>
    <a href="/cars">Véhicules</a>
    <!-- ... -->
</nav>
```

**Pourquoi ?**
- Zone confortable pour les pouces
- Standard sur iOS et Android
- Toujours accessible pendant le scroll

## Scalabilité

### Niveau actuel : 10-100 locations/jour

- SQLite suffit
- Un serveur FastAPI
- Pas de cache nécessaire

### Niveau suivant : 100-1000 locations/jour

- Passer à PostgreSQL
- Ajouter Redis pour le cache
- Séparer les services (microservices)

### Niveau élevé : 1000+ locations/jour

- Load balancing
- Base de données répliquée
- CDN pour les fichiers statiques

## Prochaines étapes

1. **Authentification** : Ajouter un système de login
2. **Panier** : Permettre plusieurs locations
3. **Paiement** : Intégrer un système de paiement
4. **Admin** : Interface d'administration
5. **Tests** : Tests unitaires et d'intégration

## Questions fréquentes

### Pourquoi pas React/Vue ?

Pour une application de location de voitures avec un budget limité, HTMX offre :
- Développement plus rapide
- Moins de complexité
- SEO natif
- Pas besoin d'API séparée

### Pourquoi async/await ?

FastAPI est asynchrone par nature. Cela permet de :
- Gérer plus de requêtes simultanément
- Utiliser des bases de données asynchrones
- Meilleure performance sous charge

### Comment déployer ?

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer en production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```