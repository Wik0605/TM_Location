import io
from pathlib import Path
from PIL import Image

IMAGE_MAX_WIDTH = 1280
IMAGE_MAX_PIXELS = 24_000_000
IMAGE_WEBP_QUALITY = 82

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS


def save_optimized_image(raw: bytes, dest: Path) -> None:
    with Image.open(io.BytesIO(raw)) as im:
        if im.format not in ALLOWED_FORMATS:
            raise ValueError("Format d'image non autorisé.")
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        if im.width > IMAGE_MAX_WIDTH:
            ratio = IMAGE_MAX_WIDTH / im.width
            im = im.resize(
                (IMAGE_MAX_WIDTH, int(im.height * ratio)), Image.LANCZOS
            )
        im.save(dest, "WEBP", quality=IMAGE_WEBP_QUALITY, method=6)
