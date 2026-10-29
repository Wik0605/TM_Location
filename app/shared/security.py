from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

ADMIN_SESSION_KEY = "admin_logged_in"


def is_admin(request: Request) -> bool:
    return bool(request.session.get(ADMIN_SESSION_KEY))


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )


async def get_current_user(
    request: Request, db: AsyncSession
) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
