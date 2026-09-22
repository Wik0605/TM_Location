from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

import datetime as _dt

from app.client.voitures import service
from app.shared.deps import get_db
from app.templating import templates


router = APIRouter(prefix="", tags=["client-voitures"])


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return _dt.date.fromisoformat(value)
    except ValueError:
        return None


@router.get("/voitures", response_class=HTMLResponse)
async def voitures_list(request: Request, db: AsyncSession = Depends(get_db)):
    depart = _parse_date(request.query_params.get("depart"))
    retour = _parse_date(request.query_params.get("retour"))
    voitures_dispo = await service.get_voitures_avec_disponibilite(
        db, depart, retour, order_by_marque=True
    )
    return templates.TemplateResponse("client/voitures/voitures.html", {
        "request": request,
        "voitures_dispo": voitures_dispo,
        "depart": depart.isoformat() if depart else "",
        "retour": retour.isoformat() if retour else "",
    })


@router.get("/voitures/{key}", response_class=HTMLResponse)
async def voiture_detail(request: Request, key: str, db: AsyncSession = Depends(get_db)):
    voiture, par_id = await service.resoudre_voiture(db, key)
    if not voiture:
        return templates.TemplateResponse("client/pages/404.html", {"request": request}, status_code=404)
    if par_id:
        return RedirectResponse(f"/voitures/{voiture.slug}", status_code=301)
    depart = _parse_date(request.query_params.get("depart"))
    retour = _parse_date(request.query_params.get("retour"))
    return templates.TemplateResponse("client/voitures/voiture_detail.html", {
        "request": request,
        "voiture": voiture,
        "depart": depart.isoformat() if depart else "",
        "retour": retour.isoformat() if retour else "",
    })


@router.get("/voitures/{key}/itineraire", response_class=HTMLResponse)
async def voiture_itineraire(request: Request, key: str, db: AsyncSession = Depends(get_db)):
    voiture, par_id = await service.resoudre_voiture(db, key)
    if not voiture:
        return templates.TemplateResponse("client/pages/404.html", {"request": request}, status_code=404)
    if par_id:
        return RedirectResponse(f"/voitures/{voiture.slug}/itineraire", status_code=301)
    return templates.TemplateResponse("client/voitures/itineraire.html", {
        "request": request,
        "car": voiture,
        "rental_types": voiture.types_location,
    })
