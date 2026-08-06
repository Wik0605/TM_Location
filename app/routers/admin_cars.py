from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pathlib import Path
import io
import uuid

from PIL import Image

from app.csrf import require_csrf
from app.database import get_db
from app.services import admin_service
from app.routers.admin_auth import require_admin
from app.schemas import VoitureCreateForm, VoitureUpdateForm, TypeLocationForm
from app.templating import templates

UPLOAD_DIR = Path(__file__).parent.parent.parent / "static" / "uploads" / "voitures"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_MAX_WIDTH = 1280
IMAGE_WEBP_QUALITY = 82
IMAGE_MAX_BYTES = 8 * 1024 * 1024
IMAGE_MAX_PIXELS = 40_000_000

Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS


def _save_optimized_image(raw: bytes, dest: Path) -> None:
    with Image.open(io.BytesIO(raw)) as im:
        im = im.convert("RGB") if im.mode in ("RGBA", "P") else im
        if im.width > IMAGE_MAX_WIDTH:
            ratio = IMAGE_MAX_WIDTH / im.width
            im = im.resize(
                (IMAGE_MAX_WIDTH, int(im.height * ratio)), Image.LANCZOS
            )
        im.save(dest, "WEBP", quality=IMAGE_WEBP_QUALITY, method=6)


async def _lire_upload_limite(file: UploadFile) -> bytes | None:
    raw = await file.read(IMAGE_MAX_BYTES + 1)
    if len(raw) > IMAGE_MAX_BYTES:
        return None
    return raw

router = APIRouter(
    prefix="/admin",
    tags=["admin-cars"],
    dependencies=[Depends(require_admin), Depends(require_csrf)],
)


@router.get("/voitures", response_class=HTMLResponse)
async def admin_voitures(request: Request, db: AsyncSession = Depends(get_db)):
    voitures = await admin_service.get_all_voitures(db)
    return templates.TemplateResponse("admin/voitures.html", {
        "request": request,
        "voitures": voitures,
        "active": "voitures",
    })


@router.post("/voitures/create", response_class=HTMLResponse)
async def create_voiture(
    request: Request,
    form: VoitureCreateForm = Depends(VoitureCreateForm.as_form),
    db: AsyncSession = Depends(get_db),
):
    data = {
        "nom": form.nom,
        "description": form.description,
        "places": form.places,
        "consommation_carburant": form.consommation_carburant,
        "is_available": True,
    }
    await admin_service.create_voiture(db, data)
    voitures = await admin_service.get_all_voitures(db)
    return templates.TemplateResponse("admin/partials/_voitures_grid.html", {
        "request": request,
        "voitures": voitures,
    })


@router.post("/voitures/{voiture_id}/delete", response_class=HTMLResponse)
async def delete_voiture(
    request: Request,
    voiture_id: int,
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_voiture(db, voiture_id)
    voitures = await admin_service.get_all_voitures(db)
    return templates.TemplateResponse("admin/partials/_voitures_grid.html", {
        "request": request,
        "voitures": voitures,
    })


@router.post("/voitures/{voiture_id}/edit", response_class=HTMLResponse)
async def edit_voiture(
    request: Request,
    voiture_id: int,
    form: VoitureUpdateForm = Depends(VoitureUpdateForm.as_form),
    db: AsyncSession = Depends(get_db),
):
    data = {
        "nom": form.nom if form.nom else None,
        "description": form.description if form.description is not None else None,
        "places": form.places,
        "consommation_carburant": form.consommation_carburant,
        "is_available": form.is_available == "on" if form.is_available is not None else None,
    }
    data = {k: v for k, v in data.items() if v is not None}
    voiture = await admin_service.update_voiture(db, voiture_id, data)
    return templates.TemplateResponse("admin/partials/_voiture_card.html", {
        "request": request,
        "voiture": voiture,
        "success": True,
    })


@router.post("/voitures/{voiture_id}/images", response_class=HTMLResponse)
async def add_voiture_images(
    request: Request,
    voiture_id: int,
    files: List[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    upload_dir = UPLOAD_DIR / str(voiture_id)
    upload_dir.mkdir(exist_ok=True)

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        raw = await _lire_upload_limite(file)
        if raw is None:
            continue
        filename = f"{uuid.uuid4().hex}.webp"
        dest = upload_dir / filename
        try:
            _save_optimized_image(raw, dest)
        except Exception:
            continue
        url = f"/static/uploads/voitures/{voiture_id}/{filename}"
        await admin_service.add_voiture_image(db, voiture_id, url)

    voiture = await admin_service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/partials/_voiture_images.html", {
        "request": request,
        "voiture": voiture,
    })


@router.post("/voitures/{voiture_id}/images/{image_id}/delete", response_class=HTMLResponse)
async def delete_voiture_image(
    request: Request,
    voiture_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_voiture_image(db, image_id)
    voiture = await admin_service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/partials/_voiture_images.html", {
        "request": request,
        "voiture": voiture,
    })


@router.post("/voitures/{voiture_id}/types/create", response_class=HTMLResponse)
async def add_type_location(
    request: Request,
    voiture_id: int,
    form: TypeLocationForm = Depends(TypeLocationForm.as_form),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.add_type_location(db, voiture_id, form.nom, form.prix)
    voiture = await admin_service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/partials/_types_location_list.html", {
        "request": request,
        "voiture": voiture,
    })


@router.post("/voitures/{voiture_id}/types/{type_id}/delete", response_class=HTMLResponse)
async def delete_type_location(
    request: Request,
    voiture_id: int,
    type_id: int,
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_type_location(db, type_id)
    voiture = await admin_service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/partials/_types_location_list.html", {
        "request": request,
        "voiture": voiture,
    })
