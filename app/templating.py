import datetime

from fastapi.templating import Jinja2Templates

from app.csrf import csrf_input, get_or_create_csrf_token


def _to_webp(url: str) -> str:
    if not url:
        return url
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        if url.endswith(ext):
            return url[: -len(ext)] + ".webp"
    return url


templates = Jinja2Templates(directory="app/templates")
templates.env.globals["csrf_input"] = csrf_input
templates.env.globals["csrf_token"] = get_or_create_csrf_token
templates.env.filters["current_year"] = lambda: datetime.datetime.now().year
templates.env.filters["to_webp"] = _to_webp
