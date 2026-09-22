from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, DateTime, Text
from sqlmodel import SQLModel, Field, Relationship

from app.models.base import utcnow

if TYPE_CHECKING:
    from app.models.reservation import Location


class VoitureBase(SQLModel):
    nom: str = Field(max_length=100)
    description: str = Field(sa_column=Column(Text, nullable=False))
    consommation_carburant: float = Field(default=8.0)
    places: int = Field(default=5)


class Voiture(VoitureBase, table=True):
    __tablename__ = "voitures"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(max_length=140, unique=True, index=True)
    is_available: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, default=utcnow, nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False),
    )

    images: list["VoitureImage"] = Relationship(
        back_populates="voiture",
        sa_relationship_kwargs={
            "order_by": "VoitureImage.position",
            "cascade": "all, delete-orphan",
        },
    )
    types_location: list["TypeLocation"] = Relationship(
        back_populates="voiture",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    locations: list["Location"] = Relationship(back_populates="voiture")

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


class VoitureImage(SQLModel, table=True):
    __tablename__ = "voiture_images"

    id: Optional[int] = Field(default=None, primary_key=True)
    voiture_id: int = Field(foreign_key="voitures.id")
    url: str = Field(max_length=255)
    position: int = Field(default=0)

    voiture: Voiture = Relationship(back_populates="images")


class TypeLocation(SQLModel, table=True):
    __tablename__ = "types_location"

    id: Optional[int] = Field(default=None, primary_key=True)
    voiture_id: int = Field(foreign_key="voitures.id")
    nom: str = Field(max_length=100)
    prix: int

    voiture: Voiture = Relationship(back_populates="types_location")
    locations: list["Location"] = Relationship(back_populates="type_location")

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


class VoitureCreate(VoitureBase):
    pass


class VoitureUpdate(SQLModel):
    nom: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    consommation_carburant: Optional[float] = None
    places: Optional[int] = None
    is_available: Optional[bool] = None


class VoitureRead(VoitureBase):
    id: int
    slug: str
    is_available: bool
    created_at: datetime
    updated_at: datetime


class TypeLocationCreate(SQLModel):
    nom: str = Field(min_length=1, max_length=100)
    prix: int = Field(gt=0, lt=100_000_000)


class TypeLocationRead(SQLModel):
    id: int
    voiture_id: int
    nom: str
    prix: int
