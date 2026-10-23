"""Orígenes del frontend autorizados a llamar a la API (CORS), leídos del entorno.

- CORS_ALLOWED_ORIGINS: lista separada por comas de orígenes exactos (https://sitio.vercel.app).
- CORS_ALLOWED_ORIGIN_REGEX: expresión regular opcional para aceptar varias direcciones del mismo
  proyecto de Vercel (cada rama y cada despliegue tiene la suya), p. ej.
  ^https://frontend(-[a-z0-9-]+)?-gonpuri1\\.vercel\\.app$
"""
import os
import re

from django.core.exceptions import ImproperlyConfigured


def desde_entorno(env=os.environ):
    origenes = [o.strip() for o in env.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    patron = env.get("CORS_ALLOWED_ORIGIN_REGEX", "").strip() or None
    if patron:
        try:
            re.compile(patron)
        except re.error as error:
            raise ImproperlyConfigured(f"CORS_ALLOWED_ORIGIN_REGEX no es una expresión regular válida: {error}") from error
    return origenes, patron


def opciones_fastapi(origenes, patron):
    """Argumentos de CORSMiddleware de FastAPI (el CORS de Django no alcanza a sus rutas)."""
    return {
        "allow_origins": origenes,
        "allow_origin_regex": patron,
        "allow_methods": ["*"],
        "allow_headers": ["authorization", "content-type"],
    }
