import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_login_devuelve_token(admin_user):
    r = APIClient().post("/api/auth/login/", {"username": "admin", "password": "clave-segura-123"})
    assert r.status_code == 200 and r.data["token"]


def test_login_con_clave_incorrecta(admin_user):
    r = APIClient().post("/api/auth/login/", {"username": "admin", "password": "mal"})
    assert r.status_code == 400


def test_yo_requiere_autenticacion(admin_client):
    assert APIClient().get("/api/auth/yo/").status_code == 401
    r = admin_client.get("/api/auth/yo/")
    assert r.data["username"] == "admin" and r.data["is_staff"] is True


def test_modulos_registrados(common_client):
    nombres = [m["nombre"] for m in common_client.get("/api/modulos/").data]
    assert nombres == ["academico", "horarios", "rrhh"]


def test_usuarios_solo_administrador(common_client, admin_client):
    assert common_client.get("/api/administracion/usuarios/").status_code == 403
    assert APIClient().get("/api/administracion/usuarios/").status_code == 401
    assert admin_client.get("/api/administracion/usuarios/").status_code == 200


def test_crear_usuario_con_clave_hasheada(admin_client):
    r = admin_client.post("/api/administracion/usuarios/", {"username": "nuevo", "password": "clave-segura-123"})
    assert r.status_code == 201 and "password" not in r.data
    user = get_user_model().objects.get(username="nuevo")
    assert user.check_password("clave-segura-123")


def test_crear_usuario_exige_clave_valida(admin_client):
    assert admin_client.post("/api/administracion/usuarios/", {"username": "x"}).status_code == 400
    assert admin_client.post("/api/administracion/usuarios/", {"username": "x", "password": "123"}).status_code == 400


def test_editar_usuario_cambia_clave_y_desactiva(admin_client, common_user):
    r = admin_client.patch(
        f"/api/administracion/usuarios/{common_user.pk}/", {"password": "otra-clave-456", "is_active": False}
    )
    assert r.status_code == 200
    common_user.refresh_from_db()
    assert common_user.check_password("otra-clave-456") and not common_user.is_active


def test_eliminar_usuario(admin_client, common_user):
    assert admin_client.delete(f"/api/administracion/usuarios/{common_user.pk}/").status_code == 204
