from datetime import time

import pytest

from apps.horarios.models import BloqueHorario
from apps.rrhh.models import AsignacionDocente, Designacion, Personal

pytestmark = pytest.mark.django_db
URL = "/api/consulta_docente/"
# Semana de prueba: lunes 19, martes 20, miércoles 21, jueves 22, viernes 23, sábado 24, domingo 25 de octubre de 2026.


def _bloque(e, materia, dia, inicio, fin):
    return BloqueHorario.objects.create(
        division=e["div"], materia=e[materia], dia=dia, hora_inicio=time(*inicio), hora_fin=time(*fin)
    )


def _docente(e, materia, cuil="20-30123456-7", dni="30123456", categoria="profesor", situacion="titular"):
    persona = Personal.objects.create(apellido="Nievas", nombre="Silvia", dni=dni, cuil=cuil)
    des = Designacion.objects.create(personal=persona, categoria=categoria, turno="tarde", situacion_revista=situacion)
    AsignacionDocente.objects.create(designacion=des, division=e["div"], materia=e[materia])
    return persona


@pytest.fixture
def escenario(estructura):
    _bloque(estructura, "matematica", 1, (13, 0), (14, 0))
    _bloque(estructura, "matematica", 1, (14, 0), (15, 0))
    _bloque(estructura, "contabilidad", 3, (15, 10), (16, 10))  # otra materia: no es de este docente
    _docente(estructura, "matematica")
    return estructura


def test_requiere_autenticacion(escenario):
    from rest_framework.test import APIClient
    assert APIClient().get(URL, {"cuil": "20301234567", "desde": "2026-10-19"}).status_code == 401


def test_dia_con_clases_muestra_curso_materia_y_horarios(common_client, escenario):
    r = common_client.get(URL, {"cuil": "20-30123456-7", "desde": "2026-10-19"})
    assert r.status_code == 200
    d = r.data
    assert d["tiene_clases"] is True and d["cursos_asignados"] == 1
    assert d["docente"]["apellido"] == "Nievas"
    assert len(d["dias"]) == 1 and d["dias"][0]["dia"] == "Lunes"
    assert d["dias"][0]["clases"] == [
        {"hora_inicio": "13:00", "hora_fin": "14:00", "curso": "4° 1ª", "materia": "Matemática", "situacion_revista": "Titular"},
        {"hora_inicio": "14:00", "hora_fin": "15:00", "curso": "4° 1ª", "materia": "Matemática", "situacion_revista": "Titular"},
    ]


def test_dia_sin_clases(common_client, escenario):
    r = common_client.get(URL, {"cuil": "20301234567", "desde": "2026-10-20"})  # martes
    assert r.status_code == 200 and r.data["tiene_clases"] is False
    assert r.data["dias"][0]["clases"] == []


def test_intervalo_incluye_cada_fecha_y_fines_de_semana_sin_clases(common_client, escenario):
    r = common_client.get(URL, {"cuil": "20301234567", "desde": "2026-10-19", "hasta": "2026-10-25"})
    assert [d["dia"] for d in r.data["dias"]] == ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    assert [bool(d["clases"]) for d in r.data["dias"]] == [True, False, False, False, False, False, False]


def test_el_intervalo_se_repite_semana_a_semana(common_client, escenario):
    r = common_client.get(URL, {"cuil": "20301234567", "desde": "2026-10-19", "hasta": "2026-11-02"})
    con_clases = [d["fecha"] for d in r.data["dias"] if d["clases"]]
    assert con_clases == ["2026-10-19", "2026-10-26", "2026-11-02"]


@pytest.mark.parametrize("cuil", ["20-30123456-7", "20 30123456 7", "20301234567"])
def test_cuil_con_o_sin_formato(common_client, escenario, cuil):
    assert common_client.get(URL, {"cuil": cuil, "desde": "2026-10-19"}).status_code == 200


def test_cuil_guardado_sin_guiones_tambien_se_encuentra(common_client, estructura):
    _bloque(estructura, "matematica", 1, (13, 0), (14, 0))
    _docente(estructura, "matematica", cuil="20301234567")
    assert common_client.get(URL, {"cuil": "20-30123456-7", "desde": "2026-10-19"}).data["tiene_clases"] is True


def test_cuil_inexistente(common_client, escenario):
    r = common_client.get(URL, {"cuil": "20-99999999-9", "desde": "2026-10-19"})
    assert r.status_code == 404 and "CUIL" in r.data["detail"]


def test_docente_sin_cursos_asignados(common_client, estructura):
    Personal.objects.create(apellido="Sin", nombre="Cursos", dni="30999999", cuil="27-30999999-1")
    r = common_client.get(URL, {"cuil": "27309999991", "desde": "2026-10-19"})
    assert r.status_code == 200 and r.data["tiene_clases"] is False and r.data["cursos_asignados"] == 0


def test_solo_cuentan_profesores_y_ematp(common_client, estructura):
    _bloque(estructura, "matematica", 1, (13, 0), (14, 0))
    _docente(estructura, "matematica", categoria="ematp", cuil="20-11111111-1", dni="11111111")
    assert common_client.get(URL, {"cuil": "20111111111", "desde": "2026-10-19"}).data["tiene_clases"] is True
    # una designación no docente con asignaciones cargadas por fuera de la API no da clases
    persona = Personal.objects.create(apellido="Pre", nombre="Ceptor", dni="22222222", cuil="20-22222222-2")
    des = Designacion.objects.create(personal=persona, categoria="preceptor", turno="tarde", situacion_revista="titular")
    AsignacionDocente.objects.create(designacion=des, division=estructura["div"], materia=estructura["matematica"])
    assert common_client.get(URL, {"cuil": "20222222222", "desde": "2026-10-19"}).data["tiene_clases"] is False


def test_titular_y_suplente_de_la_misma_materia_ven_los_bloques_con_su_situacion(common_client, escenario):
    _docente(escenario, "matematica", cuil="27-33333333-3", dni="33333333", situacion="suplente")
    r = common_client.get(URL, {"cuil": "27333333333", "desde": "2026-10-19"})
    assert {c["situacion_revista"] for c in r.data["dias"][0]["clases"]} == {"Suplente"}


def test_mismo_docente_en_dos_turnos_no_duplica_clases(common_client, escenario):
    persona = Personal.objects.get(cuil="20-30123456-7")
    des2 = Designacion.objects.create(personal=persona, categoria="profesor", turno="manana", situacion_revista="suplente")
    AsignacionDocente.objects.create(designacion=des2, division=escenario["div"], materia=escenario["matematica"])
    r = common_client.get(URL, {"cuil": "20301234567", "desde": "2026-10-19"})
    assert len(r.data["dias"][0]["clases"]) == 2


@pytest.mark.parametrize("params", [
    {"cuil": "123", "desde": "2026-10-19"},
    {"cuil": "20301234567"},
    {"cuil": "20301234567", "desde": "ayer"},
    {"cuil": "20301234567", "desde": "2026-10-20", "hasta": "2026-10-19"},
    {"cuil": "20301234567", "desde": "2026-01-01", "hasta": "2027-12-31"},
])
def test_parametros_invalidos(common_client, escenario, params):
    assert common_client.get(URL, params).status_code == 400
