from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pathlib import Path
import uuid

from app.config import settings
from app.database import get_db
from app.services import admin_service

UPLOAD_DIR = Path(__file__).parent.parent.parent / "static" / "uploads" / "cars"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def require_admin(request: Request):
    if not request.session.get("admin_logged_in"):
        return RedirectResponse("/admin/login", status_code=302)
    return None


# ── Auth ──

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


# ── Voitures ──

@router.get("/cars", response_class=HTMLResponse)
async def admin_cars(request: Request, db: AsyncSession = Depends(get_db)):
    redirect = require_admin(request)
    if redirect:
        return redirect
    cars = await admin_service.get_all_cars(db)
    return templates.TemplateResponse("admin/cars.html", {
        "request": request,
        "cars": cars,
    })


@router.post("/cars/create", response_class=HTMLResponse)
async def create_car(
    request: Request,
    brand: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    plate_number: str = Form(...),
    daily_price: float = Form(...),
    seats: int = Form(5),
    fuel_consumption: float = Form(8.0),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    data = {
        "brand": brand,
        "model": model,
        "year": year,
        "plate_number": plate_number,
        "daily_price": daily_price,
        "seats": seats,
        "fuel_consumption": fuel_consumption,
        "description": description or None,
        "is_available": True,
    }
    await admin_service.create_car(db, data)
    cars = await admin_service.get_all_cars(db)
    return templates.TemplateResponse("admin/partials/_cars_grid.html", {
        "request": request,
        "cars": cars,
    })


@router.post("/cars/{car_id}/delete", response_class=HTMLResponse)
async def delete_car(
    request: Request,
    car_id: int,
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    await admin_service.delete_car(db, car_id)
    cars = await admin_service.get_all_cars(db)
    return templates.TemplateResponse("admin/partials/_cars_grid.html", {
        "request": request,
        "cars": cars,
    })


@router.post("/cars/{car_id}/edit", response_class=HTMLResponse)
async def edit_car(
    request: Request,
    car_id: int,
    seats: Optional[int] = Form(None),
    fuel_consumption: Optional[float] = Form(None),
    daily_price: Optional[float] = Form(None),
    description: Optional[str] = Form(None),
    is_available: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    data = {
        "seats": seats,
        "fuel_consumption": fuel_consumption,
        "daily_price": daily_price,
        "description": description if description else None,
        "is_available": is_available == "on" if is_available is not None else None,
    }
    data = {k: v for k, v in data.items() if v is not None}
    car = await admin_service.update_car(db, car_id, data)
    return templates.TemplateResponse("admin/partials/_car_card.html", {
        "request": request,
        "car": car,
        "success": True,
    })


@router.post("/cars/{car_id}/images", response_class=HTMLResponse)
async def add_car_images(
    request: Request,
    car_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    car_upload_dir = UPLOAD_DIR / str(car_id)
    car_upload_dir.mkdir(exist_ok=True)

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = car_upload_dir / filename
        dest.write_bytes(await file.read())
        url = f"/static/uploads/cars/{car_id}/{filename}"
        await admin_service.add_car_image(db, car_id, url)

    car = await admin_service.get_car_by_id(db, car_id)
    return templates.TemplateResponse("admin/partials/_car_images.html", {
        "request": request,
        "car": car,
    })


@router.post("/cars/{car_id}/images/{image_id}/delete", response_class=HTMLResponse)
async def delete_car_image(
    request: Request,
    car_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
):
    redirect = require_admin(request)
    if redirect:
        return redirect
    await admin_service.delete_car_image(db, image_id)
    car = await admin_service.get_car_by_id(db, car_id)
    return templates.TemplateResponse("admin/partials/_car_images.html", {
        "request": request,
        "car": car,
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
    price_multiplier: float = Form(...),
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
        "price_multiplier": price_multiplier,
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
    price_multiplier: float = Form(...),
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
        "price_multiplier": price_multiplier,
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
