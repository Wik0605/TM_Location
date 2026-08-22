"""Service analytics maison — écriture non bloquante d'événements."""

from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import AnalyticsEvent, Location


SESSION_COOKIE = "tm_sid"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 jours
TZ_ANTANANARIVO = ZoneInfo("Indian/Antananarivo")


def get_or_create_session_id(request: Request, response: Response) -> str:
    """Retourne le session_id du cookie, en pose un neuf sinon."""
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        sid = str(uuid4())
        response.set_cookie(
            SESSION_COOKIE,
            sid,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
    return sid


def _referer_host(request: Request) -> str:
    ref = request.headers.get("referer") or ""
    if not ref:
        return "direct"
    try:
        host = urlparse(ref).hostname or "direct"
    except Exception:
        return "direct"
    if host in {"localhost", "127.0.0.1"}:
        return "direct"
    self_host = request.url.hostname
    if self_host and host == self_host:
        return "direct"
    return host[:120]


def _hour_local() -> int:
    return datetime.now(TZ_ANTANANARIVO).hour


def _parse_waypoints(text: str | None) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
    if not text:
        return None, None
    pts = []
    for p in text.split(";"):
        try:
            lat_s, lon_s = p.split(",")
            pts.append((float(lat_s), float(lon_s)))
        except ValueError:
            continue
    if len(pts) < 2:
        return None, None
    return pts[0], pts[-1]


async def _write(event: AnalyticsEvent) -> None:
    """Écrit un événement dans sa propre session (background-safe)."""
    async with AsyncSessionLocal() as db:
        db.add(event)
        await db.commit()


async def enregistrer_devis(
    session_id: str | None,
    referer_host: str,
    hour_local: int,
    voiture_id: int,
    depart_lat: float,
    depart_lon: float,
    arrivee_lat: float,
    arrivee_lon: float,
    distance_km: float,
) -> None:
    await _write(AnalyticsEvent(
        event_type="devis_created",
        session_id=session_id,
        voiture_id=voiture_id,
        depart_lat=depart_lat,
        depart_lon=depart_lon,
        arrivee_lat=arrivee_lat,
        arrivee_lon=arrivee_lon,
        distance_km=distance_km,
        referer_host=referer_host,
        hour_local=hour_local,
    ))


async def enregistrer_reservation(
    session_id: str | None,
    referer_host: str,
    hour_local: int,
    location: Location,
) -> None:
    depart, arrivee = _parse_waypoints(location.itineraire_etapes)
    await _write(AnalyticsEvent(
        event_type="reservation_created",
        session_id=session_id,
        location_id=location.id,
        voiture_id=location.voiture_id,
        type_location_id=location.type_location_id,
        prix=float(location.prix_total) if location.prix_total else None,
        depart_lat=depart[0] if depart else None,
        depart_lon=depart[1] if depart else None,
        arrivee_lat=arrivee[0] if arrivee else None,
        arrivee_lon=arrivee[1] if arrivee else None,
        depart_nom=location.itineraire_depart,
        arrivee_nom=location.itineraire_arrivee,
        distance_km=location.itineraire_distance_km,
        referer_host=referer_host,
        hour_local=hour_local,
    ))


async def enregistrer_event_client(
    event_type: str,
    session_id: str | None,
    referer_host: str,
    hour_local: int,
) -> None:
    await _write(AnalyticsEvent(
        event_type=event_type,
        session_id=session_id,
        referer_host=referer_host,
        hour_local=hour_local,
    ))


def extraire_contexte(request: Request) -> dict:
    """Extrait le contexte (sans muter la réponse — cookie posé ailleurs)."""
    return {
        "session_id": request.cookies.get(SESSION_COOKIE),
        "referer_host": _referer_host(request),
        "hour_local": _hour_local(),
    }
