from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List

from app.models import RentalType, Rental


async def get_rental_types(db: AsyncSession) -> List[RentalType]:
    result = await db.execute(select(RentalType).order_by(RentalType.duration_days))
    return result.scalars().all()


async def has_conflict(db: AsyncSession, car_id: int, start: datetime, end: datetime) -> bool:
    result = await db.execute(
        select(Rental).where(
            and_(
                Rental.car_id == car_id,
                Rental.status != "annulée",
                Rental.start_date < end,
                Rental.end_date > start,
            )
        )
    )
    return result.scalar_one_or_none() is not None
