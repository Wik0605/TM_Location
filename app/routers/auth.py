import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
REDIRECT_URI = "http://localhost:8000/auth/google/callback"
SCOPES = "openid email profile"


@router.get("/google")
async def google_login(request: Request):
    if next_url := request.query_params.get("next"):
        request.session["next_url"] = next_url
    params = (
        f"client_id={settings.google_client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPES.replace(' ', '%20')}"
        f"&access_type=offline"
    )
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{params}")


@router.get("/google/callback")
async def google_callback(request: Request, code: str):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        userinfo = userinfo_response.json()

    google_id = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name")
    picture = userinfo.get("picture")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.google_id == google_id))
        user = result.scalars().first()

        if not user:
            user = User(google_id=google_id, email=email, name=name, picture=picture)
            session.add(user)
            await session.commit()
            await session.refresh(user)

    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_picture"] = user.picture or ""

    next_url = request.session.pop("next_url", "/")
    return RedirectResponse(url=next_url)


@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user_id", None)
    request.session.pop("user_name", None)
    request.session.pop("user_picture", None)
    return RedirectResponse(url="/")
