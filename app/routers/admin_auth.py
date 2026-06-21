from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings

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
    username: str = Form(...),
    password: str = Form(...),
):
    if username == settings.admin_username and password == settings.admin_password:
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
