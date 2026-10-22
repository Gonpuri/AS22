import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.academico.models import Materia

pytestmark = pytest.mark.django_db


@pytest.fixture
def panel(db):
    user = get_user_model().objects.create_superuser("admin", password="clave-segura-123")
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.parametrize("modelo", [
    "academico_orientacion", "academico_anio", "academico_division", "academico_materia",
    "horarios_bloquehorario", "rrhh_personal", "rrhh_designacion", "rrhh_asignaciondocente",
])
def test_cada_modelo_se_puede_listar_y_crear_desde_el_panel(panel, modelo):
    assert panel.get(reverse(f"admin:{modelo}_changelist")).status_code == 200
    assert panel.get(reverse(f"admin:{modelo}_add")).status_code == 200


def test_login_del_panel_con_csrf_activo(db):
    get_user_model().objects.create_superuser("admin", password="clave-segura-123")
    c = Client(enforce_csrf_checks=True)
    pagina = c.get("/django-admin/login/")
    assert pagina.status_code == 200
    r = c.post("/django-admin/login/", {
        "username": "admin", "password": "clave-segura-123",
        "csrfmiddlewaretoken": c.cookies["csrftoken"].value, "next": "/django-admin/",
    })
    assert r.status_code == 302 and r["Location"] == "/django-admin/"


def test_usuario_sin_permisos_de_staff_no_entra(db):
    user = get_user_model().objects.create_user("comun", password="clave-segura-123")
    c = Client()
    c.force_login(user)
    r = c.get("/django-admin/")
    assert r.status_code == 302 and "/django-admin/login/" in r["Location"]


def test_alta_de_materia_con_anios_y_orientaciones_desde_el_panel(panel, estructura):
    r = panel.post(reverse("admin:academico_materia_add"), {
        "nombre": "Física", "anios": [estructura["a4"].pk], "orientaciones": [estructura["nat"].pk],
    })
    assert r.status_code == 302
    fisica = Materia.objects.get(nombre="Física")
    assert list(fisica.anios.all()) == [estructura["a4"]]
    assert list(fisica.orientaciones.all()) == [estructura["nat"]]
