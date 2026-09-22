from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.analytics import service as analytics_service
from app.client.reservations import service as reservation_service
from app.client.voitures import service as car_service
from app.limiter import limiter
from app.schemas import LocationForm
from app.shared.deps import get_db, require_csrf
from app.templating import templates


router = APIRouter(prefix="", tags=["client-reservations"])


def _traduire_erreur(exc: ValidationError) -> str:
    return "Erreur de saisie, veuillez vérifier les informations du formulaire."


@router.post("/voitures/{key}/reserver", response_class=HTMLResponse)
@limiter.limit("10/hour")
async def voiture_reserver(
    request: Request,
    key: str,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _csrf: None = Depends(require_csrf),
):
    voiture, _ = await car_service.resoudre_voiture(db, key)
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

    try:
        loc, type_location = await reservation_service.creer_reservation(
            db, voiture, form, form_data.get("itinerary_token")
        )
    except reservation_service.ReservationError as e:
        return templates.TemplateResponse("voiture_detail.html", {
            "request": request,
            "voiture": voiture,
            "error": str(e),
        }, status_code=400)

    ctx = analytics_service.extraire_contexte(request)
    background.add_task(
        analytics_service.enregistrer_reservation,
        ctx["session_id"],
        ctx["referer_host"],
        ctx["hour_local"],
        loc,
    )

    return templates.TemplateResponse("voiture_confirmation.html", {
        "request": request,
        "location": loc,
        "voiture": voiture,
        "type_location": type_location,
    })
