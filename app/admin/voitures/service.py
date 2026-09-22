from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.voiture import TypeLocation, Voiture, VoitureImage


async def get_all_voitures(db: AsyncSession) -> list[Voiture]:
    result = await db.execute(
        select(Voiture)
        .options(selectinload(Voiture.images), selectinload(Voiture.types_location))
        .order_by(Voiture.nom)
    )
    return result.scalars().all()


async def get_voiture_by_id(db: AsyncSession, voiture_id: int) -> Voiture | None:
    result = await db.execute(
        select(Voiture)
        .where(Voiture.id == voiture_id)
        .options(selectinload(Voiture.images), selectinload(Voiture.types_location))
    )
    return result.scalar_one_or_none()


async def create_voiture(db: AsyncSession, data: dict) -> Voiture:
    voiture = Voiture(**data)
    db.add(voiture)
    await db.commit()
    await db.refresh(voiture)
    return voiture


async def update_voiture(db: AsyncSession, voiture_id: int, data: dict) -> Voiture | None:
    voiture = await get_voiture_by_id(db, voiture_id)
    if not voiture:
        return None
    for key, value in data.items():
        if hasattr(voiture, key) and value is not None:
            setattr(voiture, key, value)
    await db.commit()
    await db.refresh(voiture)
    return voiture


async def delete_voiture(db: AsyncSession, voiture_id: int) -> bool:
    result = await db.execute(select(Voiture).where(Voiture.id == voiture_id))
    voiture = result.scalar_one_or_none()
    if not voiture:
        return False
    await db.delete(voiture)
    await db.commit()
    return True


async def add_voiture_image(db: AsyncSession, voiture_id: int, url: str) -> VoitureImage:
    result = await db.execute(
        select(func.max(VoitureImage.position)).where(VoitureImage.voiture_id == voiture_id)
    )
    max_pos = result.scalar() or -1
    image = VoitureImage(voiture_id=voiture_id, url=url, position=max_pos + 1)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def delete_voiture_image(db: AsyncSession, image_id: int) -> bool:
    result = await db.execute(select(VoitureImage).where(VoitureImage.id == image_id))
    image = result.scalar_one_or_none()
    if not image:
        return False
    await db.delete(image)
    await db.commit()
    return True


async def add_type_location(
    db: AsyncSession, voiture_id: int, nom: str, prix: int
) -> TypeLocation:
    tl = TypeLocation(voiture_id=voiture_id, nom=nom, prix=prix)
    db.add(tl)
    await db.commit()
    await db.refresh(tl)
    return tl


async def delete_type_location(db: AsyncSession, type_id: int) -> bool:
    result = await db.execute(sql_delete(TypeLocation).where(TypeLocation.id == type_id))
    await db.commit()
    return result.rowcount > 0
