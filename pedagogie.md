# Pédagogie — Compréhension du web

Document de suivi de l'apprentissage web de Tafita sur le projet TM_Location.
Profil : entrepreneur, vision produit, non-dev de formation, passionné par la tech.

---

## Session d'évaluation du 2026-08-19

Format : 3 questions ouvertes, réponse libre, correction ciblée.
(La question 4 sur HTML complet vs fragment HTMX est reportée au Module 3.)

### Question 1 — Flux complet d'une réservation (POST)

**Acquis** : structure globale du flux client → serveur → DB → réponse bien maîtrisée.

**Corrections apportées :**

1. **Client/serveur** : FastAPI **répond** aux requêtes, il n'émet pas de GET/POST lui-même. C'est le navigateur (ou HTMX) qui initie.
2. **Migrations Alembic ≠ requêtes SQL courantes** : Alembic modifie la **structure** des tables (une fois), les INSERT/UPDATE se font à chaque requête.
3. **Pydantic vs service** : Pydantic valide le **format**, le service valide la **logique métier**.
4. **Jinja2 ≠ f-string Python** : Jinja2 est un moteur de templates avec sa propre syntaxe (`{{ variable }}`, `{% for %}`), exécuté côté serveur pour produire le HTML final.

---

### Question 2 — Validation des données

**Acquis** : séparation validation format (Pydantic) / logique métier (service) bien comprise. Exemples métier pertinents (double réservation, bascule automatique en location journée).

**Corrections apportées :**

5. **Numéro de téléphone → `str`, pas `int`** : sinon perte du `0` initial et impossible de gérer `+261`.
   **Règle générale** : si on ne fait pas de calculs dessus, c'est une chaîne.

6. **Erreur Pydantic par défaut = JSON 422**, pas du HTML.
   ```json
   {"detail": [{"loc": ["body", "telephone"], "msg": "field required"}]}
   ```
   Pour renvoyer un fragment HTML à HTMX, il faut un exception handler personnalisé :
   ```python
   @app.exception_handler(RequestValidationError)
   ```

7. **Un service ne renvoie jamais de HTML** : il lève une exception, la **route** capture et traduit en HTML.
   - **Service** = logique métier pure, ne connaît ni HTTP ni HTML
   - **Route** = traduit exceptions → réponses HTTP/HTML

---

### Question 3 — SQLAlchemy (`add` / `commit` / `refresh`)

**Acquis** : intuition juste sur le rôle de chaque fonction, notion de transaction bien comprise.

**Corrections apportées :**

8. **`db.add()` ne touche pas la base** : ajoute l'objet dans la **session en mémoire** (staging). Analogie : équivalent de `git add`.

9. **`db.commit()`** fait deux choses :
   - Envoie les instructions SQL (`INSERT INTO ...`) au serveur DB
   - Valide la transaction : les changements deviennent visibles pour les autres connexions

10. **`db.refresh()`** recharge l'objet Python depuis la base pour récupérer les champs générés côté DB (`id` auto-incrémenté, `created_at`, valeurs par défaut SQL).
    ```python
    reservation = Reservation(nom="Jean")  # id = None
    db.add(reservation)                     # toujours None
    db.commit()                             # inséré en base
    db.refresh(reservation)                 # reservation.id = 42
    ```

11. **ACID — Atomicité** : crash entre `add()` et `commit()` → rien en base. La mémoire est perdue avec le process.

**Tableau récap :**

| Fonction | Où ça agit | Ce que ça fait |
|---|---|---|
| `add()` | Mémoire (session) | Prépare l'insertion |
| `commit()` | Base de données | Envoie + valide |
| `refresh()` | Mémoire ← Base | Recharge l'objet avec les valeurs générées |

---

## Roadmap d'apprentissage (7 modules)

Ordre calibré pour un profil **vision produit** : on part toujours de "à quoi ça sert pour l'utilisateur" avant d'entrer dans la technique.

### Module 1 — Le web comme conversation (fondations)
Comprendre que tout est une suite requête/réponse pour raisonner sur n'importe quelle feature.
- HTTP : verbes (GET, POST, PUT, DELETE), codes de statut (200, 4xx, 5xx)
- Headers : Cookie, Authorization, Content-Type
- Cycle complet : DNS → serveur → routing → réponse
- **Exercice** : dessiner sur papier le flux d'une feature TM_Location de bout en bout

### Module 2 — HTML rendu côté serveur (Jinja2)
Comprendre comment le HTML est fabriqué pour contrôler l'UX.
- Templates Jinja2 : syntaxe, héritage (`{% extends %}`, `{% block %}`)
- Différence template complet vs fragment
- Passage de contexte : Python → template
- **Exercice** : identifier dans TM_Location les templates complets vs fragments

### Module 3 — HTMX (le pont interactivité/simplicité)
Comprendre pourquoi HTMX plutôt que React change ta vision de la complexité web.
- Attributs de base (`hx-get`, `hx-post`, `hx-target`, `hx-swap`)
- Fragments HTML retournés par le serveur
- Gestion des erreurs côté HTMX
- **Traite la question 4 en attente** : quand renvoyer un HTML complet vs un fragment

### Module 4 — Validation et sécurité produit
Chaque champ mal validé = mauvaise donnée = décisions produit faussées.
- Pydantic en profondeur : validators custom, messages d'erreur
- Handler d'erreurs personnalisé pour HTMX (`RequestValidationError`)
- Sanitization : injection SQL, XSS (ce que SQLAlchemy et Jinja2 t'évitent déjà)
- Auth : sessions, cookies, JWT — quand utiliser quoi

### Module 5 — Base de données côté produit
La DB est ton produit à long terme. Mauvais schéma = dette qui bloque les features futures.
- Relations : one-to-many, many-to-many
- Contraintes SQL : `UNIQUE`, `NOT NULL`, `FOREIGN KEY`, index
- Transactions ACID (approfondissement)
- Migrations Alembic : quand créer, comment relire
- **Exercice** : dessiner le schéma TM_Location et identifier ce qui manque pour Mobile Money

### Module 6 — Déploiement et production
Une app qui marche en local ne marche pas forcément en prod.
- Serveur ASGI (Uvicorn), reverse proxy (Nginx)
- Variables d'environnement, secrets
- Logs et monitoring
- Sauvegardes DB

### Module 7 — Performance et scalabilité (plus tard)
À repousser tant que tu n'as pas d'utilisateurs réels.
- Requêtes N+1 (piège classique SQLAlchemy)
- Caching
- Index DB

---

## Ordre prioritaire recommandé

Vu l'état d'avancement de TM_Location :

1. **Module 3 (HTMX)** — traite la question 4 en attente + usage quotidien
2. **Module 4 (validation/sécurité)** — bloquant avant Mobile Money
3. **Module 5 (DB)** — nécessaire pour bien modéliser les paiements
4. **Modules 1 et 2** — piqûres de rappel à intercaler
5. **Modules 6-7** — à l'approche du déploiement réel

---

## Méthode de travail

1. Un module à la fois, pas de saut en avant
2. Chaque module se termine par un exercice appliqué à TM_Location
3. Format questions ouvertes : tu réponds avec tes mots, correction sur les précisions
4. Résumé écrit à la fin de chaque module dans ce fichier, avec **tes mots à toi**

---

## Critères de validation d'un module

- Tu peux expliquer avec tes mots le concept sans regarder de doc
- Tu peux pointer dans TM_Location un exemple concret du concept
- Tu peux identifier une décision produit que ce concept t'aide à prendre
