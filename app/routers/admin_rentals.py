from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.csrf import require_csrf
from app.database import get_db
from app.services import admin_service
from app.routers.admin_auth import require_admin
from app.schemas import RentalStatusForm
from app.templating import templates

router = APIRouter(
    prefix="/admin",
    tags=["admin-rentals"],
    dependencies=[Depends(require_admin), Depends(require_csrf)],
)


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    stats = await admin_service.get_dashboard_stats(db)
    recent_locations = await admin_service.get_all_locations(db)
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_rentals": recent_locations[:5],
    })


@router.get("/reservations", response_class=HTMLResponse)
async def admin_reservations(request: Request, db: AsyncSession = Depends(get_db)):
    locations = await admin_service.get_all_locations(db)
    return templates.TemplateResponse("admin/reservations.html", {
        "request": request,
        "rentals": locations,
    })


@router.post("/reservations/{location_id}/status", response_class=HTMLResponse)
async def update_location_status(
    request: Request,
    location_id: int,
    form: RentalStatusForm = Depends(RentalStatusForm.as_form),
    db: AsyncSession = Depends(get_db),
):
    loc = await admin_service.update_location_statut(db, location_id, form.status.value)
    return templates.TemplateResponse("admin/partials/_rental_row.html", {
        "request": request,
        "rental": loc,
    })
