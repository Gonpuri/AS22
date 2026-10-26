from datetime import time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from rest_framework.authtoken.models import Token

from apps.academico.models import Division
from apps.horarios.models import BloqueHorario
from apps.horarios.services import mayor_pad_por_bloque
from apps.rrhh.models import AsignacionDocente, Designacion, Personal
from config.asgi import app


def _bloque(division, materia, dia, inicio, fin):
    return BloqueHorario.objects.create(
        division=division, materia=materia, dia=dia, hora_inicio=time(*inicio), hora_fin=time(*fin)
    )


def _docente(division, materia, apellido, dni, pad, *, activo=True, categoria="profesor", situacion="titular", turno="tarde"):
    persona = Personal.objects.create(apellido=apellido, nombre="Ana", dni=dni, pad=pad, activo=activo)
    designacion = Designacion.objects.create(personal=persona, categoria=categoria, turno=turno, situacion_revista=situacion)
    AsignacionDocente.objects.create(designacion=designacion, division=division, materia=materia)
    return persona


def _ranking(bloque):
    return [p.apellido for p in mayor_pad_por_bloque([bloque])[bloque.id]]


@pytest.fixture
def escuela(estructura):
    """Tres cursos de la tarde. Lunes 13:00-14:00 en el curso 4° 1ª; otros cursos dan clase a esa hora."""
    e = estructura
    e["curso2"] = Division.objects.create(anio=e["a5"], nombre="1ª", turno="tarde")
    e["curso3"] = Division.objects.create(anio=e["a5"], nombre="2ª", turno="tarde")
    e["mi_bloque"] = _bloque(e["div"], e["matematica"], 1, (13, 0), (14, 0))
    return e


@pytest.mark.django_db
def test_los_tres_con_mayor_pad_entre_quienes_dan_clase_en_ese_horario(escuela):
    e = escuela
    _docente(e["div"], e["matematica"], "Baja", "30000001", "10")  # en este curso y horario
    _bloque(e["curso2"], e["matematica"], 1, (13, 0), (14, 0))
    _docente(e["curso2"], e["matematica"], "Alta", "30000002", "30")  # otro curso, mismo horario
    _bloque(e["curso3"], e["historia"], 1, (13, 30), (14, 30))
    _docente(e["curso3"], e["historia"], "Media", "30000003", "20")  # se superpone parcialmente
    _bloque(e["curso3"], e["matematica"], 1, (13, 0), (14, 0))
    _docente(e["curso3"], e["matematica"], "Cuarta", "30000004", "5")  # quedaría cuarta
    assert _ranking(e["mi_bloque"]) == ["Alta", "Media", "Baja"]
    assert mayor_pad_por_bloque([e["mi_bloque"]])[e["mi_bloque"].id][0].pad == Decimal("30")


@pytest.mark.django_db
def test_no_cuentan_otro_dia_ni_otro_horario_sin_superposicion(escuela):
    e = escuela
    _docente(e["div"], e["matematica"], "Presente", "30000001", "10")
    _bloque(e["curso2"], e["historia"], 2, (13, 0), (14, 0))  # martes
    _docente(e["curso2"], e["historia"], "Martes", "30000002", "99")
    _bloque(e["curso3"], e["historia"], 1, (14, 0), (15, 0))  # empieza cuando termina el bloque
    _docente(e["curso3"], e["historia"], "Contiguo", "30000003", "98")
    _bloque(e["curso3"], e["matematica"], 1, (7, 30), (8, 30))  # a la mañana
    _docente(e["curso3"], e["matematica"], "Manana", "30000004", "97")
    assert _ranking(e["mi_bloque"]) == ["Presente"]


@pytest.mark.django_db
def test_sin_pad_inactivos_y_no_docentes_no_cuentan(escuela):
    e = escuela
    _docente(e["div"], e["matematica"], "Valido", "30000001", "10")
    _docente(e["div"], e["matematica"], "SinPad", "30000002", None)
    _docente(e["div"], e["matematica"], "Inactivo", "30000003", "99", activo=False)
    _docente(e["div"], e["matematica"], "Preceptor", "30000004", "98", categoria="preceptor")
    _docente(e["div"], e["matematica"], "Ematp", "30000005", "5", categoria="ematp")
    assert _ranking(e["mi_bloque"]) == ["Valido", "Ematp"]


@pytest.mark.django_db
def test_pad_cero_cuenta_y_el_empate_se_ordena_por_apellido(escuela):
    e = escuela
    _docente(e["div"], e["matematica"], "Zeta", "30000001", "15")
    _docente(e["div"], e["matematica"], "Alfa", "30000002", "15")
    _docente(e["div"], e["matematica"], "Cero", "30000003", "0")
    assert _ranking(e["mi_bloque"]) == ["Alfa", "Zeta", "Cero"]


@pytest.mark.django_db
def test_una_persona_con_varias_designaciones_aparece_una_sola_vez(escuela):
    e = escuela
    persona = _docente(e["div"], e["matematica"], "Doble", "30000001", "40")
    otra = Designacion.objects.create(personal=persona, categoria="profesor", turno="manana", situacion_revista="suplente")
    AsignacionDocente.objects.create(designacion=otra, division=e["div"], materia=e["matematica"])
    _bloque(e["curso2"], e["matematica"], 1, (13, 0), (14, 0))
    AsignacionDocente.objects.create(designacion=persona.designaciones.first(), division=e["curso2"], materia=e["matematica"])
    assert _ranking(e["mi_bloque"]) == ["Doble"]


@pytest.mark.django_db
def test_menos_de_tres_o_ninguno(escuela):
    e = escuela
    assert _ranking(e["mi_bloque"]) == []
    _docente(e["div"], e["matematica"], "Unica", "30000001", "1")
    assert _ranking(e["mi_bloque"]) == ["Unica"]


@pytest.mark.django_db
def test_varios_bloques_se_calculan_a_la_vez(escuela):
    e = escuela
    otro = _bloque(e["div"], e["contabilidad"], 3, (15, 10), (16, 10))
    _docente(e["div"], e["matematica"], "Lunes", "30000001", "10")
    _docente(e["div"], e["contabilidad"], "Miercoles", "30000002", "20")
    resultado = mayor_pad_por_bloque([e["mi_bloque"], otro])
    assert [p.apellido for p in resultado[e["mi_bloque"].id]] == ["Lunes"]
    assert [p.apellido for p in resultado[otro.id]] == ["Miercoles"]


@pytest.mark.django_db(transaction=True)  # TestClient ejecuta los endpoints en otro hilo
def test_la_grilla_informa_los_tres_con_mayor_pad(escuela, common_user):
    e = escuela
    _docente(e["div"], e["matematica"], "Baja", "30000001", "10.5")
    _bloque(e["curso2"], e["matematica"], 1, (13, 0), (14, 0))
    _docente(e["curso2"], e["matematica"], "Alta", "30000002", "30.125")
    token = Token.objects.create(user=common_user).key
    r = TestClient(app).get("/api/horarios/grilla", params={"division": e["div"].pk}, headers={"Authorization": f"Token {token}"})
    assert r.status_code == 200
    bloque = r.json()["bloques"][0]
    assert [(p["nombre"], p["pad"]) for p in bloque["mayor_pad"]] == [("Alta, Ana", "30.125"), ("Baja, Ana", "10.500")]
    assert {"personal_id", "nombre", "pad"} == set(bloque["mayor_pad"][0])
