import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.csrf import require_csrf
from app.limiter import limiter
from app.schemas import AdminLoginForm
from app.templating import templates

LOGIN_RATE_LIMIT = "5/15minutes"

security_logger = logging.getLogger("security")


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

router = APIRouter(prefix="/admin", tags=["admin-auth"])


def require_admin(request: Request) -> None:
    if not request.session.get("admin_logged_in"):
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    if request.session.get("admin_logged_in"):
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/login")
@limiter.limit(LOGIN_RATE_LIMIT)
async def admin_login(
    request: Request,
    form: AdminLoginForm = Depends(AdminLoginForm.as_form),
    _csrf: None = Depends(require_csrf),
):
    ok_user = secrets.compare_digest(form.username, settings.admin_username)
    ok_pass = secrets.compare_digest(form.password, settings.admin_password)
    ip = _client_ip(request)
    if ok_user and ok_pass:
        request.session.clear()
        request.session["admin_logged_in"] = True
        security_logger.info("admin_login_success user=%s ip=%s", form.username, ip)
        return RedirectResponse("/admin", status_code=302)
    security_logger.warning(
        "admin_login_failure user=%s ip=%s", form.username, ip
    )
    return templates.TemplateResponse("admin/login.html", {
        "request": request,
        "error": "Identifiant ou mot de passe incorrect.",
    })


@router.get("/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)


async def login_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    security_logger.warning(
        "rate_limit_exceeded path=%s ip=%s", request.url.path, _client_ip(request)
    )
    if request.url.path == "/admin/login":
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error": "Trop de tentatives. Réessayez dans quelques minutes.",
            },
            status_code=429,
        )
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        "Trop de requêtes. Réessayez dans quelques minutes.",
        status_code=429,
    )
