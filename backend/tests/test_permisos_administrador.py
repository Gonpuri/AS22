import pytest
from django.contrib.auth import get_user_model
from fastapi.testclient import TestClient
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from config.asgi import app

CLAVE = "Clave-Segura-123"
USUARIOS = "/api/administracion/usuarios/"


def _cliente(**permisos):
    usuario = get_user_model().objects.create_user("u" + "".join(permisos) or "u", password=CLAVE, **permisos)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=usuario).key}")
    return c, usuario


@pytest.fixture
def staff(db):
    return _cliente(is_staff=True)[0]


@pytest.fixture
def superusuario_sin_staff(db):
    return _cliente(is_superuser=True)[0]


@pytest.fixture
def comun(db):
    return _cliente()[0]


@pytest.mark.django_db
@pytest.mark.parametrize("quien, puede", [("staff", True), ("superusuario_sin_staff", True), ("comun", False)])
def test_administracion_de_usuarios_solo_para_administradores(request, quien, puede):
    cliente = request.getfixturevalue(quien)
    assert (cliente.get(USUARIOS).status_code == 200) is puede
    assert (cliente.post(USUARIOS, {"username": "nuevo", "password": CLAVE}).status_code == 201) is puede


@pytest.mark.django_db
@pytest.mark.parametrize("quien, puede", [("staff", True), ("superusuario_sin_staff", True), ("comun", False)])
@pytest.mark.parametrize("recurso, datos", [
    ("/api/academico/orientaciones/", {"nombre": "Economía"}),
    ("/api/academico/anios/", {"numero": 1}),
    ("/api/rrhh/personal/", {"apellido": "Pérez", "nombre": "Ana", "dni": "30123456"}),
])
def test_solo_los_administradores_modifican(request, quien, puede, recurso, datos):
    assert (request.getfixturevalue(quien).post(recurso, datos).status_code == 201) is puede


@pytest.mark.django_db
def test_cualquier_usuario_autenticado_consulta_la_estructura_para_armar_horarios(comun):
    # la lectura sigue abierta: las pantallas de Horarios y Consulta necesitan cursos y materias
    for recurso in ("orientaciones", "anios", "divisiones", "materias"):
        assert comun.get(f"/api/academico/{recurso}/").status_code == 200
    assert APIClient().get("/api/academico/materias/").status_code == 401


@pytest.mark.django_db
def test_yo_informa_si_es_superusuario(superusuario_sin_staff, comun):
    assert superusuario_sin_staff.get("/api/auth/yo/").data["is_superuser"] is True
    assert comun.get("/api/auth/yo/").data["is_superuser"] is False


@pytest.mark.django_db
def test_no_se_puede_crear_un_superusuario_desde_la_api(staff):
    r = staff.post(USUARIOS, {"username": "intruso", "password": CLAVE, "is_superuser": True})
    assert r.status_code == 201 and r.data["is_superuser"] is False
    assert not get_user_model().objects.get(username="intruso").is_superuser


@pytest.mark.django_db(transaction=True)  # TestClient ejecuta los endpoints en otro hilo
@pytest.mark.parametrize("permisos, puede", [({"is_staff": True}, True), ({"is_superuser": True}, True), ({}, False)])
def test_horarios_de_fastapi_usa_la_misma_regla(permisos, puede):
    usuario = get_user_model().objects.create_user("h", password=CLAVE, **permisos)
    token = Token.objects.create(user=usuario).key
    r = TestClient(app).post(
        "/api/horarios/bloques",
        json={"division": 1, "materia": 1, "dia": 1, "hora_inicio": "07:30", "hora_fin": "08:30"},
        headers={"Authorization": f"Token {token}"},
    )
    # sin permiso: 403; con permiso llega a validar (la división no existe: 422), nunca 403
    assert (r.status_code != 403) is puede
