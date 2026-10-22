"""Punto de entrada ASGI.

FastAPI es la aplicación principal: sirve los módulos que definen `api.py` (con un `router`)
y delega todo lo demás en Django REST Framework, montado en la raíz.
Ejecutar con:  uvicorn config.asgi:app
"""
import os
from importlib import import_module
from importlib.util import find_spec

from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi = get_asgi_application()  # inicializa Django (apps y modelos) antes de importar los routers

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app = FastAPI(title="Sistema Escolar", docs_url="/api/docs", openapi_url="/api/openapi.json")

# El CORS de Django (corsheaders) no alcanza a las rutas de FastAPI: se configura también acá.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["authorization", "content-type"],
)

for _modulo in settings.MODULOS:
    if find_spec(f"apps.{_modulo}.api"):
        app.include_router(import_module(f"apps.{_modulo}.api").router, prefix=f"/api/{_modulo}")

app.mount("/", django_asgi)
application = app
