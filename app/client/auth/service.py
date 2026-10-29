from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User


async def upsert_oauth_user(
    *,
    provider: str,
    provider_id: str,
    email: str,
    name: Optional[str],
    picture: Optional[str],
) -> User:
    """Recherche ou cree un User a partir des infos d un provider OAuth."""
    id_field = "google_id" if provider == "google" else "facebook_id"

    async with AsyncSessionLocal() as session:  # type: AsyncSession
        result = await session.execute(
            select(User).where(getattr(User, id_field) == provider_id)
        )
        user = result.scalars().first()

        if not user:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalars().first()
            if user:
                setattr(user, id_field, provider_id)
            else:
                user = User(
                    email=email,
                    name=name or email.split("@")[0],
                    picture=picture,
                    **{id_field: provider_id},
                )
                session.add(user)
            await session.commit()
            await session.refresh(user)

    return user


def set_user_session(request, user: User) -> None:
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_picture"] = user.picture or ""
