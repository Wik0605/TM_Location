from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
import datetime

from app.csrf import require_csrf
from app.database import get_db
from app.limiter import limiter
from app.services import car_service, routing_service, reservation_service
from app.schemas import LocationForm
from app.templating import templates

router = APIRouter(prefix="", tags=["web"])
def _to_webp(url: str) -> str:
    if not url:
        return url
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        if url.endswith(ext):
            return url[: -len(ext)] + ".webp"
    return url


templates.env.filters["current_year"] = lambda: datetime.datetime.now().year
templates.env.filters["to_webp"] = _to_webp


def _traduire_erreur(exc: ValidationError) -> str:
    return "Erreur de saisie, veuillez vérifier les informations du formulaire."


def _parse_date(value: str | None) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    depart = _parse_date(request.query_params.get("depart"))
    retour = _parse_date(request.query_params.get("retour"))
    voitures_dispo = await car_service.get_voitures_avec_disponibilite(
        db, depart, retour, limit=6
    )
    return templates.TemplateResponse("index.html", {
        "request": request,
        "voitures_dispo": voitures_dispo,
        "depart": depart.isoformat() if depart else "",
        "retour": retour.isoformat() if retour else "",
    })


@router.get("/voitures", response_class=HTMLResponse)
async def voitures_list(request: Request, db: AsyncSession = Depends(get_db)):
    depart = _parse_date(request.query_params.get("depart"))
    retour = _parse_date(request.query_params.get("retour"))
    voitures_dispo = await car_service.get_voitures_avec_disponibilite(
        db, depart, retour, order_by_marque=True
    )
    return templates.TemplateResponse("voitures.html", {
        "request": request,
        "voitures_dispo": voitures_dispo,
        "depart": depart.isoformat() if depart else "",
        "retour": retour.isoformat() if retour else "",
    })


@router.get("/voitures/{voiture_id}", response_class=HTMLResponse)
async def voiture_detail(request: Request, voiture_id: int, db: AsyncSession = Depends(get_db)):
    voiture = await car_service.get_voiture_by_id(db, voiture_id)
    if not voiture:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    depart = _parse_date(request.query_params.get("depart"))
    retour = _parse_date(request.query_params.get("retour"))
    return templates.TemplateResponse("voiture_detail.html", {
        "request": request,
        "voiture": voiture,
        "depart": depart.isoformat() if depart else "",
        "retour": retour.isoformat() if retour else "",
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
    return JSONResponse({"allowed": routing_service.verifier_quota(request)})


@router.post("/voitures/{voiture_id}/reserver", response_class=HTMLResponse)
@limiter.limit("10/hour")
async def voiture_reserver(
    request: Request,
    voiture_id: int,
    db: AsyncSession = Depends(get_db),
    _csrf: None = Depends(require_csrf),
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
            date_fin=form_data.get("date_fin") or None,
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

    disponible = await car_service.voiture_est_disponible(
        db, voiture.id, form.date_debut, form.date_fin
    )
    if not disponible:
        return templates.TemplateResponse("voiture_detail.html", {
            "request": request,
            "voiture": voiture,
            "depart": form.date_debut.isoformat(),
            "retour": form.date_fin.isoformat() if form.date_fin else "",
            "erreur_disponibilite": True,
        }, status_code=409)

    loc, type_location = await reservation_service.creer_reservation(
        db, voiture, form, form_data.get("itinerary_token")
    )

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
