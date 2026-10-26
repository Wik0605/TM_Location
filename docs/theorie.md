# Analyse théorique de TM_Location

## Contexte

Document pédagogique répondant aux 4 questions posées : situer TM_Location dans la littérature du génie logiciel (analyse des besoins → conception → développement → tests/sécurité). Objectif : donner un cadre conceptuel pour expliquer l'app (mémoire, soutenance, documentation).

---

## 1. Analyse du besoin

### Description concrète (ce que fait TM_Location)
Plateforme web de **location de voitures à Antananarivo (Madagascar)**, destinée à trois profils :
- **Clients** : touristes et locaux, authentification sociale (Google/Facebook prévus), réservation avec itinéraire.
- **Visiteurs anonymes** : exploration libre, quota de 7 calculs d'itinéraire/jour (anti-abus).
- **Administrateur** : gestion de la flotte, des réservations, statistiques.

Besoins fonctionnels principaux : catalogue de véhicules filtré par dates, calcul d'itinéraire + distance + coût, réservation, back-office admin.
Besoins non-fonctionnels : mobile-first (PWA), responsive, performant sur réseau mobile malgache, souveraineté progressive (hébergement local des tuiles OSM à moyen terme).

### Cadre théorique
L'**analyse du besoin** (requirements engineering, Sommerville, *Software Engineering*) sépare :
- **Besoins fonctionnels** : *ce que* le système doit faire (user stories, cas d'usage UML).
- **Besoins non-fonctionnels** : *comment* il doit le faire (performance, sécurité, utilisabilité — ISO/IEC 25010 "qualité produit").

TM_Location relève du modèle **B2C transactionnel** avec dimension **géospatiale** (SIG — Système d'Information Géographique). Il s'inscrit dans la littérature des **plateformes de mobilité** (Shaheen & Cohen, 2013, *Carsharing and Personal Vehicle Services*).

Méthode mobilisée : **approche itérative/agile** — pas de cahier des charges figé, le besoin émerge par cycles courts (cf. règle projet : "pas d'initiative, pas d'excès", ce qui correspond au principe YAGNI — *You Aren't Gonna Need It*, Beck).

---

## 2. Conception et architecture

### Description concrète

**Architecture logicielle** : monolithe modulaire orienté domaine.
- `app/client/` (espace public) et `app/admin/` (espace admin) séparés.
- `app/models/` (couche persistance SQLModel), `app/shared/` (sécurité, dépendances), `app/templating.py` (Jinja2 avec `PrefixLoader`).
- Pattern **MVC/MVT** (Model = SQLModel, View = Jinja2, Controller = routes FastAPI).

**Base de données** : PostgreSQL + **PostGIS** (après migration SQLite, octobre 2026). Identifiants en **UUID v7** (triables temporellement, meilleurs qu'UUID v4 pour les index B-tree).
Entités principales : `User`, `Voiture`, `VoitureImage`, `TypeLocation`, `Location` (réservation), `Quartier` (géométries PostGIS Fokontany), `Analytics`.
Relations : `Voiture 1-N Image`, `Voiture 1-N Location`, `Voiture 1-N TypeLocation`.

**UI/UX** : Tailwind CSS + glassmorphism, nav bottom mobile, carte Leaflet (OSM, Nominatim, BRouter/OSRM), PWA (manifest + service worker offline).

### Cadre théorique
- **Architecture logicielle** : *monolithe modulaire* (Fowler, *MonolithFirst*) — pertinent pour un MVP ; opposé aux microservices prématurés.
- **Modélisation données** : approche **MCD → MLD → MPD** (Merise). Les relations N-aires et l'héritage sont évités, cohérent avec la **3ᵉ forme normale** (Codd). PostGIS introduit la dimension **spatiale** (OGC Simple Features, standard ISO 19125).
- **UI/UX** : principes de Nielsen (10 heuristiques — visibilité du statut, cohérence, prévention d'erreurs). *Mobile-first* (Luke Wroblewski, 2011) : contrainte stricte justifiée par le contexte malgache (bande passante, smartphones Android bas-de-gamme).
- **PWA** (Progressive Web App, Russell 2015) : compromis entre native et web ; pertinent quand les stores sont peu accessibles.
- **Modèle UUID v7** (RFC 9562, 2024) : littérature récente sur identifiants distribués (vs auto-increment, vs UUID v4).

---

## 3. Développement (Backend, API, Frontend)

### Description concrète

**Backend** : **FastAPI** (Python async, basé sur Starlette + Pydantic), serveur ASGI **uvicorn**. ORM : SQLAlchemy async + SQLModel. Migrations : **Alembic**.

**API** : essentiellement **server-rendered** (HTML via Jinja2) + quelques endpoints JSON :
- `/api/reverse-geocode` (proxy Nominatim),
- `/api/routing` (calcul distance via BRouter/OSRM, rate-limité).
Routes publiques : `/`, `/voitures`, `/voitures/{slug}`, `/voitures/{slug}/itineraire`, `/auth/*`. Routes admin : `/admin/*` protégées par session.

**Frontend** : **HTMX** (hypermedia-driven) + Jinja2 + Tailwind + vanilla JS pour la carte (`static/js/itineraire/` : `map.js`, `state.js`, etc.). Pas de framework SPA (React/Vue).

### Cadre théorique

- **FastAPI** : framework **ASGI**, exploite `async/await` pour la **concurrence coopérative** (vs threads). Littérature : Tiangolo (2018+), concepts hérités de Flask/Starlette, validation par types (PEP 484, Pydantic → JSON Schema).
- **HTMX** : courant **HOWL / hypermedia-driven** (Carson Gross, *Hypermedia Systems*, 2023), retour aux principes **HATEOAS** de REST (Fielding, 2000). Alternative pragmatique à React/Vue : moins de complexité JS, meilleur TTI (Time To Interactive) sur mobile — cohérent avec la contrainte malgache.
- **Server-Side Rendering (SSR)** vs **CSR** (Client-Side Rendering) : TM_Location choisit SSR + "sprinkles" d'interactivité (JS progressif, Jeremy Keith). Avantages : SEO, performance initiale, accessibilité.
- **ORM asynchrone** : pattern **Unit of Work** + **Session factory** (Fowler, *PoEAA*).
- **API design** : hybride — HTML pour l'UI, JSON pour les intégrations tierces (cartographie). Correspond au principe **"use the right tool"** vs API-first stricte.

---

## 4. Tests et sécurité

### Description concrète

**Sécurité implémentée** :
- **CSRF** : token en session + validation header (`secrets.compare_digest`).
- **Sessions** : cookies `HttpOnly`, `SameSite=Lax`, `Secure` en production, rotation à la connexion admin.
- **Rate limiting** : `slowapi` sur login (5/15min) et routing anonyme (7/jour).
- **Headers HTTP** : CSP, HSTS, X-Frame-Options DENY (ajoutés au déploiement, pas en dev — cf. règle projet).
- **Validation** : Pydantic sur toutes les entrées.
- **Hash** : (à vérifier — probablement bcrypt/argon2 pour admin).

**Tests** : pas de suite automatisée (`tests/` absent). Validation manuelle documentée dans `tests_securite.md` (14 points de contrôle).

### Cadre théorique

- **Référentiel sécurité** : **OWASP Top 10** (2021) — TM_Location adresse A01 (Broken Access Control via sessions admin), A03 (Injection via Pydantic + ORM paramétré), A05 (Misconfiguration via CSP/HSTS), A07 (Auth failures via rate-limiting + CSRF).
- **Défense en profondeur** (Saltzer & Schroeder, 1975, *The Protection of Information in Computer Systems*) : plusieurs couches (validation, CSRF, rate-limit, headers).
- **Principe du moindre privilège** : séparation client/admin, OAuth plutôt que mot de passe pour les clients.
- **Rate limiting** : *token bucket* / *fixed window* — littérature en déni de service applicatif (Cloudflare, 2017+).
- **CSRF** : attaque décrite par Zeller & Felten (2008), défense par *synchronizer token pattern*.
- **Tests logiciels** : pyramide de Cohn (*unitaires → intégration → E2E*). L'absence de tests automatisés est un **risque assumé d'MVP** (cf. Reinertsen, *Principles of Product Development Flow*). À planifier : `pytest` + `httpx.AsyncClient` + fixtures PostgreSQL (testcontainers).
- **Sécurité "shift-left"** : la documentation `tests_securite.md` montre une approche manuelle ; l'automatisation (CI, SAST, dependabot) est une étape de maturité suivante.

---

## Synthèse académique

TM_Location est un exemple de **monolithe modulaire pragmatique** combinant :
- *Hypermedia-driven architecture* (HTMX) pour minimiser la complexité client,
- *Async Python* (FastAPI) pour la scalabilité I/O,
- *SIG embarqué* (PostGIS) pour la logique métier géographique,
- *Mobile-first PWA* adapté au contexte sociotechnique malgache,
- *Sécurité par défense en profondeur* conforme OWASP, avec dette technique assumée côté tests.

Il illustre les arbitrages classiques du **génie logiciel appliqué à un MVP** : simplicité > exhaustivité, livraison > perfection, itération > spécification figée (manifeste Agile, 2001).

---

## Références utiles pour la soutenance

- Sommerville, *Software Engineering* (10ᵉ éd.) — besoins, cycle de vie.
- Fowler, *Patterns of Enterprise Application Architecture* — MVC, UoW, SSR.
- Fielding (2000), thèse REST — HATEOAS, hypermedia.
- Carson Gross, *Hypermedia Systems* (2023) — HTMX.
- Nielsen (1994), *10 Usability Heuristics*.
- OWASP Top 10 (2021).
- ISO/IEC 25010 — qualité logicielle.
- RFC 9562 (UUID v7).
- Luke Wroblewski (2011), *Mobile First*.
