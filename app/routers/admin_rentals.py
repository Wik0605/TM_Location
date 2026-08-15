import secrets

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.csrf import require_csrf
from app.database import get_db
from app.limiter import limiter
from app.services import admin_service
from app.routers.admin_auth import require_admin, _client_ip, security_logger
from app.schemas import RentalStatusForm, RentalDeleteForm
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
    template = templates.env.get_template("admin/reservations.html")
    return HTMLResponse(template.module.rental_row(loc))


@router.post("/reservations/{location_id}/delete", response_class=HTMLResponse)
@limiter.limit("3/15minutes")
async def delete_reservation(
    request: Request,
    location_id: int,
    form: RentalDeleteForm = Depends(RentalDeleteForm.as_form),
    db: AsyncSession = Depends(get_db),
):
    ip = _client_ip(request)
    ok_user = secrets.compare_digest(form.username, settings.admin_username)
    ok_pass = secrets.compare_digest(form.password, settings.admin_password)
    if not (ok_user and ok_pass):
        security_logger.warning(
            "admin_delete_failure location=%s user=%s ip=%s",
            location_id, form.username, ip,
        )
        return HTMLResponse(
            '<div class="px-3 py-2 mb-3 rounded-lg bg-red-50 text-red-700 text-sm">'
            'Identifiants incorrects.</div>'
        )

    await admin_service.delete_location(db, location_id)
    security_logger.info(
        "admin_delete_success location=%s user=%s ip=%s",
        location_id, form.username, ip,
    )
    response = HTMLResponse("")
    response.headers["HX-Trigger"] = f'{{"rentalDeleted": {location_id}}}'
    return response
