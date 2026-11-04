import io
from datetime import date

import pytest
from openpyxl import Workbook

from apps.rrhh.models import Personal

pytestmark = pytest.mark.django_db
PREVIA = "/api/rrhh/personal/importar-excel/previsualizar/"
GUARDAR = "/api/rrhh/personal/importar-excel/"


def _xlsx(filas, encabezado_en=1):
    libro = Workbook()
    hoja = libro.active
    for _ in range(encabezado_en - 1):
        hoja.append(["Planilla de personal 2026"])
    for fila in filas:
        hoja.append(fila)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


ENCABEZADO = ["Apellido", "Nombre", "D.N.I.", "CUIL", "Fecha de nacimiento", "Teléfono", "Email", "PAD"]


def _subir(cliente, contenido):
    return cliente.post(PREVIA, {"archivo": io.BytesIO(contenido)}, format="multipart")


def _archivo(contenido, nombre="personal.xlsx"):
    f = io.BytesIO(contenido)
    f.name = nombre
    return f


def test_propone_crear_y_actualizar_por_dni(admin_client):
    Personal.objects.create(apellido="Pérez", nombre="Juan", dni="30123456", telefono="111")
    contenido = _xlsx([
        ENCABEZADO,
        ["Pérez", "Juan", "30.123.456", "", date(1980, 5, 17), "222", "", "12,5"],
        ["Gómez", "Ana", 28999888.0, "27-28999888-4", "03/02/1985", "", "ana@mail.com", ""],
        ["Sin", "Dni", "", "", "", "", "", ""],
    ], encabezado_en=3)
    r = admin_client.post(PREVIA, {"archivo": _archivo(contenido)}, format="multipart")
    assert r.status_code == 200
    a, b, c = r.json()["filas"]
    assert (a["fila"], a["accion"], a["dni"]) == (4, "actualizar", "30123456")
    assert set(a["cambios"]) == {"telefono", "fecha_nacimiento", "pad"}
    assert (b["accion"], b["datos"]["fecha_nacimiento"], b["datos"]["email"]) == ("crear", "1985-02-03", "ana@mail.com")
    assert (c["accion"], c["errores"]) == ("error", ["Falta el DNI."])
    assert Personal.objects.count() == 1  # previsualizar no guarda


def test_reconoce_apellido_y_nombre_juntos_y_detecta_dni_repetido(admin_client):
    contenido = _xlsx([["Apellido y nombre", "DNI"], ["LOPEZ, MARIA ELENA", 20111222], ["OTRA, PERSONA", "20.111.222"]])
    filas = admin_client.post(PREVIA, {"archivo": _archivo(contenido)}, format="multipart").json()["filas"]
    assert filas[0]["datos"]["apellido"] == "LOPEZ" and filas[0]["datos"]["nombre"] == "MARIA ELENA"
    assert filas[1]["accion"] == "error" and "repetido en la fila 2" in filas[1]["errores"][0]


def test_dni_invalido_y_fecha_ilegible_son_errores_de_fila(admin_client):
    contenido = _xlsx([ENCABEZADO, ["A", "B", "123", "", "", "", "", ""], ["C", "D", "30111222", "", "ayer", "", "", ""]])
    a, b = admin_client.post(PREVIA, {"archivo": _archivo(contenido)}, format="multipart").json()["filas"]
    assert a["accion"] == "error" and "7 u 8 dígitos" in a["errores"][0]
    assert b["accion"] == "error" and "fecha no reconocida" in b["errores"][0]


def test_archivo_invalido_o_sin_dni(admin_client):
    assert admin_client.post(PREVIA, {"archivo": _archivo(b"no soy excel")}, format="multipart").status_code == 422
    r = admin_client.post(PREVIA, {"archivo": _archivo(_xlsx([["Apellido", "Nombre"], ["A", "B"]]))}, format="multipart")
    assert r.status_code == 422 and "DNI" in r.json()["detail"]
    assert admin_client.post(PREVIA, {}, format="multipart").status_code == 400


def test_guarda_creando_y_completando_sin_borrar_datos(admin_client):
    Personal.objects.create(apellido="Pérez", nombre="Juan", dni="30123456", telefono="111", email="p@x.com")
    r = admin_client.post(GUARDAR, {"filas": [
        {"dni": "30123456", "telefono": "222", "pad": "12.500"},
        {"dni": "28999888", "apellido": "Gómez", "nombre": "Ana"},
    ]}, format="json")
    assert r.status_code == 201 and r.json() == {"creados": 1, "actualizados": 1, "sin_cambios": 0}
    p = Personal.objects.get(dni="30123456")
    assert (p.telefono, p.email, str(p.pad)) == ("222", "p@x.com", "12.500")  # el email no se borró
    assert Personal.objects.get(dni="28999888").activo is True


def test_guardar_es_todo_o_nada(admin_client):
    r = admin_client.post(GUARDAR, {"filas": [
        {"dni": "28999888", "apellido": "Gómez", "nombre": "Ana"},
        {"dni": "30111222"},  # persona nueva sin apellido ni nombre
    ]}, format="json")
    assert r.status_code == 422
    assert Personal.objects.count() == 0


def test_solo_el_administrador_importa(common_client):
    assert common_client.post(GUARDAR, {"filas": []}, format="json").status_code == 403
    assert common_client.post(PREVIA, {"archivo": _archivo(_xlsx([ENCABEZADO]))}, format="multipart").status_code == 403
