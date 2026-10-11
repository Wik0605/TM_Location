"""
Configuration de la base de données PostgreSQL (asyncpg).

DATABASE_URL doit être défini dans .env, au format :
    postgresql+asyncpg://user:password@host:port/dbname
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlmodel import SQLModel

from app.config import settings

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL manquant dans .env "
        "(ex: postgresql+asyncpg://postgres:dev@localhost:5432/tm_location)"
    )

DATABASE_URL = settings.database_url

# Création du moteur asynchrone
# echo=True affiche les requêtes SQL dans la console (utile pour le debug)
# future=True active le comportement SQLAlchemy 2.0
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# Factory pour créer des sessions de base de données
# Chaque session gère une transaction indépendante
# expire_on_commit=False permet d'accéder aux objets après commit
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """
    Classe de base pour tous les modèles SQLAlchemy

    Tous nos modèles hériteront de cette classe.
    Cela permet à SQLAlchemy de :
    - Détecter automatiquement les tables
    - Gérer les relations entre modèles
    - Créer les tables avec Base.metadata.create_all()
    """
    pass


async def init_db():
    """
    Initialise la base de données

    Crée toutes les tables définies dans les modèles.
    À appeler au démarrage de l'application.

    Utilisation :
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    """
    # Import des modeles SQLModel pour peupler SQLModel.metadata
    from app.models import voiture, reservation, user, analytics  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_db():
    """
    Dépendance FastAPI pour injecter une session DB

    Ce générateur crée une nouvelle session pour chaque requête
    et la ferme automatiquement à la fin.

    Utilisation dans une route :
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...

    Pourquoi utiliser un générateur ?
    - Garantit que la session est fermée même en cas d'erreur
    - Gestion automatique des transactions
    - Pattern recommandé par FastAPI
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commit automatique si tout va bien
        except Exception:
            await session.rollback()  # Rollback en cas d'erreur
            raise
        finally:
            await session.close()  # Toujours fermer la session