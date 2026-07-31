import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.schemas import AdminLoginForm

router = APIRouter(prefix="/admin", tags=["admin-auth"])
templates = Jinja2Templates(directory="app/templates")


def require_admin(request: Request):
    if not request.session.get("admin_logged_in"):
        return RedirectResponse("/admin/login", status_code=302)
    return None


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    if request.session.get("admin_logged_in"):
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/login")
async def admin_login(
    request: Request,
    form: AdminLoginForm = Depends(AdminLoginForm.as_form),
):
    ok_user = secrets.compare_digest(form.username, settings.admin_username)
    ok_pass = secrets.compare_digest(form.password, settings.admin_password)
    if ok_user and ok_pass:
        request.session["admin_logged_in"] = True
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse("admin/login.html", {
        "request": request,
        "error": "Identifiant ou mot de passe incorrect.",
    })


@router.get("/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)
