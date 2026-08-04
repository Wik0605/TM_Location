from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
import datetime
from datetime import date

from app.database import get_db
from app.services import car_service, routing_service
from app.models import Location
from app.schemas import LocationForm

router = APIRouter(prefix="", tags=["web"])
def _to_webp(url: str) -> str:
    if not url:
        return url
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        if url.endswith(ext):
            return url[: -len(ext)] + ".webp"
    return url


templates = Jinja2Templates(directory="app/templates")
templates.env.filters["current_year"] = lambda: datetime.datetime.now().year
templates.env.filters["to_webp"] = _to_webp


def _traduire_erreur(exc: ValidationError) -> str:
    return "Erreur de saisie, veuillez vérifier les informations du formulaire."


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


@router.post("/voitures/{voiture_id}/itineraire/quota")
async def itineraire_quota(request: Request, voiture_id: int):
    from fastapi.responses import JSONResponse
    if request.session.get("user_id"):
        return JSONResponse({"allowed": True})
    today = str(date.today())
    if request.session.get("itinerary_date") != today:
        request.session["itinerary_date"] = today
        request.session["itinerary_count"] = 0
    count = request.session.get("itinerary_count", 0)
    if count >= 7:
        return JSONResponse({"allowed": False})
    request.session["itinerary_count"] = count + 1
    return JSONResponse({"allowed": True})


@router.post("/voitures/{voiture_id}/reserver", response_class=HTMLResponse)
async def voiture_reserver(
    request: Request,
    voiture_id: int,
    db: AsyncSession = Depends(get_db),
):
    voiture = await car_service.get_voiture_by_id(db, voiture_id)
    if not voiture:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    form_data = await request.form()
    try:
        form = LocationForm(
            type_location_id=form_data.get("type_location_id") or None,
            client_nom=form_data.get("client_nom", ""),
            client_telephone=form_data.get("client_telephone", ""),
            client_email=form_data.get("client_email") or None,
            date_debut=form_data.get("date_debut", ""),
            notes=form_data.get("notes") or None,
            itinerary_distance_km=None,
            itinerary_start_name=form_data.get("itinerary_start_name") or None,
            itinerary_end_name=form_data.get("itinerary_end_name") or None,
            itinerary_waypoints=None,
        )
    except ValidationError as e:
        return templates.TemplateResponse("voiture_detail.html", {
            "request": request,
            "voiture": voiture,
            "error": _traduire_erreur(e),
        }, status_code=400)

    token = form_data.get("itinerary_token")
    if token:
        token_data = routing_service.lire_token(token)
        if token_data and token_data["voiture_id"] == voiture_id:
            form.itinerary_distance_km = token_data["distance_km"]
            form.itinerary_waypoints = ";".join(
                f"{lat},{lon}" for lat, lon in token_data["waypoints"]
            )

    type_location = next(
        (t for t in voiture.types_location if t.id == form.type_location_id), None
    )
    prix_total = float(type_location.prix) if type_location else 0.0

    loc = Location(
        voiture_id=voiture_id,
        type_location_id=form.type_location_id,
        client_nom=form.client_nom,
        client_telephone=form.client_telephone,
        client_email=form.client_email,
        date_debut=datetime.datetime.combine(form.date_debut, datetime.time.min),
        prix_total=prix_total,
        statut="confirmée",
        notes=form.notes,
        itineraire_distance_km=form.itinerary_distance_km,
        itineraire_depart=form.itinerary_start_name,
        itineraire_arrivee=form.itinerary_end_name,
        itineraire_etapes=form.itinerary_waypoints,
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


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request):
    base = str(request.base_url).rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /api/\n"
        f"\nSitemap: {base}/sitemap.xml\n"
    )


@router.get("/sitemap.xml")
async def sitemap_xml(request: Request, db: AsyncSession = Depends(get_db)):
    base = str(request.base_url).rstrip("/")
    voitures = await car_service.get_available_voitures(db)

    urls = [f"{base}/", f"{base}/voitures"]
    for v in voitures:
        urls.append(f"{base}/voitures/{v.id}")
        urls.append(f"{base}/voitures/{v.id}/itineraire")

    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        body.append(f"  <url><loc>{url}</loc></url>")
    body.append("</urlset>")

    return Response(content="\n".join(body), media_type="application/xml")
