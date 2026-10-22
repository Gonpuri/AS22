import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
User = get_user_model()


def test_crea_el_administrador_y_puede_iniciar_sesion(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "directora")
    monkeypatch.setenv("ADMIN_PASSWORD", "clave-segura-123")
    call_command("crear_admin")
    user = User.objects.get(username="directora")
    assert user.is_staff and user.is_superuser
    r = APIClient().post("/api/auth/login/", {"username": "directora", "password": "clave-segura-123"})
    assert r.status_code == 200


def test_sin_variables_no_hace_nada(monkeypatch):
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    call_command("crear_admin")
    assert not User.objects.exists()


def test_es_idempotente_y_no_pisa_la_clave(monkeypatch):
    User.objects.create_user("directora", password="la-clave-original")
    monkeypatch.setenv("ADMIN_USERNAME", "directora")
    monkeypatch.setenv("ADMIN_PASSWORD", "otra-clave-999")
    call_command("crear_admin")
    assert User.objects.count() == 1
    assert User.objects.get(username="directora").check_password("la-clave-original")
