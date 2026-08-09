import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Location
from app.schemas import LocationForm
from app.services import routing_service


async def creer_reservation(
    db: AsyncSession,
    voiture,
    form: LocationForm,
    itinerary_token: str | None,
):
    if itinerary_token:
        token_data = routing_service.lire_token(itinerary_token)
        if token_data and token_data["voiture_id"] == voiture.id:
            form.itinerary_distance_km = token_data["distance_km"]
            form.itinerary_waypoints = ";".join(
                f"{lat},{lon}" for lat, lon in token_data["waypoints"]
            )

    type_location = next(
        (t for t in voiture.types_location if t.id == form.type_location_id), None
    )
    prix_total = float(type_location.prix) if type_location else 0.0

    loc = Location(
        voiture_id=voiture.id,
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

    return loc, type_location
