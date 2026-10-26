# Migration SQLite → PostgreSQL + PostGIS : Le Voyage Complet

---

## Chapitre 1 — Pourquoi quitter SQLite ?

Imagine SQLite comme un **carnet de notes** sur ton bureau. C'est pratique pour toi seul, mais si 10 personnes essaient d'écrire dedans en même temps, ça devient le chaos.

PostgreSQL, c'est comme passer à un **vrai bureau avec des classeurs, des tiroirs, et une secrétaire** qui gère les accès simultanés.

**Concrètement pour TM_Location :**

| SQLite | PostgreSQL |
|--------|-----------|
| 1 fichier `.db` local | Serveur dédié |
| 1 utilisateur à la fois | 100+ connexions simultanées |
| Pas de géographie | PostGIS = cartes et polygones |
| Pas de production | Prêt pour Coolify/VPS |

---

## Chapitre 2 — C'est quoi Alembic ?

Avant la migration, tu modifiais ta base "à la main". Le problème : si tu déploies sur un serveur, comment ce serveur sait quelles tables créer ?

**Alembic, c'est git pour ta base de données.**

Chaque modification de ta base (créer une table, ajouter une colonne) devient un fichier versionné. Sur n'importe quel serveur vierge, tu tapes :

```bash
alembic upgrade head
```

Et toutes les modifications s'appliquent dans l'ordre, automatiquement.

**La chaîne de migrations de TM_Location :**

```
c3d4e5f6a7b8  →  Active PostGIS + uuid-ossp
      ↓
aef67dfd953f  →  Crée users, voitures, locations, analytics...
      ↓
b1c2d3e4f5a6  →  Crée la table quartiers avec géométrie
```

---

## Chapitre 3 — C'est quoi PostGIS ?

PostgreSQL seul ne comprend pas ce qu'est un polygone ou une coordonnée GPS. Il stocke des nombres, du texte, des dates — mais pas de géographie.

**PostGIS est un plugin qui ajoute une nouvelle langue à PostgreSQL : la langue des cartes.**

Grâce à PostGIS, ta base peut répondre à des questions comme :
- *"Quels fokontany sont dans cette zone de la carte ?"*
- *"Quelle est la distance entre Itaosy et Ivandry ?"*
- *"Le client est-il à l'intérieur du quartier Analakely ?"*

C'est pour ça que ta table `quartiers` a une colonne spéciale `geom` de type `MULTIPOLYGON` — ce n'est pas du texte ni un nombre, c'est une **forme géographique** que PostgreSQL comprend grâce à PostGIS.

---

## Chapitre 4 — C'est quoi SQLModel ?

Avant la migration, tu décrivais tes tables en deux endroits séparés :
- Une fois pour **SQLAlchemy** (la base de données)
- Une fois pour **Pydantic** (la validation des données dans FastAPI)

C'était de la duplication. SQLModel fusionne les deux en un seul endroit.

**Exemple concret avec `Voiture` :**

```python
# Avant (deux fichiers séparés)

# schemas.py
class VoitureCreate(BaseModel):
    nom: str
    places: int

# models.py
class Voiture(Base):
    __tablename__ = "voitures"
    nom = Column(String)
    places = Column(Integer)

# Après SQLModel (un seul fichier)
class Voiture(SQLModel, table=True):
    __tablename__ = "voitures"
    id: UUID = Field(default_factory=new_uuid7, primary_key=True)
    nom: str = Field(max_length=100)
    places: int = Field(default=5)
```

Une seule classe fait les deux jobs.

---

## Chapitre 5 — C'est quoi UUID v7 ?

En SQLite, tes enregistrements avaient des IDs simples : 1, 2, 3, 4...

Le problème en production :
- Si deux serveurs créent un enregistrement en même temps, ils peuvent tous les deux créer le numéro "42" → conflit
- Les IDs séquentiels révèlent des informations (le client voit que sa réservation est la n°3 → il sait que tu as peu de clients)

**UUID v7 génère un identifiant unique mondial** basé sur l'heure + aléatoire :

```
018c2d4e-f001-7a3b-9d2e-4f6a8b0c1d2e
```

- Impossible à deviner
- Unique même si 1000 serveurs créent des enregistrements simultanément
- Trié dans l'ordre chronologique (le "v7" = timestamp intégré)

---

## Chapitre 6 — Ce qu'on a corrigé

Quand on a testé `alembic upgrade head` sur une base vierge, trois bugs sont apparus :

**Bug 1 : PostGIS non activé**
La table `quartiers` utilisait un type géographique (`MULTIPOLYGON`) mais PostGIS n'était jamais activé. On a créé une migration dédiée qui l'active en premier.

**Bug 2 : Table `quartiers` jamais créée par Alembic**
Elle existait sur ta machine parce que tu l'avais créée manuellement via un script d'import. Alembic essayait de modifier une table qui n'existait pas encore. On a remplacé le `ALTER TABLE` par un `CREATE TABLE` complet.

**Bug 3 : Alembic ignorait `quartier.py`**
Le fichier `env.py` listait tous les modèles à surveiller, mais `quartier.py` manquait. Alembic était "aveugle" aux modifications de cette table.

---

## Résultat final

Sur n'importe quel serveur vierge aujourd'hui, une seule commande suffit :

```bash
alembic upgrade head
```

Et tu obtiens une base PostgreSQL complète avec :
- PostGIS activé
- Toutes les tables (users, voitures, locations, analytics, quartiers)
- Les bons types UUID v7
- La colonne géographique `geom` prête à recevoir les fokontany

C'est exactement ce dont tu as besoin pour déployer sur Coolify.
