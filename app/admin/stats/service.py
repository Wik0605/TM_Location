from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsEvent
from app.models.voiture import TypeLocation


def _since(days: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days)


async def _count(db: AsyncSession, event_type: str, days: int | None = None) -> int:
    q = select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.event_type == event_type)
    if days is not None:
        q = q.where(AnalyticsEvent.created_at >= _since(days))
    return (await db.execute(q)).scalar() or 0


async def get_overview(db: AsyncSession) -> dict:
    devis_7 = await _count(db, "devis_created", 7)
    devis_30 = await _count(db, "devis_created", 30)
    resa_7 = await _count(db, "reservation_created", 7)
    resa_30 = await _count(db, "reservation_created", 30)
    installs = await _count(db, "pwa_installed")
    standalone_7 = await _count(db, "pwa_standalone_session", 7)
    standalone_30 = await _count(db, "pwa_standalone_session", 30)

    conv_7 = (resa_7 / devis_7 * 100) if devis_7 else 0.0
    conv_30 = (resa_30 / devis_30 * 100) if devis_30 else 0.0

    return {
        "installs": installs,
        "standalone_7": standalone_7,
        "standalone_30": standalone_30,
        "devis_7": devis_7,
        "devis_30": devis_30,
        "reservations_7": resa_7,
        "reservations_30": resa_30,
        "conversion_7": round(conv_7, 1),
        "conversion_30": round(conv_30, 1),
    }


async def get_daily_series(db: AsyncSession, days: int = 30) -> list[dict]:
    since = _since(days)
    day = func.date(AnalyticsEvent.created_at)
    q = (
        select(
            day.label("d"),
            func.sum(case((AnalyticsEvent.event_type == "devis_created", 1), else_=0)).label("devis"),
            func.sum(case((AnalyticsEvent.event_type == "reservation_created", 1), else_=0)).label("resa"),
        )
        .where(AnalyticsEvent.created_at >= since)
        .where(AnalyticsEvent.event_type.in_(["devis_created", "reservation_created"]))
        .group_by(day)
        .order_by(day)
    )
    rows = (await db.execute(q)).all()
    return [{"date": r.d, "devis": int(r.devis or 0), "reservations": int(r.resa or 0)} for r in rows]


async def get_top_zones(db: AsyncSession, direction: str, limit: int = 10) -> list[dict]:
    col = AnalyticsEvent.depart_nom if direction == "depart" else AnalyticsEvent.arrivee_nom
    q = (
        select(col.label("nom"), func.count(AnalyticsEvent.id).label("n"))
        .where(col.isnot(None))
        .group_by(col)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(limit)
    )
    rows = (await db.execute(q)).all()
    return [{"nom": r.nom, "count": int(r.n)} for r in rows]


async def get_hour_distribution(db: AsyncSession) -> list[dict]:
    q = (
        select(AnalyticsEvent.hour_local, func.count(AnalyticsEvent.id))
        .where(AnalyticsEvent.event_type.in_(["devis_created", "reservation_created"]))
        .where(AnalyticsEvent.hour_local.isnot(None))
        .group_by(AnalyticsEvent.hour_local)
        .order_by(AnalyticsEvent.hour_local)
    )
    rows = (await db.execute(q)).all()
    counts = {int(h): int(n) for h, n in rows}
    return [{"hour": h, "count": counts.get(h, 0)} for h in range(24)]


async def get_top_referers(db: AsyncSession, limit: int = 8) -> list[dict]:
    q = (
        select(AnalyticsEvent.referer_host, func.count(AnalyticsEvent.id))
        .where(AnalyticsEvent.referer_host.isnot(None))
        .group_by(AnalyticsEvent.referer_host)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(limit)
    )
    rows = (await db.execute(q)).all()
    return [{"host": r[0], "count": int(r[1])} for r in rows]


async def get_types_location_breakdown(db: AsyncSession) -> list[dict]:
    q = (
        select(TypeLocation.nom, func.count(AnalyticsEvent.id), func.sum(AnalyticsEvent.prix))
        .join(TypeLocation, TypeLocation.id == AnalyticsEvent.type_location_id)
        .where(AnalyticsEvent.event_type == "reservation_created")
        .group_by(TypeLocation.nom)
        .order_by(func.count(AnalyticsEvent.id).desc())
    )
    rows = (await db.execute(q)).all()
    return [
        {"nom": r[0], "count": int(r[1]), "revenu": float(r[2] or 0)}
        for r in rows
    ]


async def get_recent_trajets(db: AsyncSession, limit: int = 200) -> list[dict]:
    q = (
        select(
            AnalyticsEvent.depart_lat, AnalyticsEvent.depart_lon,
            AnalyticsEvent.arrivee_lat, AnalyticsEvent.arrivee_lon,
            AnalyticsEvent.event_type,
        )
        .where(AnalyticsEvent.depart_lat.isnot(None))
        .where(AnalyticsEvent.arrivee_lat.isnot(None))
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(q)).all()
    return [
        {
            "d": [r[0], r[1]],
            "a": [r[2], r[3]],
            "t": "resa" if r[4] == "reservation_created" else "devis",
        }
        for r in rows
    ]
