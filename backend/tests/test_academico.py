import pytest

from apps.academico.models import Anio, Division, Materia, Orientacion

pytestmark = pytest.mark.django_db
BASE = "/api/academico"


def test_lectura_autenticada_escritura_admin(common_client, admin_client):
    assert common_client.get(f"{BASE}/orientaciones/").status_code == 200
    assert common_client.post(f"{BASE}/orientaciones/", {"nombre": "X"}).status_code == 403
    assert admin_client.post(f"{BASE}/orientaciones/", {"nombre": "X"}).status_code == 201


def test_orientacion_nombre_unico(admin_client):
    admin_client.post(f"{BASE}/orientaciones/", {"nombre": "Economía"})
    assert admin_client.post(f"{BASE}/orientaciones/", {"nombre": "Economía"}).status_code == 400


def test_anio_crud_y_validacion(admin_client):
    assert admin_client.post(f"{BASE}/anios/", {"numero": 0}).status_code == 400
    r = admin_client.post(f"{BASE}/anios/", {"numero": 1})
    assert r.status_code == 201
    assert admin_client.post(f"{BASE}/anios/", {"numero": 1}).status_code == 400
    assert admin_client.delete(f"{BASE}/anios/{r.data['id']}/").status_code == 204


def test_division_con_y_sin_orientacion(admin_client, estructura):
    r = admin_client.post(f"{BASE}/divisiones/", {"anio": estructura["a5"].pk, "nombre": "1ª"})
    assert r.status_code == 201 and r.data["orientacion"] is None and r.data["etiqueta"] == "5° 1ª"
    r = admin_client.post(
        f"{BASE}/divisiones/",
        {"anio": estructura["a5"].pk, "orientacion": estructura["nat"].pk, "nombre": "2ª"},
    )
    assert r.status_code == 201


def test_division_repetida_en_el_anio(admin_client, estructura):
    r = admin_client.post(f"{BASE}/divisiones/", {"anio": estructura["a4"].pk, "nombre": "1ª"})
    assert r.status_code == 400


def test_materia_asociada_a_anios_y_orientaciones(admin_client, estructura):
    r = admin_client.post(
        f"{BASE}/materias/",
        {"nombre": "Física", "anios": [estructura["a4"].pk], "orientaciones": [estructura["nat"].pk]},
    )
    assert r.status_code == 201
    assert r.data["anios"] == [estructura["a4"].pk] and r.data["orientaciones"] == [estructura["nat"].pk]
    r = admin_client.patch(f"{BASE}/materias/{r.data['id']}/", {"anios": []})
    assert r.data["anios"] == []


def test_materias_de_una_division(common_client, estructura):
    r = common_client.get(f"{BASE}/divisiones/{estructura['div'].pk}/materias/")
    assert sorted(m["nombre"] for m in r.data) == ["Contabilidad", "Matemática"]


def test_materias_de_division_sin_orientacion(estructura):
    div = Division.objects.create(anio=estructura["a4"], nombre="9ª")
    # solo las materias del año que no están restringidas a una orientación
    assert [m.nombre for m in div.materias()] == ["Matemática"]


def test_no_se_elimina_lo_que_tiene_dependencias(admin_client, estructura):
    assert admin_client.delete(f"{BASE}/anios/{estructura['a4'].pk}/").status_code == 409
    assert admin_client.delete(f"{BASE}/orientaciones/{estructura['eco'].pk}/").status_code == 409
    assert Anio.objects.filter(pk=estructura["a4"].pk).exists()


def test_eliminar_division_y_materia(admin_client, estructura):
    assert admin_client.delete(f"{BASE}/divisiones/{estructura['div'].pk}/").status_code == 204
    assert admin_client.delete(f"{BASE}/materias/{estructura['historia'].pk}/").status_code == 204
    assert not Division.objects.exists() and not Materia.objects.filter(nombre="Historia").exists()
    assert Orientacion.objects.count() == 2
