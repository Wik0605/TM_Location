"""
Point d'entrée de l'application TM_Location.

Ce fichier configure :
- L'application FastAPI
- Le middleware CORS
- Les fichiers statiques
- Le démarrage / arrêt (lifespan)
- Les données initiales (seed)
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response
from pathlib import Path

from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db, engine
from app.limiter import limiter
from app.routers.web import router as web_router
from app.routers.admin_auth import router as admin_auth_router, login_rate_limit_handler
from app.routers.admin_cars import router as admin_cars_router
from app.routers.admin_rentals import router as admin_rentals_router
from app.routers.auth import router as auth_router
from app.routers.itineraire_api import router as itineraire_api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent.parent / "static"

STATIC_CACHE_MAX_AGE = 60 * 60 * 24 * 7  # 7 jours


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(self), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, Response) and response.status_code == 200:
            response.headers["Cache-Control"] = (
                f"public, max-age={STATIC_CACHE_MAX_AGE}"
            )
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Cycle de vie de l'application.

    'async with' et 'yield' : tout ce qui est AVANT yield s'exécute au démarrage,
    tout ce qui est APRÈS yield s'exécute à l'arrêt.
    """
    logger.info("Démarrage de TM_Location...")
    await init_db()
    await seed_initial_data()
    logger.info("Application prête !")
    yield
    logger.info("Arrêt de TM_Location...")
    await engine.dispose()


async def seed_initial_data():
    """Insère les villes initiales si la DB est vide."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models import City, get_initial_cities

    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(City))
        if not existing.scalars().first():
            logger.info("Insertion des villes initiales...")
            for city_data in get_initial_cities():
                session.add(City(**city_data))
            await session.commit()
            logger.info("Villes insérées !")


app = FastAPI(
    title="TM_Location",
    description="Application de location de voitures à Madagascar.",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, login_rate_limit_handler)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# NOTE : les protections de sécurité renforcées (cookies HTTPS uniquement,
# CORS restreint) s'activent uniquement en production. En développement local,
# on garde des règles permissives pour que localhost fonctionne sans HTTPS.
# Pour passer en mode production : mettre ENVIRONMENT=production dans .env
# et lister les domaines autorisés dans ALLOWED_ORIGINS.

if settings.is_production:
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        https_only=True,
        same_site="lax",
        max_age=3600,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        same_site="lax",
        max_age=3600,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

if STATIC_DIR.exists():
    app.mount("/static", CachedStaticFiles(directory=str(STATIC_DIR)), name="static")


app.include_router(web_router)
app.include_router(admin_auth_router)
app.include_router(admin_cars_router)
app.include_router(admin_rentals_router)
app.include_router(auth_router)
app.include_router(itineraire_api_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
