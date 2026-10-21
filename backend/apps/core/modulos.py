"""Registro de módulos funcionales.

Contrato para incorporar un módulo nuevo (p. ej. "alumnos"):
  1. Crear apps/<modulo>/ como app de Django (models, migrations).
  2. Agregarlo a settings.MODULOS.
  3. Exponer su API con alguno de estos archivos (ambos opcionales):
       - urls.py  -> rutas Django REST Framework, publicadas en /api/<modulo>/
       - api.py   -> `router` de FastAPI, publicado en /api/<modulo>/
No hace falta tocar config/urls.py ni config/asgi.py.
"""
from django.apps import apps
from django.conf import settings


def listar_modulos():
    return [
        {"nombre": nombre, "etiqueta": apps.get_app_config(nombre).verbose_name}
        for nombre in settings.MODULOS
    ]
