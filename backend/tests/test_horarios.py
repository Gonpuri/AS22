import pytest
from fastapi.testclient import TestClient
from rest_framework.authtoken.models import Token

from config.asgi import app

# TestClient ejecuta los endpoints en otro hilo: se necesita la base fuera de la transacción de prueba.
pytestmark = pytest.mark.django_db(transaction=True)
URL = "/api/horarios/bloques"


@pytest.fixture
def api_admin(admin_user):
    return TestClient(app, headers={"Authorization": f"Token {Token.objects.get_or_create(user=admin_user)[0].key}"})


@pytest.fixture
def api_comun(common_user):
    return TestClient(app, headers={"Authorization": f"Token {Token.objects.get_or_create(user=common_user)[0].key}"})


def _bloque(e, materia="matematica", **extra):
    return {"division": e["div"].pk, "materia": e[materia].pk, "dia": 1,
            "hora_inicio": "07:30:00", "hora_fin": "08:10:00", **extra}


def test_sin_credenciales(estructura):
    assert TestClient(app).get(URL).status_code == 401
    assert TestClient(app, headers={"Authorization": "Token falso"}).get(URL).status_code == 401


def test_usuario_comun_solo_lee(api_comun, estructura):
    assert api_comun.get(URL).status_code == 200
    assert api_comun.post(URL, json=_bloque(estructura)).status_code == 403


def test_crear_y_listar(api_admin, estructura):
    r = api_admin.post(URL, json=_bloque(estructura))
    assert r.status_code == 201
    assert r.json()["materia"] == estructura["matematica"].pk
    assert len(api_admin.get(URL).json()) == 1
    assert api_admin.get(URL, params={"division": 999}).json() == []
    assert api_admin.get(f"{URL}/{r.json()['id']}").status_code == 200


def test_hora_fin_posterior(api_admin, estructura):
    r = api_admin.post(URL, json=_bloque(estructura, hora_fin="07:30:00"))
    assert r.status_code == 422


def test_dia_fuera_de_rango(api_admin, estructura):
    assert api_admin.post(URL, json=_bloque(estructura, dia=6)).status_code == 422


def test_materia_debe_corresponder_a_la_division(api_admin, estructura):
    for materia in ("biologia", "historia"):
        r = api_admin.post(URL, json=_bloque(estructura, materia=materia))
        assert r.status_code == 422 and "no corresponde" in r.json()["detail"]
    assert api_admin.post(URL, json=_bloque(estructura, materia="contabilidad")).status_code == 201


def test_division_o_materia_inexistente(api_admin, estructura):
    assert api_admin.post(URL, json={**_bloque(estructura), "division": 999}).status_code == 422
    assert api_admin.post(URL, json={**_bloque(estructura), "materia": 999}).status_code == 422


def test_no_se_superponen_bloques(api_admin, estructura):
    api_admin.post(URL, json=_bloque(estructura))
    r = api_admin.post(URL, json=_bloque(estructura, materia="contabilidad", hora_inicio="08:00:00", hora_fin="08:40:00"))
    assert r.status_code == 422 and "superpone" in r.json()["detail"]
    # contiguo, o en otro día, es válido
    assert api_admin.post(URL, json=_bloque(estructura, materia="contabilidad", hora_inicio="08:10:00", hora_fin="08:50:00")).status_code == 201
    assert api_admin.post(URL, json=_bloque(estructura, dia=2)).status_code == 201


def test_actualizar_puede_mantener_su_propio_horario(api_admin, estructura):
    pk = api_admin.post(URL, json=_bloque(estructura)).json()["id"]
    r = api_admin.put(f"{URL}/{pk}", json=_bloque(estructura, materia="contabilidad", hora_fin="08:20:00"))
    assert r.status_code == 200 and r.json()["hora_fin"] == "08:20:00"
    assert api_admin.put(f"{URL}/9999", json=_bloque(estructura)).status_code == 404


def test_eliminar(api_admin, estructura):
    pk = api_admin.post(URL, json=_bloque(estructura)).json()["id"]
    assert api_admin.delete(f"{URL}/{pk}").status_code == 204
    assert api_admin.get(f"{URL}/{pk}").status_code == 404


def test_division_con_horario_no_se_elimina(admin_client, api_admin, estructura):
    api_admin.post(URL, json=_bloque(estructura))
    assert admin_client.delete(f"/api/academico/divisiones/{estructura['div'].pk}/").status_code == 409


def test_django_se_sirve_desde_la_misma_app(admin_user):
    r = TestClient(app).post("/api/auth/login/", data={"username": "admin", "password": "clave-segura-123"})
    assert r.status_code == 200 and "token" in r.json()
