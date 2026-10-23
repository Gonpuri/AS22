import json
from datetime import time

import pytest
from django.core.management import call_command

from apps.academico.models import Anio, Division, Materia, Orientacion
from apps.horarios.management.commands.cargar_horarios_iniciales import ARCHIVO
from apps.horarios.models import BloqueHorario

pytestmark = pytest.mark.django_db


def _cargar(capsys):
    call_command("cargar_horarios_iniciales")
    return capsys.readouterr().out


def _bloques(division, dia):
    return [
        (b.hora_inicio.strftime("%H:%M"), b.hora_fin.strftime("%H:%M"), b.materia.nombre)
        for b in BloqueHorario.objects.filter(division__nombre=division, dia=dia).select_related("materia")
    ]


def test_el_archivo_de_datos_tiene_cinco_cursos_de_24_bloques():
    datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    assert datos["anio"] == 1
    assert [c["division"] for c in datos["cursos"]] == ["2ª", "3ª", "4ª", "5ª", "6ª"]
    assert [len(c["bloques"]) for c in datos["cursos"]] == [24] * 5
    assert len(datos["materias"]) == 8


def test_carga_anio_divisiones_materias_y_bloques(capsys):
    salida = _cargar(capsys)
    assert "120 bloques creados" in salida and "OMITIDO" not in salida
    assert list(Anio.objects.values_list("numero", flat=True)) == [1]
    assert sorted(Division.objects.values_list("nombre", flat=True)) == ["2ª", "3ª", "4ª", "5ª", "6ª"]
    assert all(d.orientacion_id is None for d in Division.objects.all())  # ciclo básico
    assert Materia.objects.count() == 8
    assert BloqueHorario.objects.count() == 120
    anio = Anio.objects.get(numero=1)
    assert all(anio in m.anios.all() for m in Materia.objects.all())


@pytest.mark.parametrize("division, dia, esperado", [
    # 1°2° (mañana): lunes con Educación Física en contraturno de las cinco franjas
    ("2ª", 1, [("07:30", "08:30", "Matemática"), ("08:30", "09:30", "Matemática"),
               ("09:40", "10:40", "Prácticas del lenguaje"), ("10:45", "11:45", "Prácticas del lenguaje"),
               ("11:45", "12:45", "Educación Física")]),
    # 1°3° (tarde)
    ("3ª", 3, [("10:00", "11:00", "Educación Física"), ("13:00", "14:00", "Matemática"),
               ("14:00", "15:00", "Matemática"), ("15:10", "16:10", "Ciencias Naturales"),
               ("16:15", "17:15", "Ciencias Naturales"), ("17:15", "18:15", "Construcción de la ciudadanía")]),
    # 1°6° (mañana): viernes
    ("6ª", 5, [("07:30", "08:30", "Educación Artística"), ("08:30", "09:30", "Educación Artística"),
               ("09:40", "10:40", "Construcción de la ciudadanía"), ("10:45", "11:45", "Construcción de la ciudadanía"),
               ("11:45", "12:45", "Matemática"), ("12:45", "13:45", "Educación Física")]),
])
def test_horarios_cargados_coinciden_con_el_excel(capsys, division, dia, esperado):
    _cargar(capsys)
    assert sorted(_bloques(division, dia)) == sorted(esperado)


def test_es_idempotente(capsys):
    _cargar(capsys)
    salida = _cargar(capsys)
    assert "0 bloques creados, 120 ya existían" in salida
    assert BloqueHorario.objects.count() == 120 and Materia.objects.count() == 8 and Division.objects.count() == 5


