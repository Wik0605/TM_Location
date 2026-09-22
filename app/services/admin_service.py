from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Location, Voiture


async def get_all_locations(db: AsyncSession) -> list[Location]:
    result = await db.execute(
        select(Location)
        .options(selectinload(Location.voiture), selectinload(Location.type_location))
        .order_by(Location.created_at.desc())
    )
    return result.scalars().all()


async def update_location_statut(
    db: AsyncSession, location_id: int, statut: str
) -> Location | None:
    result = await db.execute(
        select(Location)
        .where(Location.id == location_id)
        .options(selectinload(Location.voiture), selectinload(Location.type_location))
    )
    loc = result.scalar_one_or_none()
    if not loc:
        return None
    loc.statut = statut
    await db.commit()
    await db.refresh(loc)
    return loc


async def delete_location(db: AsyncSession, location_id: int) -> bool:
    result = await db.execute(select(Location).where(Location.id == location_id))
    loc = result.scalar_one_or_none()
    if not loc:
        return False
    await db.delete(loc)
    await db.commit()
    return True


async def get_dashboard_stats(db: AsyncSession) -> dict:
    total_locations = (await db.execute(select(func.count(Location.id)))).scalar() or 0
    total_voitures = (await db.execute(select(func.count(Voiture.id)))).scalar() or 0
    available_voitures = (await db.execute(
        select(func.count(Voiture.id)).where(Voiture.is_available == True)  # noqa: E712
    )).scalar() or 0
    total_revenue = (await db.execute(
        select(func.sum(Location.prix_total)).where(Location.statut != "annulée")
    )).scalar() or 0
    return {
        "total_rentals": total_locations,
        "total_cars": total_voitures,
        "available_cars": available_voitures,
        "total_revenue": total_revenue,
    }
