import math
import uuid
import time
from typing import Optional, List, Tuple

import httpx


MADAGASCAR_LAT = (-25.7, -11.9)
MADAGASCAR_LON = (43.2, 50.5)
MAX_WAYPOINTS = 10
TOKEN_TTL_SECONDS = 15 * 60
HTTP_TIMEOUT = 5.0

_cache_tokens: dict[str, dict] = {}


class RoutingError(Exception):
    pass


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


async def _appeler_brouter(waypoints, client: httpx.AsyncClient) -> Optional[dict]:
    lonlats = "|".join(f"{lon},{lat}" for lat, lon in waypoints)
    url = "https://brouter.de/brouter"
    params = {
        "lonlats": lonlats,
        "profile": "car-eco",
        "alternativeidx": 0,
        "format": "geojson",
    }
    try:
        resp = await client.get(url, params=params, timeout=HTTP_TIMEOUT)
        if resp.status_code != 200:
            return None
        geojson = resp.json()
        feature = geojson.get("features", [None])[0]
        if not feature:
            return None
        track_length = feature["properties"].get("track-length")
        if track_length is None:
            return None
        return {
            "distance_km": float(track_length) / 1000,
            "polyline": geojson,
            "source": "brouter",
        }
    except (httpx.HTTPError, ValueError, KeyError):
        return None


async def _appeler_osrm(waypoints, client: httpx.AsyncClient) -> Optional[dict]:
    coords = ";".join(f"{lon},{lat}" for lat, lon in waypoints)
    url = f"https://router.project-osrm.org/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "geojson"}
    try:
        resp = await client.get(url, params=params, timeout=HTTP_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None
        route = data["routes"][0]
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": route["geometry"], "properties": {}}
            ],
        }
        return {
            "distance_km": route["distance"] / 1000,
            "polyline": geojson,
            "source": "osrm",
        }
    except (httpx.HTTPError, ValueError, KeyError):
        return None


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
        result = await _appeler_brouter(waypoints, client)
        if result:
            return result
        result = await _appeler_osrm(waypoints, client)
        if result:
            return result
    return _fallback_haversine(waypoints)


def _purger_tokens_expires() -> None:
    now = time.time()
    expired = [t for t, d in _cache_tokens.items() if d["expire_at"] < now]
    for t in expired:
        del _cache_tokens[t]


def emettre_token(distance_km: float, waypoints, voiture_id: int) -> str:
    _purger_tokens_expires()
    token = uuid.uuid4().hex
    _cache_tokens[token] = {
        "distance_km": distance_km,
        "waypoints": waypoints,
        "voiture_id": voiture_id,
        "expire_at": time.time() + TOKEN_TTL_SECONDS,
    }
    return token


def lire_token(token: str) -> Optional[dict]:
    data = _cache_tokens.get(token)
    if not data:
        return None
    if data["expire_at"] < time.time():
        del _cache_tokens[token]
        return None
    return data
