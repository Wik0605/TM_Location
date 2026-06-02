"""
Modèles de données SQLAlchemy

Tables :
- City : Quartiers de départ/arrivée (Antananarivo)
- Car : Véhicules disponibles à la location
- CarImage : Photos d'un véhicule (plusieurs photos par voiture)
- RentalType : Types de location (journalière, hebdomadaire, mensuelle)
- Rental : Réservations effectuées par les clients
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class City(Base):
    """Quartiers disponibles pour la sélection départ/arrivée."""
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self):
        return f"<City(id={self.id}, name='{self.name}')>"


class Car(Base):
    """
    Voitures disponibles à la location.

    Attributs importants :
    - brand / model / year : Identité du véhicule
    - daily_price : Prix par jour en Ariary
    - is_available : Disponibilité actuelle
    - seats : Nombre de places
    """
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    daily_price: Mapped[float] = mapped_column(Float, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seats: Mapped[int] = mapped_column(Integer, default=5)
    fuel_consumption: Mapped[float] = mapped_column(Float, default=8.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rentals: Mapped[list["Rental"]] = relationship(back_populates="car")
    images: Mapped[list["CarImage"]] = relationship(back_populates="car", order_by="CarImage.position")

    def __repr__(self):
        return f"<Car(id={self.id}, brand='{self.brand}', model='{self.model}')>"

    @property
    def full_name(self) -> str:
        return f"{self.brand} {self.model}"


class CarImage(Base):
    """
    Photos d'une voiture.

    Une voiture peut avoir plusieurs photos (relation one-to-many).
    position : ordre d'affichage dans le carousel (0 = photo principale)
    """
    __tablename__ = "car_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    car: Mapped["Car"] = relationship(back_populates="images")

    def __repr__(self):
        return f"<CarImage(id={self.id}, car_id={self.car_id}, position={self.position})>"


class RentalType(Base):
    """
    Types de location (Journalière, Hebdomadaire, Mensuelle, Week-end).

    price_multiplier : nombre de jours facturés (ex: 6.0 pour une semaine = payer 6 jours sur 7)
    discount_percent : remise en % (ex: 5 = 5% de réduction)
    """
    __tablename__ = "rental_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discount_percent: Mapped[float] = mapped_column(Float, default=0.0)

    rentals: Mapped[list["Rental"]] = relationship(back_populates="rental_type")

    def __repr__(self):
        return f"<RentalType(id={self.id}, name='{self.name}')>"


class Rental(Base):
    """
    Réservations effectuées par les clients.

    Un Rental lie un client (nom + téléphone) à une voiture et un type de location.
    status : "confirmée" | "en_cours" | "terminée" | "annulée"
    """
    __tablename__ = "rentals"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id"), nullable=False)
    rental_type_id: Mapped[int] = mapped_column(ForeignKey("rental_types.id"), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmée")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    itinerary_distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    itinerary_start_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    itinerary_end_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    itinerary_waypoints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    car: Mapped["Car"] = relationship(back_populates="rentals")
    rental_type: Mapped["RentalType"] = relationship(back_populates="rentals")

    def __repr__(self):
        return f"<Rental(id={self.id}, customer='{self.customer_name}', status='{self.status}')>"


class User(Base):
    """Client connecté via Google OAuth."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    google_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    picture: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


# =============================================================================
# DONNÉES INITIALES
# =============================================================================

def get_initial_cities() -> list[dict]:
    return [
        {"name": "Analakely", "latitude": -18.9056, "longitude": 47.5267},
        {"name": "Anosy", "latitude": -18.9142, "longitude": 47.5217},
        {"name": "Ivandry", "latitude": -18.8683, "longitude": 47.5250},
        {"name": "Andraharo", "latitude": -18.8708, "longitude": 47.5083},
        {"name": "Tanjombato", "latitude": -18.9567, "longitude": 47.5222},
        {"name": "Ambohipo", "latitude": -18.9225, "longitude": 47.5500},
    ]


def get_initial_rental_types() -> list[dict]:
    return [
        {"name": "Journalière", "duration_days": 1, "price_multiplier": 1.0, "discount_percent": 0},
        {"name": "Hebdomadaire", "duration_days": 7, "price_multiplier": 6.0, "discount_percent": 5},
        {"name": "Mensuelle", "duration_days": 30, "price_multiplier": 25.0, "discount_percent": 10},
        {"name": "Week-end", "duration_days": 3, "price_multiplier": 2.5, "discount_percent": 0},
    ]


def get_initial_cars() -> list[dict]:
    return [
        {
            "brand": "Toyota", "model": "Yaris", "year": 2023,
            "plate_number": "1234 TANA", "daily_price": 25000.0, "seats": 5,
            "image_url": "/assets/Gemini.png", "description": "Parfaite pour la ville, économique et fiable."
        },
        {
            "brand": "Renault", "model": "Duster", "year": 2022,
            "plate_number": "5678 TANA", "daily_price": 45000.0, "seats": 5,
            "image_url": "/assets/Gemini.png", "description": "SUV compact idéal pour les routes malgaches."
        },
        {
            "brand": "Mercedes", "model": "Classe E", "year": 2023,
            "plate_number": "9999 TANA", "daily_price": 120000.0, "seats": 5,
            "image_url": "/assets/Gemini.png", "description": "Confort et élégance pour vos occasions spéciales."
        },
    ]
