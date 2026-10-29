from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.client.auth.providers import facebook, google
from app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google")
@limiter.limit("20/hour")
async def google_login(request: Request):
    return await google.start_login(request)


@router.get("/google/callback")
async def google_callback(request: Request, code: str = "", state: str = ""):
    return await google.handle_callback(request, code, state)


@router.get("/facebook")
@limiter.limit("20/hour")
async def facebook_login(request: Request):
    return await facebook.start_login(request)


@router.get("/facebook/callback")
async def facebook_callback(request: Request, code: str = "", state: str = ""):
    return await facebook.handle_callback(request, code, state)


@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user_id", None)
    request.session.pop("user_name", None)
    request.session.pop("user_picture", None)
    return RedirectResponse(url="/")
