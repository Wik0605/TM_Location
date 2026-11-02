from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.client.analytics import service as analytics_service
from app.client.reservations import service as reservation_service
from app.client.voitures import service as car_service
from app.limiter import limiter
from app.client.reservations.forms import LocationForm
from app.models.reservation import Location
from app.shared.deps import get_db, require_csrf
from app.templating import templates


router = APIRouter(prefix="", tags=["client-reservations"])


def _traduire_erreur(exc: ValidationError) -> list[str]:
    _MAP: dict[tuple[str, str], str] = {
        ("client_nom", "string_pattern_mismatch"): "Le nom doit contenir uniquement des lettres (pas de chiffres ni de symboles).",
        ("client_nom", "string_too_short"):         "Le nom est trop court (2 caractères minimum).",
        ("client_telephone", "string_pattern_mismatch"): "Le numéro de téléphone doit contenir uniquement des chiffres.",
        ("client_email", "string_pattern_mismatch"):    "L'adresse email n'est pas valide (ex : jean@email.mg).",
        ("date_debut", "datetime_parsing"):             "La date de début est invalide.",
        ("date_debut", "datetime_from_date_parsing"):   "La date de début est invalide.",
    }
    messages: list[str] = []
    seen: set[str] = set()
    for err in exc.errors():
        field = err["loc"][0] if err["loc"] else ""
        etype = err["type"]
        msg = _MAP.get((str(field), etype))
        if msg is None:
            if str(field) == "date_debut" and etype == "value_error":
                msg = "Vous ne pouvez pas réserver à une date déjà passée."
            elif str(field) == "date_fin" and etype == "value_error":
                msg = "La date de retour doit être après la date de départ."
            else:
                msg = "Vérifiez les informations du formulaire."
        if msg not in seen:
            seen.add(msg)
            messages.append(msg)
    return messages or ["Vérifiez les informations du formulaire."]



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
        return templates.TemplateResponse("client/pages/404.html", {"request": request}, status_code=404)

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
        msgs = _traduire_erreur(e)
        return RedirectResponse(
            f"/voitures/{voiture.slug}/itineraire?erreur={msgs[0]}",
            status_code=303,
        )

    disponible = await car_service.voiture_est_disponible(
        db, voiture.id, form.date_debut, form.date_fin
    )
    if not disponible:
        return RedirectResponse(
            f"/voitures/{voiture.slug}/itineraire?erreur=Véhicule non disponible aux dates choisies.",
            status_code=303,
        )

    date_fin_effective = form.date_fin or form.date_debut
    if not car_service.verifier_heures_disponibilite(voiture, form.date_debut, date_fin_effective):
        return RedirectResponse(
            f"/voitures/{voiture.slug}/itineraire?erreur=Véhicule non disponible à ces heures.",
            status_code=303,
        )

    try:
        loc, type_location = await reservation_service.creer_reservation(
            db, voiture, form, form_data.get("itinerary_token"),
            user_id=request.session.get("user_id"),
        )
    except reservation_service.ReservationError as e:
        return RedirectResponse(
            f"/voitures/{voiture.slug}/itineraire?erreur={e}",
            status_code=303,
        )

    ctx = analytics_service.extraire_contexte(request)
    background.add_task(
        analytics_service.enregistrer_reservation,
        ctx["session_id"],
        ctx["referer_host"],
        ctx["hour_local"],
        loc,
    )

    return templates.TemplateResponse("client/reservations/voiture_confirmation.html", {
        "request": request,
        "location": loc,
        "voiture": voiture,
        "type_location": type_location,
    })


@router.get("/reservations/{reservation_id}/recu", response_class=HTMLResponse)
async def page_recu(
    request: Request,
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Location).where(Location.id == reservation_id))
    loc = result.scalar_one_or_none()
    if not loc:
        return templates.TemplateResponse("client/pages/404.html", {"request": request}, status_code=404)

    await db.refresh(loc, ["voiture", "type_location"])

    return templates.TemplateResponse("client/reservations/recu.html", {
        "request": request,
        "location": loc,
        "voiture": loc.voiture,
        "type_location": loc.type_location,
    })
