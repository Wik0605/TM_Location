from typing import Optional

import httpx

HTTP_TIMEOUT = 5.0

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_UA = "TM_Location/1.0 (contact: rakotomalalatafita2007@gmail.com)"


async def appeler_brouter(waypoints, client: httpx.AsyncClient) -> Optional[dict]:
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


async def appeler_osrm(waypoints, client: httpx.AsyncClient) -> Optional[dict]:
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


async def reverse_geocode_nominatim(lat: float, lon: float) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "format": "json",
                    "accept-language": "fr",
                    "zoom": 16,
                },
                headers={"User-Agent": NOMINATIM_UA},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            display = data.get("display_name")
            if display:
                return ", ".join(display.split(",")[:2]).strip()
    except (httpx.HTTPError, ValueError, KeyError):
        return None
    return None
