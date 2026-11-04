"""Carga de personal desde una planilla Excel (.xlsx). La clave única es el DNI: si la persona ya existe
se completan sus datos, si no se crea. Nada se escribe en la base desde la lectura: primero se arma una
propuesta (`leer_planilla`) que la persona revisa y recién después se aplica (`aplicar`).

La planilla es una tabla con una fila de encabezados; las columnas se reconocen por su nombre, sin
importar el orden, tildes ni mayúsculas (ver COLUMNAS). Hace falta, como mínimo, la columna del DNI.
"""
import io
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from openpyxl import load_workbook

from .models import Personal
from .serializers import PersonalSerializer

MAX_FILAS = 2000
MAX_BYTES = 5 * 1024 * 1024
FILAS_BUSCANDO_ENCABEZADO = 20

# campo -> nombres de columna aceptados (ya normalizados)
COLUMNAS = {
    "dni": {"dni", "d n i", "documento", "nro documento", "n documento", "numero de documento", "nro de documento"},
    "apellido": {"apellido", "apellidos"},
    "nombre": {"nombre", "nombres"},
    "apellido_nombre": {"apellido y nombre", "apellido y nombres", "apellidos y nombres", "apellidos y nombre",
                        "nombre y apellido", "nombres y apellidos", "nombre completo", "agente", "docente"},
    "cuil": {"cuil", "cuit", "cuil cuit"},
    "fecha_nacimiento": {"fecha de nacimiento", "fecha nacimiento", "nacimiento", "fec nac", "f nacimiento"},
    "domicilio": {"domicilio", "direccion"},
    "telefono": {"telefono", "tel", "celular", "telefono celular", "nro de telefono"},
    "email": {"email", "e mail", "mail", "correo", "correo electronico"},
    "fecha_ingreso": {"fecha de ingreso", "fecha ingreso", "ingreso", "f ingreso"},
    "pad": {"pad", "puntaje pad", "puntaje"},
}
CAMPOS = ["dni", "apellido", "nombre", "cuil", "fecha_nacimiento", "domicilio", "telefono", "email",
          "fecha_ingreso", "pad"]


class ErrorPlanilla(ValueError):
    pass


def _clave(texto) -> str:
    base = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", base.lower()).strip()


def _campo_de(encabezado) -> str | None:
    """Campo al que corresponde un encabezado: primero el nombre exacto y, si no, que empiece con alguno
    ("Email (abc)", "Fecha de ingreso a la escuela")."""
    clave = _clave(encabezado)
    if not clave:
        return None
    exacto = next((campo for campo, nombres in COLUMNAS.items() if clave in nombres), None)
    return exacto or next(
        (campo for campo, nombres in COLUMNAS.items() if any(clave.startswith(n + " ") for n in nombres)), None
    )


def _texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\s+", " ", str(valor)).strip()


def _dni(valor) -> str:
    """Solo dígitos: "30.123.456", 30123456 y 30123456.0 son el mismo DNI."""
    return re.sub(r"\D", "", _texto(valor))


