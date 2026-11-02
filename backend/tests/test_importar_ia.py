import io

import pytest
from fastapi.testclient import TestClient
from rest_framework.authtoken.models import Token
from reportlab.pdfgen import canvas

from apps.academico.models import Anio, Division, Materia, Orientacion
from apps.horarios import importar_ia
from apps.horarios.models import BloqueHorario
from config.asgi import app

pytestmark = pytest.mark.django_db(transaction=True)
LEER = "/api/horarios/importar/pdf/leer"
CURSOS = "/api/horarios/importar/cursos"


def _pdf(paginas=2):
    salida = io.BytesIO()
    c = canvas.Canvas(salida)
    for i in range(paginas):
        c.drawString(100, 700, f"pagina {i + 1}")
        c.showPage()
    c.save()
    return salida.getvalue()


LEIDO = {
    "encabezado": {"anio": 4, "division": "1ª", "turno": "tarde", "modalidad": "Comunicación", "preceptor": "X"},
    "franjas": [
        {"desde": "13:00", "hasta": "14:00", "dias": ["Matemática Ciclo Superior", "Inglés", "", "", ""]},
        {"desde": "14:00", "hasta": "15:00", "dias": ["Matemática Ciclo Superior", "Inglés", "", "", ""]},
        {"desde": "15:10", "hasta": "ilegible", "dias": ["Biología", "", "", "", ""]},
    ],
    "educacion_fisica": [{"dia": 1, "desde": "9:00", "hasta": "10:00"}],
}


@pytest.fixture
def api_admin(admin_user):
    return TestClient(app, headers={"Authorization": f"Token {Token.objects.get_or_create(user=admin_user)[0].key}"})


@pytest.fixture
def api_comun(common_user):
    return TestClient(app, headers={"Authorization": f"Token {Token.objects.get_or_create(user=common_user)[0].key}"})


@pytest.fixture
def ia(monkeypatch):
    pedidos = []
    monkeypatch.setattr(importar_ia, "_consultar", lambda pagina_pdf: pedidos.append(pagina_pdf) or LEIDO)
    return pedidos


def _leer(cliente, pagina=1, pdf=None):
    return cliente.post(LEER, data={"pagina": pagina}, files={"archivo": ("h.pdf", pdf or _pdf(), "application/pdf")})


def test_lee_una_pagina_y_propone_los_bloques(api_admin, ia):
    mate = Materia.objects.create(nombre="Matemática Ciclo Superior")
    Materia.objects.create(nombre="Matemática")  # no debe confundirse con la anterior
    r = _leer(api_admin, 2)
    assert r.status_code == 200
    datos = r.json()
    assert (datos["paginas"], datos["pagina"]) == (2, 2)
    curso = datos["curso"]
    assert (curso["anio"], curso["division"], curso["turno"], curso["modalidad"]) == (4, "1ª", "tarde", "Comunicación")
    assert curso["division_id"] is None
    lunes = [b for b in curso["bloques"] if b["dia"] == 1]
    assert [(b["hora_inicio"], b["materia"], b["materia_nombre"]) for b in lunes] == [
        ("09:00:00", None, "Educación Física"),
        ("13:00:00", mate.pk, "Matemática Ciclo Superior"),
        ("14:00:00", mate.pk, "Matemática Ciclo Superior"),
    ]
    assert [b["materia_nombre"] for b in curso["bloques"] if b["dia"] == 2] == ["Inglés", "Inglés"]
    assert len(curso["advertencias"]) == 1 and "ilegible" in curso["advertencias"][0]
    assert len(ia) == 1  # a la IA se le envía solo la página pedida


def test_detecta_la_division_existente(api_admin, ia):
    div = Division.objects.create(anio=Anio.objects.create(numero=4), nombre="1°", turno="tarde")
    assert _leer(api_admin).json()["curso"]["division_id"] == div.pk


