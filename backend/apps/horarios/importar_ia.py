"""Lectura con IA (Claude, con visión) de los horarios en PDF escaneado: una página por curso.

Cada página trae arriba el curso, la división, el turno y la modalidad, y debajo la grilla de horarios.
El PDF se procesa de a una página por vez (la pantalla va pidiendo cada una) para no superar el tiempo
máximo de una petición. El resultado es una propuesta para revisar: nada se guarda desde acá.
"""
import base64
import io
import json
import os
import re
from datetime import time

import anthropic
from pypdf import PdfReader, PdfWriter

from apps.academico.models import Turno

from .importar_pdf import Buscador, ErrorPdf
from .services import clave_texto

MODELO = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5-5")
HORA = re.compile(r"^(\d{1,2}):(\d{2})$")

ESQUEMA = {
    "type": "object",
    "properties": {
        "encabezado": {
            "type": "object",
            "properties": {
                "anio": {"type": "integer", "description": "Curso (año): 1 a 6"},
                "division": {"type": "string", "description": "Número de división, por ejemplo «1ª»"},
                "turno": {"type": "string", "enum": [t.value for t in Turno]},
                "modalidad": {"type": "string", "description": "Modalidad u orientación; vacío si no figura"},
                "preceptor": {"type": "string", "description": "Preceptor/a; vacío si no figura"},
            },
            "required": ["anio", "division", "turno", "modalidad", "preceptor"],
            "additionalProperties": False,
        },
        "franjas": {
            "type": "array",
            "description": "Una por cada fila horaria de la grilla, de arriba hacia abajo",
            "items": {
                "type": "object",
                "properties": {
                    "desde": {"type": "string", "description": "HH:MM en 24 horas"},
                    "hasta": {"type": "string", "description": "HH:MM en 24 horas"},
                    "dias": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Exactamente 5 textos: materia de lunes, martes, miércoles, jueves y viernes ('' si la celda está vacía)",
                    },
                },
                "required": ["desde", "hasta", "dias"],
                "additionalProperties": False,
            },
        },
        "educacion_fisica": {
            "type": "array",
            "description": "Horarios de la fila «ED. FÍSICA» de la grilla (uno por cada día que tiene hora indicada)",
            "items": {
                "type": "object",
                "properties": {
                    "dia": {"type": "integer", "description": "1=lunes … 5=viernes"},
                    "desde": {"type": "string", "description": "HH:MM en 24 horas"},
                    "hasta": {"type": "string", "description": "HH:MM en 24 horas"},
                },
                "required": ["dia", "desde", "hasta"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["encabezado", "franjas", "educacion_fisica"],
    "additionalProperties": False,
}

INSTRUCCIONES = """Esta página es el horario escolar de un curso (foto escaneada). Transcribilo tal como está escrito, sin inventar nada.

- Encabezado: curso (año), división, turno (MAÑANA = manana, TARDE = tarde, VESPERTINO = vespertino), modalidad y preceptor/a.
- Grilla «HORARIO»: una franja por cada fila (columna «Horas»), con las materias de lunes a viernes. Las horas van en 24 horas con formato HH:MM (7:30 → 07:30; 13:00 queda 13:00).
- En cada celda escribí el NOMBRE COMPLETO de la materia, tal como figura en la tabla «MATERIAS» de la misma página, sin el código (como LIT o MCS) ni los números entre guiones. Si la celda dice «Obs. de Comun. Cultura y sociedad», buscá en la tabla «MATERIAS» su nombre completo y usá ese. Dejá '' en las celdas vacías.
- La fila «ED. FÍSICA» no es una franja: indica a qué hora tiene Educación Física cada día (por ejemplo «9:00 a 10:00 hs» bajo Lunes y Viernes). Ponela en educacion_fisica.
- Ignorá los profesores, las situaciones de revista y las anotaciones a mano."""


class ErrorIa(ValueError):
    pass


def _paginas(contenido: bytes) -> PdfReader:
    try:
        return PdfReader(io.BytesIO(contenido))
    except Exception as error:
        raise ErrorPdf("No se pudo leer el archivo: no parece un PDF válido.") from error


def cantidad_paginas(contenido: bytes) -> int:
    return len(_paginas(contenido).pages)


def _pagina_como_pdf(contenido: bytes, numero: int) -> bytes:
    lector = _paginas(contenido)
    if not 1 <= numero <= len(lector.pages):
        raise ErrorPdf(f"El PDF tiene {len(lector.pages)} páginas; no existe la {numero}.")
    escritor = PdfWriter()
    escritor.add_page(lector.pages[numero - 1])
    salida = io.BytesIO()
    escritor.write(salida)
    return salida.getvalue()


def _consultar(pagina_pdf: bytes) -> dict:
    try:
        cliente = anthropic.Anthropic()
        respuesta = cliente.messages.create(
            model=MODELO,
            max_tokens=16000,
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": ESQUEMA}},
            messages=[{"role": "user", "content": [
                {"type": "document", "source": {
                    "type": "base64", "media_type": "application/pdf",
                    "data": base64.standard_b64encode(pagina_pdf).decode(),
                }},
                {"type": "text", "text": INSTRUCCIONES},
            ]}],
        )
    except anthropic.AuthenticationError as error:
        raise ErrorIa("La clave de la API de Anthropic (ANTHROPIC_API_KEY) falta o no es válida.") from error
    except anthropic.APIError as error:
        raise ErrorIa(f"No se pudo consultar a la IA: {error}") from error
    if respuesta.stop_reason in ("refusal", "max_tokens"):
        raise ErrorIa("La IA no pudo leer esta página.")
    texto = next((b.text for b in respuesta.content if b.type == "text"), "")
    try:
        return json.loads(texto)
    except json.JSONDecodeError as error:
        raise ErrorIa("La IA devolvió una respuesta ilegible.") from error


def _hora(texto: str) -> time | None:
    m = HORA.match(texto.strip())
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        return None
    return time(int(m[1]), int(m[2]))


def interpretar(datos: dict, materias, estricto=True) -> dict:
    """Pasa lo leído a la propuesta: bloques con la materia reconocida (id) o, si no existe, su nombre.
    Lo dudoso (horas ilegibles, filas incompletas) va a `advertencias` en lugar de descartarse en silencio."""
    buscador = Buscador(materias, estricto=estricto)
    advertencias = []
    bloques = []

    def agregar(dia, desde, hasta, nombre):
        inicio, fin = _hora(desde), _hora(hasta)
        if inicio is None or fin is None or fin <= inicio:
            advertencias.append(f"Se omitió «{nombre}»: horario ilegible ({desde} a {hasta}).")
            return
        materia = buscador.buscar(nombre)
        bloques.append({"dia": dia, "hora_inicio": inicio, "hora_fin": fin,
                        "materia": materia.id if materia else None,
                        "materia_nombre": materia.nombre if materia else nombre})

    for franja in datos["franjas"]:
        if len(franja["dias"]) != 5:
            advertencias.append(f"La franja {franja['desde']} a {franja['hasta']} no tiene 5 días: se omitió.")
            continue
        for dia, nombre in enumerate(franja["dias"], start=1):
            if nombre.strip():
                agregar(dia, franja["desde"], franja["hasta"], nombre.strip())
    for hora in datos["educacion_fisica"]:
        if 1 <= hora["dia"] <= 5:
            agregar(hora["dia"], hora["desde"], hora["hasta"], "Educación Física")
    if not bloques:
        advertencias.append("No se leyó ningún bloque de horario en esta página.")
    bloques.sort(key=lambda b: (b["dia"], b["hora_inicio"]))
    return {"bloques": bloques, "advertencias": advertencias}


def leer_pagina(contenido: bytes, numero: int, materias) -> tuple[dict, dict]:
    """(encabezado, propuesta) de una página del PDF."""
    datos = _consultar(_pagina_como_pdf(contenido, numero))
    return datos["encabezado"], interpretar(datos, materias)
