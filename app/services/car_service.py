from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.models import Voiture, TypeLocation


async def get_available_voitures(
    db: AsyncSession,
    limit: Optional[int] = None,
    order_by_marque: bool = False
) -> List[Voiture]:
    query = (
        select(Voiture)
        .where(Voiture.is_available == True)
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


async def get_voiture_by_id(db: AsyncSession, voiture_id: int) -> Optional[Voiture]:
    result = await db.execute(
        select(Voiture)
        .where(Voiture.id == voiture_id)
        .options(selectinload(Voiture.images), selectinload(Voiture.types_location))
    )
    return result.scalar_one_or_none()
