from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sql_delete
from sqlalchemy.orm import selectinload
from typing import Optional

from app.models import Car, CarImage, Rental, RentalType


async def get_all_rentals(db: AsyncSession) -> list[Rental]:
    result = await db.execute(
        select(Rental)
        .options(selectinload(Rental.car), selectinload(Rental.rental_type))
        .order_by(Rental.created_at.desc())
    )
    return result.scalars().all()


async def create_car(db: AsyncSession, data: dict) -> Car:
    car = Car(**data)
    db.add(car)
    await db.commit()
    await db.refresh(car)
    return car


async def delete_car(db: AsyncSession, car_id: int) -> bool:
    result = await db.execute(select(Car).where(Car.id == car_id))
    car = result.scalar_one_or_none()
    if not car:
        return False
    await db.delete(car)
    await db.commit()
    return True


async def get_all_cars(db: AsyncSession) -> list[Car]:
    result = await db.execute(
        select(Car)
        .options(selectinload(Car.images))
        .order_by(Car.brand)
    )
    return result.scalars().all()


async def get_car_by_id(db: AsyncSession, car_id: int) -> Optional[Car]:
    result = await db.execute(
        select(Car).where(Car.id == car_id).options(selectinload(Car.images))
    )
    return result.scalar_one_or_none()


async def update_car(db: AsyncSession, car_id: int, data: dict) -> Optional[Car]:
    car = await get_car_by_id(db, car_id)
    if not car:
        return None
    for key, value in data.items():
        if hasattr(car, key) and value is not None:
            setattr(car, key, value)
    await db.commit()
    await db.refresh(car)
    return car


async def add_car_image(db: AsyncSession, car_id: int, url: str) -> CarImage:
    result = await db.execute(
        select(func.max(CarImage.position)).where(CarImage.car_id == car_id)
    )
    max_pos = result.scalar() or -1
    image = CarImage(car_id=car_id, url=url, position=max_pos + 1)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def delete_car_image(db: AsyncSession, image_id: int) -> bool:
    result = await db.execute(select(CarImage).where(CarImage.id == image_id))
    image = result.scalar_one_or_none()
    if not image:
        return False
    await db.delete(image)
    await db.commit()
    return True


async def get_all_rental_types(db: AsyncSession) -> list[RentalType]:
    result = await db.execute(select(RentalType).order_by(RentalType.duration_days))
    return result.scalars().all()


async def create_rental_type(db: AsyncSession, data: dict) -> RentalType:
    rental_type = RentalType(**data)
    db.add(rental_type)
    await db.commit()
    await db.refresh(rental_type)
    return rental_type


async def update_rental_type(db: AsyncSession, rental_type_id: int, data: dict) -> Optional[RentalType]:
    result = await db.execute(select(RentalType).where(RentalType.id == rental_type_id))
    rental_type = result.scalar_one_or_none()
    if not rental_type:
        return None
    nullable_fields = {"prix_fixe", "fuel_consumption"}
    for key, value in data.items():
        if hasattr(rental_type, key) and (value is not None or key in nullable_fields):
            setattr(rental_type, key, value)
    await db.commit()
    await db.refresh(rental_type)
    return rental_type


async def delete_rental_type(db: AsyncSession, rental_type_id: int) -> bool:
    result = await db.execute(
        sql_delete(RentalType).where(RentalType.id == rental_type_id)
    )
    await db.commit()
    return result.rowcount > 0


async def get_dashboard_stats(db: AsyncSession) -> dict:
    total_rentals = (await db.execute(select(func.count(Rental.id)))).scalar() or 0
    total_cars = (await db.execute(select(func.count(Car.id)))).scalar() or 0
    available_cars = (await db.execute(
        select(func.count(Car.id)).where(Car.is_available == True)
    )).scalar() or 0
    total_revenue = (await db.execute(
        select(func.sum(Rental.total_price)).where(Rental.status != "annulée")
    )).scalar() or 0
    return {
        "total_rentals": total_rentals,
        "total_cars": total_cars,
        "available_cars": available_cars,
        "total_revenue": total_revenue,
    }


async def update_rental_status(db: AsyncSession, rental_id: int, status: str) -> Optional[Rental]:
    result = await db.execute(
        select(Rental).where(Rental.id == rental_id)
        .options(selectinload(Rental.car), selectinload(Rental.rental_type))
    )
    rental = result.scalar_one_or_none()
    if not rental:
        return None
    rental.status = status
    await db.commit()
    await db.refresh(rental)
    return rental
