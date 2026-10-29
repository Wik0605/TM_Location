# Migration SQLite → PostgreSQL + UUID v7 — Théorie pour débutant

Ce document explique **le pourquoi et le comment** de la migration qu'on est en train de faire sur TM_Location. Il est écrit pour toi, à ton niveau actuel : tu connais bien Python/FastAPI, tu débutes complètement avec Docker et PostgreSQL.

---

## 1. Docker — c'est quoi et pourquoi on l'utilise

### 1.1. Le problème que Docker résout

Sans Docker, pour utiliser PostgreSQL sur ton Mac, tu dois :
1. Télécharger PostgreSQL depuis leur site.
2. L'installer (avec droits admin).
3. Configurer un service qui tourne au démarrage.
4. Gérer les mises à jour, les conflits de version, les fichiers de config éparpillés.
5. Si un jour tu veux tester **PostgreSQL 16 et 17 en parallèle** → cauchemar.

Docker règle tout ça : chaque logiciel tourne dans une **boîte isolée** appelée **conteneur**.

### 1.2. Vocabulaire de base

| Terme | Analogie simple |
|---|---|
| **Image** | Un plan de maison (fichier figé, réutilisable). Ex : `postgres:17-alpine` |
| **Conteneur** | Une maison construite à partir du plan. Tu peux avoir 10 maisons à partir du même plan. |
| **Docker Hub** | Le catalogue de plans publics (comme PyPI pour Python). |
| **Volume** | Une clé USB branchée à la maison : les données survivent même si tu détruis la maison. |
| **Port** | Une porte d'entrée. On mappe une porte de la maison vers une porte de ton Mac. |

### 1.3. La commande qu'on a lancée, ligne par ligne

```bash
docker run -d --name tml-pg \
  -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=tm_location \
  -p 5432:5432 \
  postgres:17-alpine
```

- `docker run` → construit et démarre un conteneur.
- `-d` → **detached**. Sans ça, ton terminal reste bloqué à afficher les logs. Avec `-d`, ça tourne en fond.
- `--name tml-pg` → nom lisible. Sinon Docker en génère un aléatoire (`funny_einstein`). Pratique pour cibler le conteneur ensuite.
- `-e VARIABLE=valeur` → injecte une variable d'environnement dans le conteneur. Ici, PG lit `POSTGRES_PASSWORD` au démarrage pour créer le user admin.
- `-p 5432:5432` → **port mapping**. Le PostgreSQL dans la boîte écoute sur son port 5432 interne, on l'expose sur le port 5432 de ton Mac. Format : `port_mac:port_conteneur`.
- `postgres:17-alpine` → l'image à utiliser. `17` = version PostgreSQL, `alpine` = variante Linux minimaliste (~80 MB au lieu de ~400 MB).

### 1.4. Les commandes du quotidien

| Commande | Ce que ça fait |
|---|---|
| `docker ps` | Liste les conteneurs **en cours d'exécution** |
| `docker ps -a` | Liste **tous** les conteneurs (même arrêtés) |
| `docker stop tml-pg` | Arrête le conteneur (les données restent) |
| `docker start tml-pg` | Redémarre un conteneur arrêté |
| `docker restart tml-pg` | Stop + start |
| `docker logs tml-pg` | Affiche ce que le conteneur a écrit (utile pour déboguer) |
| `docker logs -f tml-pg` | Idem mais en continu (comme `tail -f`) |
| `docker exec -it tml-pg <commande>` | Lance une commande **dedans** le conteneur (ex : ouvrir psql) |
| `docker rm tml-pg` | Supprime le conteneur (il doit être arrêté) |
| `docker images` | Liste les images téléchargées |

### 1.5. Point d'attention : les données

Actuellement notre conteneur **ne persiste pas les données**. Si tu fais `docker rm tml-pg`, tu perds tout. C'est OK pour du développement où on migre depuis SQLite. Plus tard, on ajoutera `-v` (volume) :
```bash
-v tml-pg-data:/var/lib/postgresql/data
```
→ les fichiers de la base sont stockés dans un volume Docker et survivent à la destruction du conteneur.

---

## 2. Pourquoi PostgreSQL plutôt que SQLite

### 2.1. SQLite en résumé
- Un **fichier unique** (`tm_location.db`).
- Aucun serveur, la lib Python parle directement au fichier.
- Un seul processus peut écrire à la fois (verrouillage global).
- Parfait pour du prototypage, une app mono-utilisateur, une extension navigateur.

### 2.2. PostgreSQL en résumé
- Un **serveur** qui tourne en permanence.
- L'app se connecte via TCP (port 5432).
- Plusieurs écritures **simultanées** possibles (MVCC — Multi-Version Concurrency Control).
- Types riches : `JSONB`, `TIMESTAMPTZ`, `ARRAY`, extensions comme **PostGIS** (cartes).

