from importlib import import_module
from importlib.util import find_spec

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Sistema Escolar - Administración"
admin.site.site_title = "Sistema Escolar"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
]

# Cada módulo que exponga apps/<modulo>/urls.py (Django REST Framework) se publica en /api/<modulo>/.
# Los módulos con apps/<modulo>/api.py (FastAPI) se montan en config/asgi.py.
for _modulo in settings.MODULOS:
    if find_spec(f"apps.{_modulo}.urls"):
        urlpatterns.append(path(f"api/{_modulo}/", include(import_module(f"apps.{_modulo}.urls"))))
