from slugify import slugify as _slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

MAX_SLUG_LENGTH = 80


def slugify(text: str) -> str:
    return _slugify(text or "", max_length=MAX_SLUG_LENGTH) or "voiture"


async def unique_slug(db: AsyncSession, base_slug: str, model) -> str:
    slug = base_slug
    suffix = 2
    while True:
        stmt = select(model).where(model.slug == slug).limit(1)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1