def test_pagina_inexistente_y_archivo_invalido(api_admin, ia):
    assert _leer(api_admin, 5).status_code == 422
    assert _leer(api_admin, 1, b"no soy un pdf").status_code == 422


def test_error_de_la_ia_es_un_502(api_admin, monkeypatch):
    def falla(_):
        raise importar_ia.ErrorIa("sin clave")
    monkeypatch.setattr(importar_ia, "_consultar", falla)
    r = _leer(api_admin)
    assert r.status_code == 502 and r.json()["detail"] == "sin clave"


def test_solo_el_administrador_lee_e_importa(api_comun, ia):
    assert _leer(api_comun).status_code == 403
    assert api_comun.post(CURSOS, json={"cursos": []}).status_code == 403
    assert ia == []


def _curso(**extra):
    return {"anio": 4, "division": "1ª", "turno": "tarde", "modalidad": "Comunicación", "bloques": [
        {"dia": 1, "hora_inicio": "13:00:00", "hora_fin": "14:00:00", "materia": None, "materia_nombre": "Matemática Ciclo Superior"},
        {"dia": 2, "hora_inicio": "13:00:00", "hora_fin": "14:00:00", "materia": None, "materia_nombre": "Inglés"},
    ], **extra}


def test_importa_creando_division_orientacion_y_materias(api_admin):
    r = api_admin.post(CURSOS, json={"cursos": [_curso()]})
    assert r.status_code == 201
    assert r.json() == {"creados": 2, "existentes": 0, "eliminados": 0, "divisiones_creadas": 1, "materias_creadas": 2}
    div = Division.objects.get()
    assert (div.anio.numero, div.nombre, div.turno, div.orientacion.nombre) == (4, "1ª", "tarde", "Comunicación")
    assert BloqueHorario.objects.count() == 2
    assert div.materias().count() == 2  # las materias quedan habilitadas para la división


def test_reimportar_no_duplica_y_reutiliza_materias_y_division(api_admin):
    api_admin.post(CURSOS, json={"cursos": [_curso()]})
    r = api_admin.post(CURSOS, json={"cursos": [_curso()]})
    assert r.json() == {"creados": 0, "existentes": 2, "eliminados": 0, "divisiones_creadas": 0, "materias_creadas": 0}
    assert Materia.objects.count() == 2 and Division.objects.count() == 1


def test_una_materia_de_otra_orientacion_se_habilita_en_la_nueva(api_admin):
    eco = Orientacion.objects.create(nombre="Economía y Administración")
    conta = Materia.objects.create(nombre="Derecho")
    conta.orientaciones.add(eco)
    curso = _curso(modalidad="Comunicación")
    curso["bloques"] = [{"dia": 1, "hora_inicio": "13:00:00", "hora_fin": "14:00:00", "materia": conta.pk, "materia_nombre": "Derecho"}]
    assert api_admin.post(CURSOS, json={"cursos": [curso]}).status_code == 201
    assert set(conta.orientaciones.values_list("nombre", flat=True)) == {"Economía y Administración", "Comunicación"}


def test_todo_o_nada_entre_cursos(api_admin):
    malo = _curso(division="2ª")
    malo["bloques"].append({"dia": 1, "hora_inicio": "13:30:00", "hora_fin": "14:30:00", "materia": None, "materia_nombre": "Inglés"})
    r = api_admin.post(CURSOS, json={"cursos": [_curso(), malo]})
    assert r.status_code == 422 and "No se guardó nada" in r.json()["detail"] and "superpone" in r.json()["detail"]
    assert (Division.objects.count(), Materia.objects.count(), BloqueHorario.objects.count(), Orientacion.objects.count()) == (0, 0, 0, 0)


def test_sin_clave_de_anthropic_responde_un_error_claro(api_admin, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = _leer(api_admin)
    assert r.status_code == 502 and "ANTHROPIC_API_KEY" in r.json()["detail"]
