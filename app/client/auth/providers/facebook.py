import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import settings
from app.client.auth.service import set_user_session, upsert_oauth_user

FACEBOOK_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
FACEBOOK_USERINFO_URL = "https://graph.facebook.com/me"
FACEBOOK_SCOPES = "email public_profile"

HTTP_TIMEOUT = 10.0

security_logger = logging.getLogger("security")


async def start_login(request: Request) -> RedirectResponse:
    if not settings.facebook_client_id or not settings.facebook_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Connexion Facebook indisponible (configuration manquante).",
        )

    if next_url := request.query_params.get("next"):
        request.session["next_url"] = next_url

    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state

    params = urlencode({
        "client_id": settings.facebook_client_id,
        "redirect_uri": settings.facebook_redirect_uri,
        "response_type": "code",
        "scope": FACEBOOK_SCOPES,
        "state": state,
    })
    return RedirectResponse(url=f"{FACEBOOK_AUTH_URL}?{params}")


async def handle_callback(request: Request, code: str, state: str) -> RedirectResponse:
    expected_state = request.session.pop("oauth_state", None)
    if not expected_state or not state or not secrets.compare_digest(state, expected_state):
        ip = request.client.host if request.client else "unknown"
        security_logger.warning("oauth_state_mismatch provider=facebook ip=%s", ip)
        raise HTTPException(status_code=400, detail="État OAuth invalide.")

    if not code:
        raise HTTPException(status_code=400, detail="Code OAuth manquant.")

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            token_response = await client.get(FACEBOOK_TOKEN_URL, params={
                "code": code,
                "client_id": settings.facebook_client_id,
                "client_secret": settings.facebook_client_secret,
                "redirect_uri": settings.facebook_redirect_uri,
            })
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise HTTPException(status_code=502, detail="Réponse Facebook invalide.")

            userinfo_response = await client.get(
                FACEBOOK_USERINFO_URL,
                params={
                    "fields": "id,name,email,picture.type(large)",
                    "access_token": access_token,
                },
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Erreur de communication avec Facebook.")

    facebook_id = userinfo.get("id")
    email = userinfo.get("email")
    name = userinfo.get("name")
    picture_data = userinfo.get("picture", {}).get("data", {})
    picture = picture_data.get("url") if isinstance(picture_data, dict) else None

    if not facebook_id or not email:
        raise HTTPException(status_code=502, detail="Profil Facebook incomplet (email requis).")

    user = await upsert_oauth_user(
        provider="facebook",
        provider_id=facebook_id,
        email=email,
        name=name,
        picture=picture,
    )
    set_user_session(request, user)

    next_url = request.session.pop("next_url", "/")
    return RedirectResponse(url=next_url)
