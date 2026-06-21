from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services import admin_service
from app.routers.admin_auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin-rentals"])
templates = Jinja2Templates(directory="app/templates")


# ── Dashboard ──

@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect
    stats = await admin_service.get_dashboard_stats(db)
    recent_rentals = await admin_service.get_all_rentals(db)
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_rentals": recent_rentals[:5],
    })


# ── Réservations ──

@router.get("/reservations", response_class=HTMLResponse)
async def admin_reservations(request: Request, db: AsyncSession = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect
    rentals = await admin_service.get_all_rentals(db)
    return templates.TemplateResponse("admin/reservations.html", {
        "request": request,
        "rentals": rentals,
    })


@router.post("/reservations/{rental_id}/status", response_class=HTMLResponse)
async def update_rental_status(
    request: Request,
    rental_id: int,
    status: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    rental = await admin_service.update_rental_status(db, rental_id, status)
    return templates.TemplateResponse("admin/partials/_rental_row.html", {
        "request": request,
        "rental": rental,
    })


# ── Types de location ──

@router.get("/rental-types", response_class=HTMLResponse)
async def admin_rental_types(request: Request, db: AsyncSession = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect
    rental_types = await admin_service.get_all_rental_types(db)
    return templates.TemplateResponse("admin/rental_types.html", {
        "request": request,
        "rental_types": rental_types,
    })


@router.post("/rental-types/create", response_class=HTMLResponse)
async def create_rental_type(
    request: Request,
    name: str = Form(...),
    duration_days: int = Form(...),
    prix_fixe: Optional[float] = Form(None),
    fuel_consumption: Optional[float] = Form(None),
    fuel_price: Optional[float] = Form(None),
    discount_percent: float = Form(0.0),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    data = {
        "name": name,
        "duration_days": duration_days,
        "prix_fixe": prix_fixe,
        "fuel_consumption": fuel_consumption,
        "fuel_price": fuel_price,
        "discount_percent": discount_percent,
        "description": description,
    }
    await admin_service.create_rental_type(db, data)
    rental_types = await admin_service.get_all_rental_types(db)
    return templates.TemplateResponse("admin/partials/_rental_types_list.html", {
        "request": request,
        "rental_types": rental_types,
    })


@router.post("/rental-types/{rental_type_id}/edit", response_class=HTMLResponse)
async def edit_rental_type(
    request: Request,
    rental_type_id: int,
    name: str = Form(...),
    duration_days: int = Form(...),
    prix_fixe: Optional[float] = Form(None),
    fuel_consumption: Optional[float] = Form(None),
    fuel_price: Optional[float] = Form(None),
    discount_percent: float = Form(0.0),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    data = {
        "name": name,
        "duration_days": duration_days,
        "prix_fixe": prix_fixe,
        "fuel_consumption": fuel_consumption,
        "fuel_price": fuel_price,
        "discount_percent": discount_percent,
        "description": description,
    }
    await admin_service.update_rental_type(db, rental_type_id, data)
    rental_types = await admin_service.get_all_rental_types(db)
    return templates.TemplateResponse("admin/partials/_rental_types_list.html", {
        "request": request,
        "rental_types": rental_types,
    })


@router.post("/rental-types/{rental_type_id}/delete", response_class=HTMLResponse)
async def delete_rental_type(
    request: Request,
    rental_type_id: int,
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    await admin_service.delete_rental_type(db, rental_type_id)
    rental_types = await admin_service.get_all_rental_types(db)
    return templates.TemplateResponse("admin/partials/_rental_types_list.html", {
        "request": request,
        "rental_types": rental_types,
    })
