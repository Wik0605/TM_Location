from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, conlist

from app.client.analytics import service as analytics_service
from app.client.itineraire import service as routing_service
from app.client.itineraire.external import reverse_geocode_nominatim
from app.client.itineraire.service import RoutingError
from app.limiter import limiter


router = APIRouter(prefix="/api", tags=["itineraire-api"])


_REVERSE_GEOCODE_CACHE: dict[tuple[float, float], str] = {}
_REVERSE_GEOCODE_CACHE_MAX = 500
_FALLBACK_NAME = "Lieu sélectionné"


@router.get("/reverse-geocode")
@limiter.limit("60/minute")
async def reverse_geocode(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    key = (round(lat, 5), round(lon, 5))
    cached = _REVERSE_GEOCODE_CACHE.get(key)
    if cached is not None:
        return {"name": cached, "cached": True}

    name = await reverse_geocode_nominatim(lat, lon) or _FALLBACK_NAME

    if len(_REVERSE_GEOCODE_CACHE) >= _REVERSE_GEOCODE_CACHE_MAX:
        _REVERSE_GEOCODE_CACHE.clear()
    _REVERSE_GEOCODE_CACHE[key] = name

    return {"name": name, "cached": False}


class WaypointsPayload(BaseModel):
    waypoints: conlist(
        conlist(float, min_length=2, max_length=2),
        min_length=2,
        max_length=routing_service.MAX_WAYPOINTS,
    ) = Field(..., description="Liste de [lat, lon]")


@router.post("/voitures/{voiture_id}/itineraire/calculer")
@limiter.limit("30/minute")
async def calculer_itineraire(
    request: Request,
    voiture_id: int,
    payload: WaypointsPayload,
    response: Response,
    background: BackgroundTasks,
):
    if not routing_service.verifier_quota(request):
        raise HTTPException(status_code=429, detail="Quota journalier atteint.")

    waypoints = [(lat, lon) for lat, lon in payload.waypoints]

    try:
        result = await routing_service.calculer_itineraire(waypoints)
    except RoutingError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token = routing_service.emettre_token(
        distance_km=result["distance_km"],
        waypoints=waypoints,
        voiture_id=voiture_id,
        source=result["source"],
    )

    session_id = analytics_service.get_or_create_session_id(request, response)
    ctx = analytics_service.extraire_contexte(request)
    depart = waypoints[0]
    arrivee = waypoints[-1]
    background.add_task(
        analytics_service.enregistrer_devis,
        session_id,
        ctx["referer_host"],
        ctx["hour_local"],
        voiture_id,
        depart[0], depart[1],
        arrivee[0], arrivee[1],
        result["distance_km"],
    )

    return {
        "distance_km": round(result["distance_km"], 2),
        "polyline": result["polyline"],
        "source": result["source"],
        "token": token,
    }
