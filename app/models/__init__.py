"""Modeles SQLModel (source unique DB + validation)."""

from app.models.analytics import AnalyticsEvent, EventIn
from app.models.itineraire import DevisResponse, ItineraireRequest
from app.models.reservation import Location, LocationCreate, LocationRead
from app.models.user import User, UserRead
from app.models.voiture import (
    TypeLocation,
    TypeLocationCreate,
    TypeLocationRead,
    Voiture,
    VoitureCreate,
    VoitureImage,
    VoitureRead,
    VoitureUpdate,
)

__all__ = [
    "AnalyticsEvent",
    "EventIn",
    "DevisResponse",
    "ItineraireRequest",
    "Location",
    "LocationCreate",
    "LocationRead",
    "User",
    "UserRead",
    "TypeLocation",
    "TypeLocationCreate",
    "TypeLocationRead",
    "Voiture",
    "VoitureCreate",
    "VoitureImage",
    "VoitureRead",
    "VoitureUpdate",
]
