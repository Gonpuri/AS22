import io

import pytest
from fastapi.testclient import TestClient
from rest_framework.authtoken.models import Token
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from apps.horarios.models import BloqueHorario
from config.asgi import app

pytestmark = pytest.mark.django_db(transaction=True)
PREVIA = "/api/horarios/importar/previsualizar"
GUARDAR = "/api/horarios/importar"

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]


def _pdf(filas, traspuesta=False):
    """PDF con una grilla: encabezado de días y una fila por franja."""
    tabla = [["Hora", *DIAS], *filas]
    if traspuesta:
        tabla = [list(c) for c in zip(*tabla)]
    salida = io.BytesIO()
    t = Table(tabla)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    SimpleDocTemplate(salida, pagesize=landscape(A4)).build([t])
    return salida.getvalue()


FILAS = [
    ["07:30 a 08:30", "Matemática", "Contab.", "", "matematica", "Matemática"],
    ["Recreo", "Recreo", "Recreo", "Recreo", "Recreo", "Recreo"],
    ["08:40 a 09:40", "Matemática", "Contabilidad", "Fisica rara", "", ""],
]


@pytest.fixture
def api_admin(admin_user):
    return TestClient(app, headers={"Authorization": f"Token {Token.objects.get_or_create(user=admin_user)[0].key}"})


@pytest.fixture
def api_comun(common_user):
    return TestClient(app, headers={"Authorization": f"Token {Token.objects.get_or_create(user=common_user)[0].key}"})


def _subir(cliente, estructura, pdf):
    return cliente.post(PREVIA, data={"division": estructura["div"].pk}, files={"archivo": ("h.pdf", pdf, "application/pdf")})


def test_lee_la_grilla_y_reconoce_materias(api_admin, estructura):
    r = _subir(api_admin, estructura, _pdf(FILAS))
    assert r.status_code == 200
    bloques = r.json()["bloques"]
    assert len(bloques) == 7  # sin las celdas vacías ni los recreos
    mate, conta = estructura["matematica"].pk, estructura["contabilidad"].pk
    lunes = [b for b in bloques if b["dia"] == 1]
    assert [(b["hora_inicio"], b["hora_fin"], b["materia"]) for b in lunes] == [
        ("07:30:00", "08:30:00", mate), ("08:40:00", "09:40:00", mate)]
    assert next(b for b in bloques if b["dia"] == 2 and b["hora_inicio"] == "07:30:00")["materia"] == conta  # "Contab."
    assert next(b for b in bloques if b["dia"] == 4 and b["hora_inicio"] == "07:30:00")["materia"] == mate  # sin tildes
    desconocido = next(b for b in bloques if b["dia"] == 3 and b["hora_inicio"] == "08:40:00")
    assert desconocido["materia"] is None and desconocido["texto"] == "Fisica rara"
    assert BloqueHorario.objects.count() == 0  # previsualizar no guarda


def test_acepta_la_grilla_traspuesta(api_admin, estructura):
    r = _subir(api_admin, estructura, _pdf(FILAS, traspuesta=True))
    assert r.status_code == 200 and len(r.json()["bloques"]) == 7


def test_rechaza_archivos_que_no_son_un_horario(api_admin, estructura):
    assert _subir(api_admin, estructura, b"no soy un pdf").status_code == 422
    salida = io.BytesIO()
    SimpleDocTemplate(salida).build([Table([["a", "b"], ["c", "d"]])])
    r = _subir(api_admin, estructura, salida.getvalue())
    assert r.status_code == 422 and "No se encontró un horario" in r.json()["detail"]


def test_solo_el_administrador_importa(api_comun, estructura):
    assert _subir(api_comun, estructura, _pdf(FILAS)).status_code == 403
    cuerpo = {"division": estructura["div"].pk, "bloques": []}
    assert api_comun.post(GUARDAR, json=cuerpo).status_code == 403


def _revisado(e, dia=1, inicio="07:30:00", fin="08:30:00", materia="matematica"):
    return {"dia": dia, "hora_inicio": inicio, "hora_fin": fin, "materia": e[materia].pk}


def test_guarda_el_horario_revisado_sin_duplicar(api_admin, estructura):
    cuerpo = {"division": estructura["div"].pk,
              "bloques": [_revisado(estructura), _revisado(estructura, 2, materia="contabilidad")]}
    r = api_admin.post(GUARDAR, json=cuerpo)
    assert r.status_code == 201 and r.json() == {"creados": 2, "existentes": 0, "eliminados": 0}
    assert api_admin.post(GUARDAR, json=cuerpo).json() == {"creados": 0, "existentes": 2, "eliminados": 0}
    assert BloqueHorario.objects.count() == 2


def test_reemplazar_borra_los_bloques_anteriores(api_admin, estructura):
    api_admin.post(GUARDAR, json={"division": estructura["div"].pk, "bloques": [_revisado(estructura)]})
    r = api_admin.post(GUARDAR, json={"division": estructura["div"].pk, "reemplazar": True,
                                      "bloques": [_revisado(estructura, 3)]})
    assert r.json() == {"creados": 1, "existentes": 0, "eliminados": 1}
    assert list(BloqueHorario.objects.values_list("dia", flat=True)) == [3]


def test_si_un_bloque_es_invalido_no_se_guarda_nada(api_admin, estructura):
    api_admin.post(GUARDAR, json={"division": estructura["div"].pk, "bloques": [_revisado(estructura, 5)]})
    cuerpo = {"division": estructura["div"].pk, "reemplazar": True,
              "bloques": [_revisado(estructura), _revisado(estructura, 1, "08:00:00", "09:00:00"),
                          _revisado(estructura, 2, materia="biologia")]}
    r = api_admin.post(GUARDAR, json=cuerpo)
    assert r.status_code == 422 and "No se guardó nada" in r.json()["detail"]
    assert list(BloqueHorario.objects.values_list("dia", flat=True)) == [5]  # ni siquiera se borró lo anterior
