"""
Routes Web (HTML/HTMX)

Routes disponibles :
- GET /              : Page d'accueil
- GET /cars          : Liste des voitures
- GET /cars/{id}     : Détail d'une voiture
- GET /car/{id}/itineraire : Calculateur d'itinéraire
- GET /booking       : Page de réservation
- GET /rental-types  : Page des tarifs
- GET /contact       : Page de contact
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import datetime
from datetime import date

from app.database import get_db
from app.services import car_service, rental_service, city_service
from app.models import Rental

router = APIRouter(prefix="", tags=["web"])
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["current_year"] = lambda: datetime.datetime.now().year


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    cars = await car_service.get_available_cars(db, limit=6)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "cars": cars,
    })


@router.get("/cars", response_class=HTMLResponse)
async def cars_list(request: Request, db: AsyncSession = Depends(get_db)):
    cars = await car_service.get_available_cars(db, order_by_price=True)

    return templates.TemplateResponse("cars.html", {
        "request": request,
        "cars": cars,
    })


@router.get("/cars/{car_id}", response_class=HTMLResponse)
async def car_detail(request: Request, car_id: int, db: AsyncSession = Depends(get_db)):
    car = await car_service.get_car_by_id(db, car_id)

    if not car:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    rental_types = await rental_service.get_rental_types(db)

    return templates.TemplateResponse("car_detail.html", {
        "request": request,
        "car": car,
        "rental_types": rental_types,
    })


@router.get("/car/{car_id}/itineraire", response_class=HTMLResponse)
async def car_itineraire(request: Request, car_id: int, db: AsyncSession = Depends(get_db)):
    car = await car_service.get_car_by_id(db, car_id)

    if not car:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    rental_types = await rental_service.get_rental_types(db)

    return templates.TemplateResponse("itineraire.html", {
        "request": request,
        "car": car,
        "rental_types": rental_types,
    })


@router.get("/booking", response_class=HTMLResponse)
async def booking_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    car_id: Optional[int] = None,
    distance: Optional[float] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    waypoints: Optional[str] = None,
):
    cars = await car_service.get_available_cars(db)
    rental_types = await rental_service.get_rental_types(db)
    car = await car_service.get_car_by_id(db, car_id) if car_id else None

    return templates.TemplateResponse("booking.html", {
        "request": request,
        "cars": cars,
        "rental_types": rental_types,
        "car": car,
        "itinerary_distance": distance,
        "itinerary_start": start,
        "itinerary_end": end,
        "itinerary_waypoints": waypoints,
    })


@router.post("/booking", response_class=HTMLResponse)
async def booking_submit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    car_id: int = Form(...),
    rental_type_id: int = Form(...),
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    customer_email: Optional[str] = Form(None),
    start_date: str = Form(...),
    itinerary_distance_km: Optional[float] = Form(None),
    itinerary_start_name: Optional[str] = Form(None),
    itinerary_end_name: Optional[str] = Form(None),
    itinerary_waypoints: Optional[str] = Form(None),
):
    rental_types = await rental_service.get_rental_types(db)
    car = await car_service.get_car_by_id(db, car_id)
    rental_type = next((r for r in rental_types if r.id == rental_type_id), None)

    if not car or not rental_type:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end = start + datetime.timedelta(days=rental_type.duration_days)

    cars = await car_service.get_available_cars(db)
    rental_types = await rental_service.get_rental_types(db)

    def error_response(message: str):
        return templates.TemplateResponse("booking.html", {
            "request": request,
            "cars": cars,
            "rental_types": rental_types,
            "car": car,
            "error": message,
        })

    if start.date() < date.today():
        return error_response("La date de départ ne peut pas être dans le passé.")

    if await rental_service.has_conflict(db, car_id, start, end):
        return error_response("Cette voiture est déjà réservée sur ces dates. Choisissez d'autres dates.")

    if rental_type.prix_fixe is not None:
        total_price = float(rental_type.prix_fixe) * (1 - rental_type.discount_percent / 100)
    else:
        total_price = car.daily_price * rental_type.price_multiplier * (1 - rental_type.discount_percent / 100)

    rental = Rental(
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        car_id=car_id,
        rental_type_id=rental_type_id,
        start_date=start,
        end_date=end,
        total_price=total_price,
        status="confirmée",
        itinerary_distance_km=itinerary_distance_km,
        itinerary_start_name=itinerary_start_name,
        itinerary_end_name=itinerary_end_name,
        itinerary_waypoints=itinerary_waypoints,
    )
    db.add(rental)
    await db.commit()
    await db.refresh(rental)

    return templates.TemplateResponse("booking_confirmation.html", {
        "request": request,
        "rental": rental,
        "car": car,
        "rental_type": rental_type,
    })


@router.get("/rental-types", response_class=HTMLResponse)
async def rental_types_page(request: Request, db: AsyncSession = Depends(get_db)):
    rental_types = await rental_service.get_rental_types(db)

    return templates.TemplateResponse("rental_types.html", {
        "request": request,
        "rental_types": rental_types,
    })


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})


# =============================================================================
# PARTIALS HTMX
# =============================================================================

@router.get("/api/cars/search", response_class=HTMLResponse)
async def search_cars(request: Request, db: AsyncSession = Depends(get_db)):
    cars = await car_service.get_available_cars(db, order_by_price=True)
    return templates.TemplateResponse("partials/_car_list.html", {"request": request, "cars": cars})


@router.get("/api/cars/popular", response_class=HTMLResponse)
async def popular_cars(request: Request, db: AsyncSession = Depends(get_db)):
    cars = await car_service.get_available_cars(db, limit=6)
    return templates.TemplateResponse("partials/_car_grid.html", {"request": request, "cars": cars})
