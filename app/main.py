"""
Point d'entrée de l'application TM_Location.

Ce fichier configure :
- L'application FastAPI
- Le middleware CORS
- Les fichiers statiques
- Le démarrage / arrêt (lifespan)
- Les données initiales (seed)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path

from app.config import settings
from app.database import init_db, engine
from app.routers.web import router as web_router
from app.routers.admin_auth import router as admin_auth_router
from app.routers.admin_cars import router as admin_cars_router
from app.routers.admin_rentals import router as admin_rentals_router
from app.routers.auth import router as auth_router

STATIC_DIR = Path(__file__).parent.parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Cycle de vie de l'application.

    'async with' et 'yield' : tout ce qui est AVANT yield s'exécute au démarrage,
    tout ce qui est APRÈS yield s'exécute à l'arrêt.
    """
    print("Démarrage de TM_Location...")
    await init_db()
    await seed_initial_data()
    print("Application prête !")
    yield
    print("Arrêt de TM_Location...")
    await engine.dispose()


async def seed_initial_data():
    """
    Insère les données initiales si la DB est vide.
    Guard : on vérifie RentalType — s'il en existe déjà, on ne réinsère rien.
    """
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models import RentalType, Car, City, get_initial_rental_types, get_initial_cars, get_initial_cities

    async with AsyncSessionLocal() as session:
        # Insérer les villes si absentes
        existing_cities = await session.execute(select(City))
        if not existing_cities.scalars().first():
            print("Insertion des villes initiales...")
            for city_data in get_initial_cities():
                session.add(City(**city_data))
            await session.commit()

        # Si des RentalTypes existent déjà, les données sont déjà là
        existing_rental_types = await session.execute(select(RentalType))
        if existing_rental_types.scalars().first():
            return

        print("Insertion des types de location et voitures...")

        for rental_type_data in get_initial_rental_types():
            session.add(RentalType(**rental_type_data))
        await session.commit()

        for car_data in get_initial_cars():
            session.add(Car(**car_data))
        await session.commit()

        print("Données initiales insérées !")


app = FastAPI(
    title="TM_Location",
    description="Application de location de voitures à Madagascar.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


app.include_router(web_router)
app.include_router(admin_auth_router)
app.include_router(admin_cars_router)
app.include_router(admin_rentals_router)
app.include_router(auth_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
