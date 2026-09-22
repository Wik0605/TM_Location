from datetime import date, datetime, time
from typing import List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reservation import Location
from app.models.voiture import Voiture


async def get_available_voitures(
    db: AsyncSession,
    limit: Optional[int] = None,
    order_by_marque: bool = False,
) -> List[Voiture]:
    query = (
        select(Voiture)
        .where(Voiture.is_available == True)  # noqa: E712
        .options(selectinload(Voiture.images), selectinload(Voiture.types_location))
    )
    if order_by_marque:
        query = query.order_by(Voiture.nom)
    else:
        query = query.order_by(Voiture.created_at.desc())
    if limit is not None:
        query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def _ids_voitures_reservees(
    db: AsyncSession, debut: datetime, fin: datetime
) -> set[int]:
    stmt = select(Location.voiture_id).where(
        and_(
            Location.statut != "annulée",
            Location.date_debut <= fin,
            Location.date_fin >= debut,
        )
    )
    result = await db.execute(stmt)
    return {row for row in result.scalars().all()}


async def get_voitures_avec_disponibilite(
    db: AsyncSession,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    limit: Optional[int] = None,
    order_by_marque: bool = False,
) -> List[Tuple[Voiture, bool]]:
    voitures = await get_available_voitures(
        db, limit=limit, order_by_marque=order_by_marque
    )
    if not date_debut:
        return [(v, True) for v in voitures]
    fin = date_fin or date_debut
    debut_dt = datetime.combine(date_debut, time.min)
    fin_dt = datetime.combine(fin, time.max)
    reserves = await _ids_voitures_reservees(db, debut_dt, fin_dt)
    return [(v, v.id not in reserves) for v in voitures]


async def voiture_est_disponible(
    db: AsyncSession,
    voiture_id: int,
    date_debut: date,
    date_fin: Optional[date] = None,
) -> bool:
    fin = date_fin or date_debut
    debut_dt = datetime.combine(date_debut, time.min)
    fin_dt = datetime.combine(fin, time.max)
    reserves = await _ids_voitures_reservees(db, debut_dt, fin_dt)
    return voiture_id not in reserves


async def get_voiture_by_id(db: AsyncSession, voiture_id: int) -> Optional[Voiture]:
    result = await db.execute(
        select(Voiture)
        .where(Voiture.id == voiture_id)
        .options(selectinload(Voiture.images), selectinload(Voiture.types_location))
    )
    return result.scalar_one_or_none()


async def get_voiture_by_slug(db: AsyncSession, slug: str) -> Optional[Voiture]:
    result = await db.execute(
        select(Voiture)
        .where(Voiture.slug == slug)
        .options(selectinload(Voiture.images), selectinload(Voiture.types_location))
    )
    return result.scalar_one_or_none()


async def resoudre_voiture(db: AsyncSession, key: str):
    """Retourne (voiture, par_id) — True si la cle etait un id numerique."""
    if key.isdigit():
        voiture = await get_voiture_by_id(db, int(key))
        return voiture, True
    voiture = await get_voiture_by_slug(db, key)
    return voiture, False
