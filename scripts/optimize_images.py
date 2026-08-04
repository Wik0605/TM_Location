"""
Optimise toutes les images existantes dans static/uploads/.

Pour chaque image (PNG/JPG/JPEG) :
- Redimensionne à MAX_WIDTH px de large (garde les proportions).
- Genere une version .webp a cote (qualite 82).
- Conserve l'original comme fallback.

Usage : python scripts/optimize_images.py
Sans risque : re-exécutable, saute les .webp déjà présents.
"""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "static" / "uploads"

MAX_WIDTH = 1280
WEBP_QUALITY = 82
SOURCE_EXTS = {".png", ".jpg", ".jpeg"}


def optimize(path: Path) -> None:
    webp_path = path.with_suffix(".webp")
    if webp_path.exists():
        return

    with Image.open(path) as im:
        im = im.convert("RGB") if im.mode in ("RGBA", "P") else im
        if im.width > MAX_WIDTH:
            ratio = MAX_WIDTH / im.width
            new_size = (MAX_WIDTH, int(im.height * ratio))
            im = im.resize(new_size, Image.LANCZOS)
        im.save(webp_path, "WEBP", quality=WEBP_QUALITY, method=6)

    original_kb = path.stat().st_size // 1024
    webp_kb = webp_path.stat().st_size // 1024
    print(f"{path.relative_to(ROOT)}: {original_kb} KB -> {webp_kb} KB (webp)")


def main() -> None:
    if not UPLOAD_DIR.exists():
        print(f"Dossier absent : {UPLOAD_DIR}")
        return

    count = 0
    for path in UPLOAD_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in SOURCE_EXTS:
            try:
                optimize(path)
                count += 1
            except Exception as e:
                print(f"Erreur sur {path.name}: {e}")
    print(f"\nTermine. {count} image(s) traitee(s).")


if __name__ == "__main__":
    main()