def test_reutiliza_materias_y_divisiones_existentes_aunque_se_llamen_distinto(capsys):
    anio = Anio.objects.create(numero=1)
    naturales = Materia.objects.create(nombre="Cs Naturales")
    matematica = Materia.objects.create(nombre="MATEMATICA")
    otra = Division.objects.create(anio=anio, nombre="2")
    _cargar(capsys)
    assert Materia.objects.filter(nombre__icontains="natural").count() == 1
    assert Materia.objects.filter(nombre__icontains="matem").count() == 1
    assert Materia.objects.count() == 8
    assert Division.objects.count() == 5 and Division.objects.filter(nombre="2ª").count() == 0
    assert BloqueHorario.objects.filter(materia=naturales, division=otra).exists()
    assert BloqueHorario.objects.filter(materia=matematica).exists()
    assert anio in naturales.anios.all()


def test_un_bloque_que_se_superpone_se_omite_sin_cortar_la_carga(capsys):
    anio = Anio.objects.create(numero=1)
    division = Division.objects.create(anio=anio, nombre="2ª")
    lengua = Materia.objects.create(nombre="Lengua")
    lengua.anios.add(anio)
    BloqueHorario.objects.create(division=division, materia=lengua, dia=1, hora_inicio=time(7, 30), hora_fin=time(8, 30))
    salida = _cargar(capsys)
    assert "OMITIDO" in salida and "se superpone" in salida
    assert BloqueHorario.objects.filter(division=division).count() == 24 - 1 + 1  # el lunes 7:30 quedó como estaba
    assert BloqueHorario.objects.count() == 120 - 1 + 1


def test_una_materia_restringida_a_otra_orientacion_se_informa(capsys):
    anio = Anio.objects.create(numero=1)
    eco = Orientacion.objects.create(nombre="Economía")
    m = Materia.objects.create(nombre="Matemática")
    m.orientaciones.add(eco)
    salida = _cargar(capsys)
    assert "no corresponde al año/orientación" in salida
    assert not BloqueHorario.objects.filter(materia=m).exists()
    assert BloqueHorario.objects.exclude(materia=m).count() > 0 and anio.materias.count() == 8


def test_condicionado_solo_con_la_variable(monkeypatch, capsys):
    monkeypatch.delenv("CARGAR_HORARIOS_INICIALES", raising=False)
    call_command("cargar_horarios_iniciales", "--condicionado")
    assert not BloqueHorario.objects.exists()
    monkeypatch.setenv("CARGAR_HORARIOS_INICIALES", "1")
    call_command("cargar_horarios_iniciales", "--condicionado")
    assert BloqueHorario.objects.count() == 120


@pytest.mark.django_db(transaction=True)  # TestClient ejecuta los endpoints en otro hilo
def test_la_grilla_muestra_lo_cargado(capsys):
    from django.contrib.auth import get_user_model
    from fastapi.testclient import TestClient
    from rest_framework.authtoken.models import Token

    from config.asgi import app

    _cargar(capsys)
    usuario = get_user_model().objects.create_user("u", password="clave-segura-123")
    token = Token.objects.create(user=usuario).key
    division = Division.objects.get(nombre="3ª")
    r = TestClient(app).get(
        "/api/horarios/grilla", params={"division": division.pk}, headers={"Authorization": f"Token {token}"}
    )
    assert r.status_code == 200 and len(r.json()["bloques"]) == 24
    assert r.json()["division"]["anio"] == 1 and r.json()["division"]["orientacion"] is None


def test_los_cursos_quedan_con_el_turno_del_excel(capsys):
    _cargar(capsys)
    turnos = dict(Division.objects.values_list("nombre", "turno"))
    assert turnos == {"2ª": "manana", "3ª": "tarde", "4ª": "tarde", "5ª": "tarde", "6ª": "manana"}


def test_completa_el_turno_de_divisiones_existentes_sin_pisar_el_que_ya_tienen(capsys):
    anio = Anio.objects.create(numero=1)
    sin_turno = Division.objects.create(anio=anio, nombre="2")
    con_turno = Division.objects.create(anio=anio, nombre="3", turno="vespertino")
    salida = _cargar(capsys)
    sin_turno.refresh_from_db()
    con_turno.refresh_from_db()
    assert sin_turno.turno == "manana" and con_turno.turno == "vespertino"
    assert "turno completado en 1 divisiones" in salida
