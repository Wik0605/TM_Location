from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import datetime
from datetime import date

from app.database import get_db
from app.services import car_service
from app.models import Location

router = APIRouter(prefix="", tags=["web"])
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["current_year"] = lambda: datetime.datetime.now().year


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    voitures = await car_service.get_available_voitures(db, limit=6)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "voitures": voitures,
    })


@router.get("/voitures", response_class=HTMLResponse)
async def voitures_list(request: Request, db: AsyncSession = Depends(get_db)):
    voitures = await car_service.get_available_voitures(db, order_by_marque=True)
    return templates.TemplateResponse("voitures.html", {
        "request": request,
        "voitures": voitures,
    })


@router.get("/voitures/{voiture_id}", response_class=HTMLResponse)
async def voiture_detail(request: Request, voiture_id: int, db: AsyncSession = Depends(get_db)):
    voiture = await car_service.get_voiture_by_id(db, voiture_id)
    if not voiture:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("voiture_detail.html", {
        "request": request,
        "voiture": voiture,
    })


@router.get("/voitures/{voiture_id}/itineraire", response_class=HTMLResponse)
async def voiture_itineraire(request: Request, voiture_id: int, db: AsyncSession = Depends(get_db)):
    voiture = await car_service.get_voiture_by_id(db, voiture_id)
    if not voiture:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("itineraire.html", {
        "request": request,
        "car": voiture,
        "rental_types": voiture.types_location,
    })


@router.post("/voitures/{voiture_id}/reserver", response_class=HTMLResponse)
async def voiture_reserver(
    request: Request,
    voiture_id: int,
    db: AsyncSession = Depends(get_db),
    type_location_id: Optional[int] = Form(None),
    client_nom: str = Form(...),
    client_telephone: str = Form(...),
    client_email: Optional[str] = Form(None),
    date_debut: str = Form(...),
    notes: Optional[str] = Form(None),
    itinerary_distance_km: Optional[float] = Form(None),
    itinerary_start_name: Optional[str] = Form(None),
    itinerary_end_name: Optional[str] = Form(None),
    itinerary_waypoints: Optional[str] = Form(None),
):
    voiture = await car_service.get_voiture_by_id(db, voiture_id)
    if not voiture:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    type_location = next((t for t in voiture.types_location if t.id == type_location_id), None)
    prix_total = float(type_location.prix) if type_location else 0.0

    start = datetime.datetime.strptime(date_debut, "%Y-%m-%d")

    if start.date() < date.today():
        return templates.TemplateResponse("voiture_detail.html", {
            "request": request,
            "voiture": voiture,
            "error": "La date de départ ne peut pas être dans le passé.",
        })

    loc = Location(
        voiture_id=voiture_id,
        type_location_id=type_location_id,
        client_nom=client_nom,
        client_telephone=client_telephone,
        client_email=client_email,
        date_debut=start,
        prix_total=prix_total,
        statut="confirmée",
        notes=notes,
        itineraire_distance_km=itinerary_distance_km,
        itineraire_depart=itinerary_start_name,
        itineraire_arrivee=itinerary_end_name,
        itineraire_etapes=itinerary_waypoints,
    )
    db.add(loc)
    await db.commit()
    await db.refresh(loc)

    return templates.TemplateResponse("voiture_confirmation.html", {
        "request": request,
        "location": loc,
        "voiture": voiture,
        "type_location": type_location,
    })


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})
