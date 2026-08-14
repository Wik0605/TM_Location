"""
Point d'entree de developpement local.

Charge .env.dev si present (bac a sable local), sinon .env par defaut.
En production, Railway fournit ses propres variables d'environnement.
"""

from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).parent
_DEV_ENV = _ROOT / ".env.dev"

if _DEV_ENV.exists():
    load_dotenv(_DEV_ENV, override=True)
    print(f"[dev] variables chargees depuis {_DEV_ENV.name}")

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
