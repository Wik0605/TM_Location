import logging
import math
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple

import httpx
import jwt
from fastapi import Request

from app.client.itineraire.external import appeler_brouter, appeler_osrm
from app.config import settings

logger = logging.getLogger(__name__)


MADAGASCAR_LAT = (-25.7, -11.9)
MADAGASCAR_LON = (43.2, 50.5)
MAX_WAYPOINTS = 10
TOKEN_TTL_SECONDS = 15 * 60
QUOTA_ANON_PAR_JOUR = 7
JWT_ALGORITHM = "HS256"
MIN_DISTANCE_KM = 0.1


class RoutingError(Exception):
    pass


def verifier_quota(request: Request) -> bool:
    if request.session.get("user_id"):
        return True
    today = str(date.today())
    if request.session.get("itinerary_date") != today:
        request.session["itinerary_date"] = today
        request.session["itinerary_count"] = 0
    count = request.session.get("itinerary_count", 0)
    if count >= QUOTA_ANON_PAR_JOUR:
        return False
    request.session["itinerary_count"] = count + 1
    return True


def _haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    s = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(s), math.sqrt(1 - s))


def _valider_waypoints(waypoints: List[Tuple[float, float]]) -> None:
    if len(waypoints) < 2:
        raise RoutingError("Il faut au moins deux points.")
    if len(waypoints) > MAX_WAYPOINTS:
        raise RoutingError(f"Maximum {MAX_WAYPOINTS} points autorisés.")
    for lat, lon in waypoints:
        if not (MADAGASCAR_LAT[0] <= lat <= MADAGASCAR_LAT[1]):
            raise RoutingError("Latitude hors de Madagascar.")
        if not (MADAGASCAR_LON[0] <= lon <= MADAGASCAR_LON[1]):
            raise RoutingError("Longitude hors de Madagascar.")
    for i in range(len(waypoints) - 1):
        if _haversine_km(waypoints[i], waypoints[i + 1]) < MIN_DISTANCE_KM:
            raise RoutingError(
                f"Points consecutifs trop proches (min {int(MIN_DISTANCE_KM * 1000)} m)."
            )


def _fallback_haversine(waypoints) -> dict:
    total = 0.0
    for i in range(len(waypoints) - 1):
        total += _haversine_km(waypoints[i], waypoints[i + 1])
    coords = [[lon, lat] for lat, lon in waypoints]
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {},
            }
        ],
    }
    return {
        "distance_km": total * 1.3,
        "polyline": geojson,
        "source": "haversine",
    }


async def calculer_itineraire(waypoints: List[Tuple[float, float]]) -> dict:
    _valider_waypoints(waypoints)
    async with httpx.AsyncClient() as client:
        result = await appeler_brouter(waypoints, client)
        if result:
            logger.info("itineraire_calcul source=brouter points=%d distance_km=%.2f",
                        len(waypoints), result["distance_km"])
            return result
        result = await appeler_osrm(waypoints, client)
        if result:
            logger.warning("itineraire_calcul source=osrm points=%d distance_km=%.2f fallback_from=brouter",
                           len(waypoints), result["distance_km"])
            return result
    result = _fallback_haversine(waypoints)
    logger.error("itineraire_calcul source=haversine points=%d distance_km=%.2f fallback_from=osrm",
                 len(waypoints), result["distance_km"])
    return result


def emettre_token(distance_km: float, waypoints, voiture_id: int, source: str) -> str:
    payload = {
        "distance_km": distance_km,
        "waypoints": [[lat, lon] for lat, lon in waypoints],
        "voiture_id": voiture_id,
        "source": source,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def lire_token(token: str) -> Optional[dict]:
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    data["waypoints"] = [tuple(pt) for pt in data["waypoints"]]
    return data
