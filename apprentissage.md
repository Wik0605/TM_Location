1. HTTP en profondeur
  
  - Méthodes, codes de statut (200, 201, 400, 401,
  403, 404, 422, 500...)
  - Headers importants : Content-Type, Authorization,
   Cache-Control, Set-Cookie
  - Différence GET vs POST vs PUT vs PATCH vs DELETE
  - Idempotence (pourquoi PUT ≠ POST)

  2. Cookies et Sessions

  - Ce qu'est un cookie (clé/valeur stocké dans le
  navigateur)
  - HttpOnly, Secure, SameSite (Lax / Strict / None)
  - Pourquoi localhost ≠ 127.0.0.1 pour les cookies
  - Session côté serveur vs cookie signé côté client

  3. Authentification et Autorisation

  - JWT : structure (header.payload.signature),
  expiration, refresh token
  - Sessions : cookie de session + stockage serveur
  (Redis, DB)
  - OAuth2 : le flux Authorization Code, le paramètre
   state anti-CSRF
  - Différence authn (qui es-tu ?) vs authz (t'as le
  droit ?)
  - Hachage de mot de passe : bcrypt, pourquoi jamais
   MD5/SHA1 seul

  4. Sécurité web (OWASP Top 10)

  - SQL Injection : toujours des requêtes paramétrées
  - XSS : échapper les sorties HTML
  - CSRF : token CSRF ou SameSite cookie
  - IDOR : vérifier que l'utilisateur possède la
  ressource qu'il demande
  - Rate limiting : limiter les tentatives de login
  - Variables sensibles dans .env, jamais dans le
  code

  5. Base de données au-delà du SELECT/INSERT

  - Index : pourquoi, quand, sur quelles colonnes
  - Transactions : ACID, commit/rollback
  - N+1 problem : charger les relations en une seule
  requête
  - Migrations : versionner le schéma (Alembic,
  Flyway...)
  - Différence JOIN vs sous-requête vs ORM lazy
  loading

  6. API Design

  - REST : ressources, nommage des routes
  (/users/{id} pas /getUser)
  - Pagination : offset vs cursor
  - Versioning : /api/v1/...
  - Validation des entrées : ne jamais faire
  confiance au client
  - Réponses d'erreur cohérentes (format standard)

  7. Asynchrone et tâches de fond

  - Pourquoi ne pas faire du long traitement dans une
   requête HTTP
  - Queue / Worker : Celery, RQ, ARQ
  - Webhooks : recevoir des événements externes
  - Différence sync vs async dans le code (Python
  async/await)

  8. Cache

  - Pourquoi cacher : réduire les appels DB,
  accélérer les réponses
  - Redis : cas d'usage (cache, sessions, rate
  limiting, queues)
  - TTL (Time To Live), invalidation de cache
  - Cache HTTP : ETag, Cache-Control

  9. Logs et Observabilité

  - Différence print vs logger structuré
  - Niveaux : DEBUG / INFO / WARNING / ERROR /
  CRITICAL
  - Ce qu'il faut loguer (et ce qu'il ne faut PAS :
  mots de passe, tokens)
  - Traces et monitoring basique

  10. Déploiement et environnement

  - Variables d'environnement : dev / staging / prod
  - Docker : image, container, docker-compose
  - Reverse proxy : Nginx devant l'app
  - HTTPS, certificats TLS (Let's Encrypt)
  - Healthcheck endpoint

  ---
  Priorité pour toi maintenant (par rapport à ton
  projet TM_Location) :
  
  Priorité: 🔴 Urgent
  Notion: Cookies/sessions, OAuth2, JWT
  ────────────────────────────────────────
  Priorité: 🟠 Important
  Notion: Sécurité OWASP, Index DB, Cache
  ────────────────────────────────────────
  Priorité: 🟡 Moyen terme
  Notion: Queues, Logs structurés, Docker
