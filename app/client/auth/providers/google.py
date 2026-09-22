import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import settings
from app.client.auth.service import set_user_session, upsert_oauth_user

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = "openid email profile"

HTTP_TIMEOUT = 10.0

security_logger = logging.getLogger("security")


async def start_login(request: Request) -> RedirectResponse:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Connexion Google indisponible (configuration manquante).",
        )

    if next_url := request.query_params.get("next"):
        request.session["next_url"] = next_url

    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state

    params = urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "state": state,
    })
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{params}")


async def handle_callback(request: Request, code: str, state: str) -> RedirectResponse:
    expected_state = request.session.pop("oauth_state", None)
    if not expected_state or not state or not secrets.compare_digest(state, expected_state):
        ip = request.client.host if request.client else "unknown"
        security_logger.warning("oauth_state_mismatch ip=%s", ip)
        raise HTTPException(status_code=400, detail="État OAuth invalide.")

    if not code:
        raise HTTPException(status_code=400, detail="Code OAuth manquant.")

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            token_response = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            })
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise HTTPException(status_code=502, detail="Réponse Google invalide.")

            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Erreur de communication avec Google.")

    google_id = userinfo.get("sub")
    email = userinfo.get("email")
    email_verified = userinfo.get("email_verified", False)
    name = userinfo.get("name")
    picture = userinfo.get("picture")

    if not google_id or not email:
        raise HTTPException(status_code=502, detail="Profil Google incomplet.")
    if not email_verified:
        security_logger.warning("oauth_email_not_verified email=%s", email)
        raise HTTPException(status_code=403, detail="Email Google non vérifié.")

    user = await upsert_oauth_user(
        provider="google",
        provider_id=google_id,
        email=email,
        name=name,
        picture=picture,
    )
    set_user_session(request, user)

    next_url = request.session.pop("next_url", "/")
    return RedirectResponse(url=next_url)