### 2.3. Pourquoi c'est important pour TM_Location
- **Mobile Money** : plusieurs clients peuvent réserver en même temps sans se bloquer.
- **Coolify/VPS** : le déploiement standard tourne avec un serveur DB séparé.
- **PostGIS futur** : quand on hébergera les tuiles OSM Madagascar, on stockera de la géométrie native.
- **Recherche floue** (`pg_trgm`) : trouver "Antanana" quand l'utilisateur tape "antananarivo".

---

## 3. UUID v7 — pourquoi remplacer les entiers

### 3.1. Le problème des IDs entiers

Aujourd'hui, tes URLs ressemblent à ça :
```
/voiture/1
/voiture/2
/reservation/15
```

Trois soucis :
1. **Énumération** : n'importe qui peut tester `/voiture/1`, `/2`, `/3`… et découvrir tout ton catalogue.
2. **Fuite d'information business** : `/reservation/47` révèle qu'il y a eu ~47 réservations. Un concurrent le voit.
3. **Fusion / offline** : si deux environnements créent chacun un `id = 5`, impossible de fusionner.

### 3.2. Les UUID (version 4)

Un UUID version 4 ressemble à ça :
```
f47ac10b-58cc-4372-a567-0e02b2c3d479
```
128 bits d'aléatoire pur. **Problème** : quand tu insères des UUID v4 dans une base, ils tombent partout au hasard dans l'index B-tree, ce qui fragmente l'index et ralentit les écritures à grande échelle.

### 3.3. UUID v7 — le compromis moderne (2024+)

Un UUID v7 encode le **timestamp** dans ses premiers bits :
```
018f5a3c-6a2e-7abc-8def-0123456789ab
└──────────────┘
   timestamp ms
```
Résultat :
- Toujours **imprévisible** (les bits de fin restent aléatoires).
- **Ordonnés dans le temps** → un UUID généré maintenant est "plus grand" qu'un UUID généré hier.
- Les insertions se font en fin d'index B-tree → **performance préservée**, comme avec un `INTEGER` auto-incrémenté.

### 3.4. Comment on les génère

Python 3.14 n'a pas encore `uuid.uuid7()` dans la stdlib. On utilise la lib **`uuid-utils`** (implémentée en Rust, très rapide) :

```python
# app/utils/ids.py
import uuid_utils

def new_uuid7() -> UUID:
    return UUID(str(uuid_utils.uuid7()))
```

Dans les modèles SQLModel, on l'utilise comme `default_factory` :
```python
id: UUID = Field(default_factory=new_uuid7, primary_key=True)
```

À chaque `INSERT`, Python génère un UUID v7 avant d'envoyer la requête. Aucun aller-retour DB nécessaire pour obtenir l'ID (contrairement à `AUTOINCREMENT`).

---

## 4. Ce qu'on a fait aujourd'hui (étape 1)

1. **Ajouté 3 dépendances** à `requirements.txt` :
   - `asyncpg` : driver async Python ↔ PostgreSQL.
   - `psycopg2-binary` : driver sync utilisé par Alembic (les migrations).
   - `uuid-utils` : génération d'UUID v7.
2. **Créé le helper** `app/utils/ids.py` avec la fonction `new_uuid7()`.
3. **Lancé PostgreSQL 17** dans un conteneur Docker nommé `tml-pg` sur le port 5432.

Rien n'a changé côté code applicatif. L'app tourne toujours sur SQLite comme avant.

---

## 5. Ce qui vient ensuite

- **Étape 2** : réécrire les 6 modèles SQLModel pour que `id` soit un `UUID` au lieu d'un `int`. Squash des 19 migrations Alembic en une seule migration initiale.
- **Étape 3** : script Python one-shot qui copie les données de `tm_location.db` (SQLite) vers PostgreSQL en générant des UUID v7 et en remappant les foreign keys.
- **Étape 4** : adapter les routes FastAPI pour accepter des UUID dans les path params.
- **Étape 5** : nettoyage (retirer `aiosqlite`, documenter `.env.example`).

Le plan complet est ici : `~/.claude/plans/reagrde-mon-app-silly-raccoon.md`.

---

## 6. Vocabulaire à retenir

- **Conteneur** : une instance en cours d'exécution d'une image Docker.
- **Image** : template figé qui contient un logiciel prêt à démarrer.
- **Volume** : stockage persistant Docker (survit à la suppression du conteneur).
- **Port mapping** (`-p host:container`) : redirection réseau du Mac vers le conteneur.
- **MVCC** : mécanisme PostgreSQL qui autorise lectures + écritures simultanées.
- **UUID v7** : identifiant 128 bits ordonné dans le temps, non-énumérable, bon pour les index.
- **Alembic** : outil de migration de schéma SQL pour SQLAlchemy/SQLModel.
- **Squash** : condenser plusieurs migrations en une seule.
