import secrets

from fastapi import HTTPException, Request
from markupsafe import Markup

CSRF_SESSION_KEY = "csrf_token"
CSRF_FIELD_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def csrf_input(request: Request) -> Markup:
    token = get_or_create_csrf_token(request)
    return Markup(
        f'<input type="hidden" name="{CSRF_FIELD_NAME}" value="{token}">'
    )


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def require_csrf(request: Request) -> None:
    if request.method in SAFE_METHODS:
        return
    expected = request.session.get(CSRF_SESSION_KEY)
    if not expected:
        raise HTTPException(status_code=403, detail="Jeton CSRF absent de la session.")

    submitted = request.headers.get(CSRF_HEADER_NAME)
    if not submitted:
        content_type = request.headers.get("content-type", "")
        if content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
            form = await request.form()
            submitted = form.get(CSRF_FIELD_NAME)

    if not submitted or not secrets.compare_digest(str(submitted), expected):
        raise HTTPException(status_code=403, detail="Jeton CSRF invalide.")
