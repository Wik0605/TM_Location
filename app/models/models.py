"""
Modèles de données SQLAlchemy

Tables actives :
- Voiture : Véhicules disponibles à la location
- VoitureImage : Photos d'un véhicule
- TypeLocation : Tarifs propres à chaque voiture (ex: "Mariage — 500 000 Ar")
- Location : Réservations effectuées par les clients
- User : Clients connectés via Google OAuth
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Voiture(Base):
    """Nouveau modèle unifié de véhicule avec types de location propres."""
    __tablename__ = "voitures"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    consommation_carburant: Mapped[float] = mapped_column(Float, default=8.0)
    places: Mapped[int] = mapped_column(Integer, default=5)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images: Mapped[list["VoitureImage"]] = relationship(
        back_populates="voiture", order_by="VoitureImage.position", cascade="all, delete-orphan"
    )
    types_location: Mapped[list["TypeLocation"]] = relationship(
        back_populates="voiture", cascade="all, delete-orphan"
    )
    locations: Mapped[list["Location"]] = relationship(back_populates="voiture")

    # Compatibilité itineraire.html
    @property
    def brand(self) -> str:
        return self.nom

    @property
    def model(self) -> str:
        return ""

    @property
    def seats(self) -> int:
        return self.places

    @property
    def fuel_consumption(self) -> float:
        return self.consommation_carburant

    @property
    def daily_price(self) -> float:
        return 0.0

    def __repr__(self):
        return f"<Voiture(id={self.id}, nom='{self.nom}')>"


class VoitureImage(Base):
    """Photos d'une voiture (nouvelle architecture)."""
    __tablename__ = "voiture_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    voiture_id: Mapped[int] = mapped_column(ForeignKey("voitures.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    voiture: Mapped["Voiture"] = relationship(back_populates="images")

    def __repr__(self):
        return f"<VoitureImage(id={self.id}, voiture_id={self.voiture_id})>"


class TypeLocation(Base):
    """Type de location propre à une voiture (ex: 'Location Mariage — 500 000 Ar')."""
    __tablename__ = "types_location"

    id: Mapped[int] = mapped_column(primary_key=True)
    voiture_id: Mapped[int] = mapped_column(ForeignKey("voitures.id"), nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prix: Mapped[int] = mapped_column(Integer, nullable=False)

    voiture: Mapped["Voiture"] = relationship(back_populates="types_location")
    locations: Mapped[list["Location"]] = relationship(back_populates="type_location")

    # Compatibilité avec itineraire.html (ancienne interface RentalType)
    @property
    def name(self) -> str:
        return self.nom

    @property
    def prix_fixe(self) -> int:
        return self.prix

    @property
    def price_multiplier(self) -> float:
        return 1.0

    @property
    def discount_percent(self) -> float:
        return 0.0

    @property
    def fuel_consumption(self):
        return None

    @property
    def fuel_price(self):
        return None

    def __repr__(self):
        return f"<TypeLocation(id={self.id}, nom='{self.nom}', prix={self.prix})>"


class Location(Base):
    """Réservation (nouvelle architecture) liée à une Voiture et un TypeLocation."""
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    voiture_id: Mapped[int] = mapped_column(ForeignKey("voitures.id"), nullable=False)
    type_location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("types_location.id"), nullable=True)
    client_nom: Mapped[str] = mapped_column(String(100), nullable=False)
    client_telephone: Mapped[str] = mapped_column(String(20), nullable=False)
    client_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_debut: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    date_fin: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duree_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prix_total: Mapped[float] = mapped_column(Float, nullable=False)
    statut: Mapped[str] = mapped_column(String(20), default="confirmée")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    itineraire_distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itineraire_depart: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    itineraire_arrivee: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    depart_coords: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    arrivee_coords: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    itineraire_etapes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    itineraire_source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    voiture: Mapped["Voiture"] = relationship(back_populates="locations")
    type_location: Mapped[Optional["TypeLocation"]] = relationship(back_populates="locations")

    def __repr__(self):
        return f"<Location(id={self.id}, client='{self.client_nom}', statut='{self.statut}')>"


class AnalyticsEvent(Base):
    """Événements analytics maison (léger, sans dépendance externe)."""
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    depart_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    depart_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    arrivee_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    arrivee_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    depart_nom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    arrivee_nom: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    voiture_id: Mapped[Optional[int]] = mapped_column(ForeignKey("voitures.id"), nullable=True)
    type_location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("types_location.id"), nullable=True)
    prix: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    referer_host: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    hour_local: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AnalyticsEvent(id={self.id}, type='{self.event_type}')>"


class User(Base):
    """Client connecté via OAuth (Google, Facebook)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    facebook_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    picture: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


