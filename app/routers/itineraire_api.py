from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field, conlist

from app.services import routing_service
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

    return {
        "distance_km": round(result["distance_km"], 2),
        "polyline": result["polyline"],
        "source": result["source"],
        "token": token,
    }
