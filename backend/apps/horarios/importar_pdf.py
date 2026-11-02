"""Lectura del horario completo de un curso desde un PDF.

El PDF debe traer la grilla como tabla: una columna por día (lunes … viernes) y una fila por franja
horaria, con la franja ("07:30 a 08:30") en la primera columna y la materia en cada celda. También se
acepta la grilla traspuesta (días en las filas, franjas en las columnas). El resultado es una propuesta
que la persona revisa antes de guardar: nada se escribe en la base desde acá.
"""
import difflib
import io
import re
from datetime import time

import pdfplumber

from .services import clave_texto

DIAS = {"lunes": 1, "lun": 1, "martes": 2, "mar": 2, "miercoles": 3, "mie": 3, "mier": 3,
        "jueves": 4, "jue": 4, "viernes": 5, "vie": 5}
FRANJA = re.compile(r"(\d{1,2})\s*[:.hH]\s*(\d{2})\s*(?:hs\.?)?\s*(?:a|al|-|–|—|/)?\s*(\d{1,2})\s*[:.hH]\s*(\d{2})")
SIN_CLASE = ("recreo", "receso", "almuerzo", "descanso", "break")
UMBRAL_PARECIDO = 0.8


class ErrorPdf(ValueError):
    pass


def _texto(celda) -> str:
    return re.sub(r"\s+", " ", celda or "").strip()


def _dia(celda) -> int | None:
    return DIAS.get(clave_texto(_texto(celda)))


def _franja(celda) -> tuple[time, time] | None:
    m = FRANJA.search(_texto(celda))
    if not m:
        return None
    h1, m1, h2, m2 = map(int, m.groups())
    if h1 > 23 or h2 > 23 or m1 > 59 or m2 > 59:
        return None
    return time(h1, m1), time(h2, m2)


def _transponer(tabla):
    ancho = max(len(f) for f in tabla)
    return [[(f[i] if i < len(f) else None) for f in tabla] for i in range(ancho)]


def _celdas_de(tabla):
    """Recorre una tabla (días en columnas) y entrega (día, inicio, fin, texto) por cada celda con contenido.
    Devuelve None si no se reconoce una fila de encabezado con al menos tres días."""
    for i, fila in enumerate(tabla):
        columnas = {j: d for j, c in enumerate(fila) if (d := _dia(c))}
        if len(columnas) < 3:
            continue
        salida = []
        for resto in tabla[i + 1:]:
            franja = next((f for c in resto if (f := _franja(c))), None)
            if franja is None:
                continue
            for j, dia in columnas.items():
                texto = _texto(resto[j]) if j < len(resto) else ""
                if texto and not any(p in clave_texto(texto) for p in SIN_CLASE) and not _franja(texto):
                    salida.append((dia, franja[0], franja[1], texto))
        return salida
    return None


def extraer_celdas(contenido: bytes) -> list[tuple[int, time, time, str]]:
    try:
        pdf = pdfplumber.open(io.BytesIO(contenido))
    except Exception as error:  # archivo corrupto o que no es un PDF
        raise ErrorPdf("No se pudo leer el archivo: no parece un PDF válido.") from error
    celdas = []
    with pdf:
        for pagina in pdf.pages:
            tablas = pagina.extract_tables() or pagina.extract_tables({"vertical_strategy": "text", "horizontal_strategy": "text"})
            for tabla in tablas:
                tabla = [f for f in tabla if f]
                if not tabla:
                    continue
                encontradas = _celdas_de(tabla)
                if encontradas is None:
                    encontradas = _celdas_de(_transponer(tabla))
                celdas.extend(encontradas or [])
    if not celdas:
        raise ErrorPdf(
            "No se encontró un horario en el PDF. Debe tener una tabla con los días (lunes a viernes) "
            "y las franjas horarias (por ejemplo «07:30 a 08:30») en la primera columna."
        )
    return celdas


class Buscador:
    """Relaciona el texto de una celda con una materia de la división (sin tildes ni mayúsculas;
    acepta abreviaturas y diferencias leves)."""

    def __init__(self, materias):
        self.por_clave = {clave_texto(m.nombre): m for m in materias}

    def buscar(self, texto: str):
        clave = clave_texto(texto)
        if clave in self.por_clave:
            return self.por_clave[clave]
        palabras = clave.split()
        candidatas = [m for c, m in self.por_clave.items()
                      if c.startswith(clave) or clave.startswith(c) or _abreviatura(palabras, c.split())]
        if len(candidatas) == 1:
            return candidatas[0]
        parecida = difflib.get_close_matches(clave, self.por_clave, n=1, cutoff=UMBRAL_PARECIDO)
        return self.por_clave[parecida[0]] if parecida else None


def _subsecuencia(corta: str, larga: str) -> bool:
    letras = iter(larga)
    return all(c in letras for c in corta)


def _abreviatura(palabras, nombre) -> bool:
    """"Cs Naturales" ~ "Ciencias Naturales": mismas palabras, cada una igual o abreviada (misma inicial)."""
    return len(palabras) == len(nombre) and all(
        a == b or (a[0] == b[0] and _subsecuencia(a, b)) for a, b in zip(palabras, nombre)
    )


def proponer_bloques(contenido: bytes, materias) -> list[dict]:
    """Bloques propuestos, ordenados por día y hora. `materia` es el id de la materia reconocida
    (None si no se pudo relacionar: la persona la elige en la revisión); `texto` es lo que decía el PDF."""
    buscador = Buscador(materias)
    bloques = []
    for dia, inicio, fin, texto in sorted(extraer_celdas(contenido), key=lambda c: c[:3]):
        materia = buscador.buscar(texto)
        bloques.append({"dia": dia, "hora_inicio": inicio, "hora_fin": fin,
                        "materia": materia.id if materia else None, "texto": texto})
    return bloques
