from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import admin_service
from app.routers.admin_auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin-rentals"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect
    stats = await admin_service.get_dashboard_stats(db)
    recent_locations = await admin_service.get_all_locations(db)
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_rentals": recent_locations[:5],
    })


@router.get("/reservations", response_class=HTMLResponse)
async def admin_reservations(request: Request, db: AsyncSession = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect
    locations = await admin_service.get_all_locations(db)
    return templates.TemplateResponse("admin/reservations.html", {
        "request": request,
        "rentals": locations,
    })


@router.post("/reservations/{location_id}/status", response_class=HTMLResponse)
async def update_location_status(
    request: Request,
    location_id: int,
    status: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    loc = await admin_service.update_location_statut(db, location_id, status)
    return templates.TemplateResponse("admin/partials/_rental_row.html", {
        "request": request,
        "rental": loc,
    })
