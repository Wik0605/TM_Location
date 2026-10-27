from typing import Optional, TYPE_CHECKING
import asyncio
import json
import pathlib
import httpx
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

NOMINATIM_LOCAL_URL = "http://localhost:8081"
PHOTON_URL = "https://photon.komoot.io/api/"
MG_BBOX = "43.2,-25.6,50.5,-11.9"
HTTP_TIMEOUT = 3.0

_SYNONYMES_PATH = pathlib.Path(__file__).parent / "synonymes.json"
_SYNONYMES: dict = json.loads(_SYNONYMES_PATH.read_text(encoding="utf-8"))


def _nominatim_to_photon(results: list) -> dict:
    features = []
    for r in results:
        try:
            lat = float(r["lat"])
            lon = float(r["lon"])
        except (KeyError, ValueError, TypeError):
            continue

        addr = r.get("address", {})
        name = (
            addr.get("amenity")
            or addr.get("shop")
            or addr.get("office")
            or addr.get("tourism")
            or addr.get("suburb")
            or addr.get("neighbourhood")
            or addr.get("quarter")
            or addr.get("village")
            or addr.get("town")
            or addr.get("city")
            or r.get("name")
            or r.get("display_name", "").split(",")[0]
        )
        props = {
            "name": name,
            "city": addr.get("city") or addr.get("town") or addr.get("village") or "",
            "district": addr.get("suburb") or addr.get("neighbourhood") or "",
            "state": addr.get("state") or addr.get("region") or "",
            "country": addr.get("country") or "",
            "osm_id": r.get("osm_id"),
            "osm_type": r.get("osm_type"),
            "type": r.get("type") or r.get("class") or "",
        }
        bbox = r.get("boundingbox")
        if bbox and len(bbox) == 4:
            south, north, west, east = (float(x) for x in bbox)
            props["extent"] = [west, north, east, south]

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": features}


async def search_photon(
    q: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    limit: int = 10,
    lang: str = "fr",
) -> Optional[dict]:
    params = {
        "q": q,
        "limit": limit,
        "lang": lang,
        "bbox": MG_BBOX,
    }
    if lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(PHOTON_URL, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data.get("features"):
                return None
            return data
    except httpx.HTTPError:
        return None


async def search_nominatim_local(
    q: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    limit: int = 10,
    lang: str = "fr",
) -> dict:
    params = {
        "q": q,
        "format": "json",
        "addressdetails": 1,
        "limit": limit,
        "accept-language": lang,
        "countrycodes": "mg",
    }
    if lat is not None and lon is not None:
        params["viewbox"] = f"{lon - 1},{lat + 1},{lon + 1},{lat - 1}"
        params["bounded"] = 0

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(
                f"{NOMINATIM_LOCAL_URL}/search",
                params=params,
                headers={"User-Agent": "TM_Location/1.0"},
            )
            if resp.status_code != 200:
                return {"type": "FeatureCollection", "features": []}
            return _nominatim_to_photon(resp.json())
    except httpx.HTTPError:
        return {"type": "FeatureCollection", "features": []}


def _search_synonymes(q: str, limit: int) -> list:
    key = q.strip().lower()
    features = []
    for syn, data in _SYNONYMES.items():
        if key in syn or syn.startswith(key):
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [data["lon"], data["lat"]]},
                "properties": {
                    "name": data["label"],
                    "city": data.get("city", ""),
                    "district": "",
                    "state": "Antananarivo",
                    "country": "Madagascar",
                    "osm_id": None,
                    "osm_type": None,
                    "type": "neighbourhood",
                },
            })
        if len(features) >= limit:
            break
    return features


async def search_quartiers_db(db: "AsyncSession", q: str, limit: int) -> list:
    sql = text("""
        SELECT
            nom,
            nom_court,
            type,
            ST_X(ST_Centroid(geom)) AS lon,
            ST_Y(ST_Centroid(geom)) AS lat
        FROM quartiers
        WHERE actif = true
          AND (nom ILIKE :search OR nom_court ILIKE :search)
        ORDER BY nom
        LIMIT :limit
    """)
    result = await db.execute(sql, {"search": f"%{q}%", "limit": limit})
    rows = result.mappings().all()
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
            "properties": {
                "name": row["nom"],
                "city": "Antananarivo",
                "district": row["nom_court"],
                "state": "Antananarivo",
                "country": "Madagascar",
                "osm_id": None,
                "osm_type": None,
                "type": row["type"],
            },
        })
    return features


async def search_places(
    q: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    limit: int = 10,
    lang: str = "fr",
    db: Optional["AsyncSession"] = None,
) -> dict:
    synonyme_features = _search_synonymes(q, limit)

    tasks = [
        search_photon(q=q, lat=lat, lon=lon, limit=limit, lang=lang),
        search_nominatim_local(q=q, lat=lat, lon=lon, limit=limit, lang=lang),
    ]
    if db is not None:
        tasks.append(search_quartiers_db(db=db, q=q, limit=limit))

    results = await asyncio.gather(*tasks)

    photon_features = (results[0] or {}).get("features", [])
    nominatim_features = results[1].get("features", [])
    quartiers_features = results[2] if db is not None else []

    seen = set()
    merged = []
    for f in quartiers_features + synonyme_features + photon_features + nominatim_features:
        osm_id = f.get("properties", {}).get("osm_id")
        key = osm_id if osm_id else id(f)
        if key not in seen:
            seen.add(key)
            merged.append(f)

    return {"type": "FeatureCollection", "features": merged[:limit]}
