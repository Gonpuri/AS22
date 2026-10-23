import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
USUARIOS = "/api/administracion/usuarios/"
CLAVE = "Clave-Segura-123"


def _login(usuario, clave):
    return APIClient().post("/api/auth/login/", {"username": usuario, "password": clave})


def test_un_usuario_creado_desde_la_api_puede_iniciar_sesion(admin_client):
    r = admin_client.post(USUARIOS, {"username": "maria", "password": CLAVE, "is_staff": False, "is_active": True})
    assert r.status_code == 201
    guardada = get_user_model().objects.get(username="maria").password
    assert guardada != CLAVE and guardada.startswith("pbkdf2_")  # se guarda encriptada, nunca en texto
    login = _login("maria", CLAVE)
    assert login.status_code == 200 and login.data["token"]
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")
    yo = cliente.get("/api/auth/yo/")
    assert yo.status_code == 200 and yo.data["username"] == "maria" and yo.data["is_staff"] is False
    assert cliente.get("/api/academico/anios/").status_code == 200  # puede consultar
    assert cliente.post("/api/academico/anios/", {"numero": 7}).status_code == 403  # no modificar


def test_contrasena_con_caracteres_especiales_y_espacios(admin_client):
    clave = "Ñandú con ü & ñ - 2026 !"
    assert admin_client.post(USUARIOS, {"username": "jose", "password": clave}).status_code == 201
    assert _login("jose", clave).status_code == 200
    assert _login("jose", clave.strip().upper()).status_code == 400


def test_cambiar_la_contrasena_desde_la_api(admin_client):
    pk = admin_client.post(USUARIOS, {"username": "ana", "password": CLAVE}).data["id"]
    assert admin_client.put(USUARIOS + f"{pk}/", {"username": "ana", "password": "Otra-Clave-456"}).status_code == 200
    assert _login("ana", CLAVE).status_code == 400
    assert _login("ana", "Otra-Clave-456").status_code == 200


def test_editar_otros_datos_sin_enviar_contrasena_no_la_cambia(admin_client):
    pk = admin_client.post(USUARIOS, {"username": "ana", "password": CLAVE}).data["id"]
    assert admin_client.put(USUARIOS + f"{pk}/", {"username": "ana", "first_name": "Ana"}).status_code == 200
    assert _login("ana", CLAVE).status_code == 200


def test_un_usuario_inactivo_no_puede_iniciar_sesion(admin_client):
    admin_client.post(USUARIOS, {"username": "baja", "password": CLAVE, "is_active": False})
    assert _login("baja", CLAVE).status_code == 400


def test_el_usuario_distingue_mayusculas_y_la_clave_tambien(admin_client):
    admin_client.post(USUARIOS, {"username": "Maria", "password": CLAVE})
    assert _login("Maria", CLAVE).status_code == 200
    assert _login("maria", CLAVE).status_code == 400  # el nombre de usuario respeta mayúsculas


def test_no_se_puede_crear_un_usuario_sin_contrasena(admin_client):
    r = admin_client.post(USUARIOS, {"username": "sinclave"})
    assert r.status_code == 400 and not get_user_model().objects.filter(username="sinclave").exists()


def test_alta_con_los_opcionales_sin_completar_como_los_envia_el_formulario(admin_client):
    # el formulario manda "" en los textos que se dejan vacíos (con null el servidor responde 400)
    datos = {"username": "lucia", "password": CLAVE, "first_name": "", "last_name": "", "email": "",
             "is_staff": False, "is_active": True}
    r = admin_client.post(USUARIOS, datos, format="json")
    assert r.status_code == 201, r.data
    assert _login("lucia", CLAVE).status_code == 200


def test_el_servidor_rechaza_null_en_textos_opcionales(admin_client):
    r = admin_client.post(USUARIOS, {"username": "x", "password": CLAVE, "first_name": None}, format="json")
    assert r.status_code == 400 and "first_name" in r.data