def _fecha(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = _texto(valor)
    if not texto:
        return None
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    raise ValueError(f"fecha no reconocida «{texto}» (usá dd/mm/aaaa)")


def _pad(valor) -> Decimal | None:
    texto = _texto(valor).replace(",", ".")
    if not texto or not texto.strip("-–— "):  # vacío o "-": sin PAD
        return None
    try:
        return Decimal(texto).quantize(Decimal("0.001"))
    except InvalidOperation:
        raise ValueError(f"PAD no numérico «{texto}»") from None


PARTICULAS = {"de", "del", "la", "las", "los", "y", "da", "do", "di"}


def _propio(texto: str) -> str:
    """"MARIA ELENA" / "maria elena" -> "Maria Elena". Lo que ya viene con mayúsculas y minúsculas mezcladas
    se respeta tal cual."""
    if texto != texto.upper() and texto != texto.lower():
        return texto
    return " ".join(p if i and p.lower() in PARTICULAS else p.capitalize() for i, p in enumerate(texto.lower().split()))


def _cuil(texto: str) -> str:
    """11 dígitos -> XX-XXXXXXXX-X; cualquier otra cosa se deja como vino."""
    digitos = re.sub(r"\D", "", texto)
    return f"{digitos[:2]}-{digitos[2:10]}-{digitos[10]}" if len(digitos) == 11 else texto


def _separar_apellido_nombre(texto: str, email: str = "") -> tuple[str, str, bool]:
    """(apellido, nombre, dudoso). «Apellido, Nombre» es inequívoco. Sin coma no se sabe si viene
    «Nombre Apellido» o «Apellido Nombre» ni dónde corta cuando hay varias palabras: se elige la división
    cuyo apellido aparece en el correo (casi siempre lo lleva) y, ante empate, la de nombre primero.
    `dudoso` avisa cuando conviene revisarlo: más de dos palabras, apellido primero o ninguna pista en el correo."""
    if "," in texto:
        apellido, nombre = texto.split(",", 1)
        return _propio(apellido.strip()), _propio(nombre.strip()), False
    palabras = texto.split()
    if len(palabras) < 2:
        return _propio(texto), "", True
    usuario = _clave(email.split("@")[0]).replace(" ", "")
    def posiciones(grupo):
        claves = [_clave(p).replace(" ", "") for p in grupo]
        return [usuario.find(c) for c in claves if len(c) >= 3 and c in usuario]

    candidatas = []  # (puntaje, nombre antes que apellido en el correo, apellido al final, apellido, nombre, hallados)
    for i in range(1, len(palabras)):
        for apellido_al_final in (True, False):
            apellido = palabras[i:] if apellido_al_final else palabras[:i]
            nombre = palabras[:i] if apellido_al_final else palabras[i:]
            en_apellido, en_nombre = posiciones(apellido), posiciones(nombre)
            orden = not (en_apellido and en_nombre) or max(en_nombre) < min(en_apellido)
            candidatas.append((len(en_apellido) - 0.5 * (len(apellido) - len(en_apellido)), orden,
                               apellido_al_final, apellido, nombre, len(en_apellido)))
    _, _, al_final, apellido, nombre, hallados = max(candidatas, key=lambda c: c[:3])
    return _propio(" ".join(apellido)), _propio(" ".join(nombre)), len(palabras) > 2 or not al_final or hallados == 0


def _filas(contenido: bytes):
    try:
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as error:  # archivo corrupto o que no es un .xlsx
        raise ErrorPlanilla("No se pudo leer el archivo: tiene que ser una planilla de Excel (.xlsx).") from error
    try:
        yield from enumerate(libro.active.iter_rows(values_only=True), start=1)
    finally:
        libro.close()


def leer_planilla(contenido: bytes) -> list[dict]:
    """Propuesta fila por fila: {fila, datos, accion: crear|actualizar|error, errores, cambios}.
    `datos` son los valores ya limpios; `cambios` (solo al actualizar) lista los campos que se modificarían."""
    filas = _filas(contenido)
    columnas: dict[int, str] = {}
    for n, valores in filas:
        encontradas = {i: c for i, v in enumerate(valores) if (c := _campo_de(v))}
        if "dni" in encontradas.values():
            columnas = encontradas
            break
        if n >= FILAS_BUSCANDO_ENCABEZADO:
            break
    if not columnas:
        raise ErrorPlanilla(
            "No se encontró la fila de encabezados. La planilla necesita al menos una columna «DNI» "
            "(y, por ejemplo, «Apellido», «Nombre», «CUIL», «Fecha de nacimiento», «Domicilio», "
            "«Teléfono», «Email», «Fecha de ingreso», «PAD»)."
        )

    propuesta, vistos = [], {}
    for numero, valores in filas:
        if all(_texto(v) == "" for v in valores):
            continue
        if len(propuesta) >= MAX_FILAS:
            raise ErrorPlanilla(f"La planilla supera las {MAX_FILAS} filas.")
        propuesta.append(_interpretar(numero, valores, columnas, vistos))
    if not propuesta:
        raise ErrorPlanilla("La planilla no tiene personal debajo de los encabezados.")
    return propuesta


def _interpretar(numero, valores, columnas, vistos) -> dict:
    errores, datos = [], {}
    crudo = {campo: valores[i] if i < len(valores) else None for i, campo in columnas.items()}
    try:
        for campo in ("fecha_nacimiento", "fecha_ingreso"):
            if campo in crudo:
                datos[campo] = _fecha(crudo[campo])
        if "pad" in crudo:
            datos["pad"] = _pad(crudo["pad"])
    except ValueError as error:
        errores.append(str(error))
    for campo in ("dni", "cuil", "domicilio", "telefono", "email", "apellido", "nombre"):
        if campo in crudo:
            datos[campo] = _dni(crudo[campo]) if campo == "dni" else _texto(crudo[campo])
    if "cuil" in datos:
        datos["cuil"] = _cuil(datos["cuil"])
    if "email" in datos:
        datos["email"] = datos["email"].lower()
    for campo in ("apellido", "nombre"):
        if campo in datos:
            datos[campo] = _propio(datos[campo])
    dudoso = False
    if "apellido_nombre" in crudo and _texto(crudo["apellido_nombre"]):
        datos["apellido"], datos["nombre"], dudoso = _separar_apellido_nombre(
            _texto(crudo["apellido_nombre"]), datos.get("email", "")
        )
    dni = datos.get("dni", "")
    if not dni:
        errores.append("Falta el DNI.")
    elif dni in vistos:
        errores.append(f"El DNI está repetido en la fila {vistos[dni]}.")
    else:
        vistos[dni] = numero
    fila = {"fila": numero, "datos": {k: str(v) if isinstance(v, Decimal) else v
                                      for k, v in datos.items() if v not in ("", None)}, "dni": dni,
            "revisar_nombre": dudoso}

    existente = Personal.objects.filter(dni=dni).first() if dni else None
    if existente:  # el DNI identifica a la persona: su nombre ya cargado no se pisa con el de la planilla
        fila["datos"].pop("apellido", None)
        fila["datos"].pop("nombre", None)
        fila["revisar_nombre"] = False
    if errores:
        return {**fila, "accion": "error", "errores": errores, "cambios": []}
    serializador = PersonalSerializer(existente, data=_para_serializador(fila["datos"]), partial=existente is not None)
    if not serializador.is_valid():
        mensajes = [f"{campo}: {' '.join(map(str, msgs))}" for campo, msgs in serializador.errors.items()]
        return {**fila, "accion": "error", "errores": mensajes, "cambios": []}
    cambios = [] if existente is None else [
        campo for campo, valor in serializador.validated_data.items() if getattr(existente, campo) != valor
    ]
    return {**fila, "accion": "crear" if existente is None else "actualizar", "errores": [], "cambios": cambios}


def _para_serializador(datos: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, date) else str(v) if isinstance(v, Decimal) else v)
            for k, v in datos.items()}


@transaction.atomic
def aplicar(filas: list[dict]) -> dict:
    """Crea o actualiza (por DNI) las personas ya revisadas, todo o nada. Al actualizar solo se tocan
    los campos que vienen con valor: una celda vacía nunca borra un dato que ya estaba cargado."""
    resumen, vistos = {"creados": 0, "actualizados": 0, "sin_cambios": 0}, set()
    for datos in filas:
        dni = _dni(datos.get("dni"))
        if dni in vistos:
            raise ErrorPlanilla(f"El DNI {dni} está repetido.")
        vistos.add(dni)
        existente = Personal.objects.filter(dni=dni).first()
        serializador = PersonalSerializer(existente, data={**datos, "dni": dni}, partial=existente is not None)
        if not serializador.is_valid():
            raise ErrorPlanilla(f"DNI {dni}: {serializador.errors}")
        if existente is None:
            serializador.save()
            resumen["creados"] += 1
        elif any(getattr(existente, c) != v for c, v in serializador.validated_data.items()):
            serializador.save()
            resumen["actualizados"] += 1
        else:
            resumen["sin_cambios"] += 1
    return resumen
