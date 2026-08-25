import httpx
from fastapi import APIRouter, BackgroundTasks, Request, Response, HTTPException, Query
from pydantic import BaseModel, Field, conlist

from app.limiter import limiter
from app.services import analytics_service, routing_service
from app.services.routing_service import RoutingError


router = APIRouter(prefix="/api", tags=["itineraire-api"])

_REVERSE_GEOCODE_CACHE: dict[tuple[float, float], str] = {}
_REVERSE_GEOCODE_CACHE_MAX = 500
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
_NOMINATIM_UA = "TM_Location/1.0 (contact: rakotomalalatafita2007@gmail.com)"
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

    name = _FALLBACK_NAME
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                _NOMINATIM_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "format": "json",
                    "accept-language": "fr",
                    "zoom": 16,
                },
                headers={"User-Agent": _NOMINATIM_UA},
            )
            if resp.status_code == 200:
                data = resp.json()
                display = data.get("display_name")
                if display:
                    name = ", ".join(display.split(",")[:2]).strip()
    except (httpx.HTTPError, ValueError, KeyError):
        pass

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
