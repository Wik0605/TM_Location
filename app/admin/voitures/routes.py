import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.voitures import service
from app.models.voiture import Voiture
from app.admin.voitures.forms import TypeLocationForm, VoitureCreateForm, VoitureUpdateForm
from app.shared.deps import get_db, require_csrf
from app.shared.security import require_admin
from app.shared.utils.images import (
    ALLOWED_MIME,
    lire_upload_limite,
    save_optimized_image,
)
from app.shared.utils.slug import slugify, unique_slug
from app.templating import templates


UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "static" / "uploads" / "voitures"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


router = APIRouter(
    prefix="/admin",
    tags=["admin-voitures"],
    dependencies=[Depends(require_admin), Depends(require_csrf)],
)


@router.get("/voitures", response_class=HTMLResponse)
async def admin_voitures(request: Request, db: AsyncSession = Depends(get_db)):
    voitures = await service.get_all_voitures(db)
    return templates.TemplateResponse("admin/voitures/voitures.html", {
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
    slug = await unique_slug(db, slugify(form.nom), Voiture)
    data = {
        "nom": form.nom,
        "slug": slug,
        "description": form.description,
        "places": form.places,
        "consommation_carburant": form.consommation_carburant,
        "is_available": True,
    }
    await service.create_voiture(db, data)
    voitures = await service.get_all_voitures(db)
    return templates.TemplateResponse("admin/voitures/partials/_voitures_grid.html", {
        "request": request,
        "voitures": voitures,
    })


@router.post("/voitures/{voiture_id}/delete", response_class=HTMLResponse)
async def delete_voiture(
    request: Request,
    voiture_id: int,
    db: AsyncSession = Depends(get_db),
):
    await service.delete_voiture(db, voiture_id)
    voitures = await service.get_all_voitures(db)
    return templates.TemplateResponse("admin/voitures/partials/_voitures_grid.html", {
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
    voiture = await service.update_voiture(db, voiture_id, data)
    return templates.TemplateResponse("admin/voitures/partials/_voiture_card.html", {
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
        if file.content_type not in ALLOWED_MIME:
            continue
        raw = await lire_upload_limite(file)
        if raw is None:
            continue
        filename = f"{uuid.uuid4().hex}.webp"
        dest = upload_dir / filename
        try:
            save_optimized_image(raw, dest)
        except Exception:
            continue
        url = f"/static/uploads/voitures/{voiture_id}/{filename}"
        await service.add_voiture_image(db, voiture_id, url)

    voiture = await service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/voitures/partials/_voiture_images.html", {
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
    await service.delete_voiture_image(db, image_id)
    voiture = await service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/voitures/partials/_voiture_images.html", {
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
    await service.add_type_location(db, voiture_id, form.nom, form.prix)
    voiture = await service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/voitures/partials/_types_location_list.html", {
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
    await service.delete_type_location(db, type_id)
    voiture = await service.get_voiture_by_id(db, voiture_id)
    return templates.TemplateResponse("admin/voitures/partials/_types_location_list.html", {
        "request": request,
        "voiture": voiture,
    })
