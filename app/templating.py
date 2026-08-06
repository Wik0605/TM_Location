from fastapi.templating import Jinja2Templates

from app.csrf import csrf_input, get_or_create_csrf_token

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["csrf_input"] = csrf_input
templates.env.globals["csrf_token"] = get_or_create_csrf_token
