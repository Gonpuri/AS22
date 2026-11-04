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
    assert filas[0]["datos"]["apellido"] == "Lopez" and filas[0]["datos"]["nombre"] == "Maria Elena"
    assert not filas[0]["revisar_nombre"]
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


def test_formulario_de_google_con_nombre_y_apellido_en_una_columna(admin_client):
    """Formato del formulario real (datos inventados): «Nombre y Apellido» sin coma y en cualquier orden,
    el correo ayuda a decidir, PAD «-» y CUIL sin guiones."""
    Personal.objects.create(apellido="Ramos", nombre="Teodoro", dni="11222333")
    contenido = _xlsx([
        ["Marca temporal", "Nombre y Apellido", "DNI", "CUIL", "Email (abc)", "Teléfono celular",
         "Fecha de nacimiento", "Fecha de ingreso a la Escuela", "PAD", "Antigüedad en la docencia"],
        [date(2026, 11, 4), "Pedro gomez ", 10111222.0, 20101112229.0, "PGomez3@abc.gob.ar ", 2211234567.0,
         date(1978, 2, 21), date(2022, 3, 1), None, "15 años"],
        [date(2026, 11, 4), "Suarez Lucia", 10222333.0, 27102223334.0, "lusuarez@abc.gob.ar", 2217654321.0,
         date(1983, 8, 23), date(2020, 3, 2), 235.0, "16 años"],
        [date(2026, 11, 4), "Ana Duarte", 10333444.0, 27103334445.0, "aduarte@abc.gob.ar", None, None, None, "-", ""],
        [date(2026, 11, 4), "Teodoro Ramos Gil", 11222333.0, None, "tramos@abc.gob.ar", None, None, None, None, ""],
    ])
    r = admin_client.post(PREVIA, {"archivo": _archivo(contenido)}, format="multipart")
    assert r.status_code == 200
    gomez, suarez, duarte, ramos = r.json()["filas"]
    assert (gomez["accion"], gomez["datos"]["apellido"], gomez["datos"]["nombre"]) == ("crear", "Gomez", "Pedro")
    assert gomez["datos"]["cuil"] == "20-10111222-9" and gomez["datos"]["email"] == "pgomez3@abc.gob.ar"
    assert gomez["datos"]["telefono"] == "2211234567" and gomez["datos"]["fecha_ingreso"] == "2022-03-01"
    assert (suarez["datos"]["apellido"], suarez["datos"]["nombre"], suarez["datos"]["pad"]) == ("Suarez", "Lucia", "235.000")
    assert suarez["revisar_nombre"] is True  # apellido primero: se pide revisarlo
    assert duarte["accion"] == "crear" and "pad" not in duarte["datos"]  # «-» es sin PAD
    # una persona ya cargada conserva su nombre: la planilla solo aporta lo que falta
    assert ramos["accion"] == "actualizar" and "apellido" not in ramos["datos"] and ramos["revisar_nombre"] is False
