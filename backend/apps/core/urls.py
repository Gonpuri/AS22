from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("usuarios", views.UsuarioViewSet, basename="usuario")

urlpatterns = [
    path("auth/login/", obtain_auth_token),
    path("auth/yo/", views.yo),
    path("modulos/", views.modulos),
    path("administracion/", include(router.urls)),
]
