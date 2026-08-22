from fastapi import APIRouter, BackgroundTasks, Request, Response, HTTPException
from pydantic import BaseModel, Field, conlist

from app.services import analytics_service, routing_service
from app.services.routing_service import RoutingError


router = APIRouter(prefix="/api", tags=["itineraire-api"])


class WaypointsPayload(BaseModel):
    waypoints: conlist(
        conlist(float, min_length=2, max_length=2),
        min_length=2,
        max_length=routing_service.MAX_WAYPOINTS,
    ) = Field(..., description="Liste de [lat, lon]")


@router.post("/voitures/{voiture_id}/itineraire/calculer")
async def calculer_itineraire(
    voiture_id: int,
    payload: WaypointsPayload,
    request: Request,
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
