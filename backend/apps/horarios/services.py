import re
import unicodedata

from django.db import transaction

from .models import BloqueHorario


def clave_texto(texto: str) -> str:
    """Nombre comparable: sin tildes, en minúsculas y sin signos ("Cs. Naturales" == "cs naturales")."""
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", base.lower()).strip()


DIAS = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes"}


def clave_division(nombre: str) -> str:
    """"2ª", "2°" y "2" son la misma división."""
    numeros = re.findall(r"\d+", nombre)
    return "".join(numeros) if numeros else clave_texto(nombre)


class ErrorHorario(ValueError):
    pass


def validar_bloque(*, division, materia, dia, hora_inicio, hora_fin, excluir_id=None):
    """Reglas: la hora de fin es posterior a la de inicio, la materia se cursa en la división
    y no se superpone con otro bloque de la misma división el mismo día."""
    if hora_fin <= hora_inicio:
        raise ErrorHorario("La hora de fin debe ser posterior a la de inicio.")
    if not division.materias().filter(pk=materia.pk).exists():
        raise ErrorHorario("La materia no corresponde al año/orientación de la división.")
    superpuestos = BloqueHorario.objects.filter(
        division=division, dia=dia, hora_inicio__lt=hora_fin, hora_fin__gt=hora_inicio
    )
    if excluir_id:
        superpuestos = superpuestos.exclude(pk=excluir_id)
    if superpuestos.exists():
        raise ErrorHorario("El bloque se superpone con otro de la misma división.")


def _guardar_bloques(division, bloques, resumen, errores):
    """Crea los bloques de una división que no existan ya; los inválidos se acumulan en `errores`."""
    for b in bloques:
        campos = dict(division=division, materia=b["materia"], dia=b["dia"],
                      hora_inicio=b["hora_inicio"], hora_fin=b["hora_fin"])
        if BloqueHorario.objects.filter(**campos).exists():
            resumen["existentes"] += 1
            continue
        try:
            validar_bloque(**campos)
        except ErrorHorario as error:
            errores.append(
                f"{division} {DIAS[b['dia']]} {b['hora_inicio']:%H:%M}-{b['hora_fin']:%H:%M} {b['materia']}: {error}"
            )
            continue
        BloqueHorario.objects.create(**campos)
        resumen["creados"] += 1


def importar_bloques(division, bloques, reemplazar=False):
    """Guarda el horario completo de una división (bloques con `materia` ya resuelta) en una sola
    transacción: si algún bloque no es válido no se guarda nada. Con `reemplazar` se borran antes los
    bloques actuales; sin eso, los que ya existen idénticos se cuentan y no se duplican.
    Devuelve {"creados", "existentes", "eliminados"}."""
    resumen = {"creados": 0, "existentes": 0, "eliminados": 0}
    errores = []
    with transaction.atomic():
        if reemplazar:
            resumen["eliminados"] = BloqueHorario.objects.filter(division=division).delete()[0]
        _guardar_bloques(division, bloques, resumen, errores)
        if errores:
            transaction.set_rollback(True)
            raise ErrorHorario("No se guardó nada. " + " · ".join(errores))
    return resumen


def vincular_materia(materia, division):
    """Deja la materia habilitada para la división (año y, si hace falta, orientación). Se usa al cargar
    un horario desde un PDF, que es la prueba de que esa materia se dicta ahí. Las materias sin
    orientaciones sirven a todas las del año; si tienen, se les suma la de la división."""
    materia.anios.add(division.anio)
    if materia.orientaciones.exists():
        if division.orientacion_id is None:
            raise ErrorHorario(f"«{materia}» es de una orientación y la división {division} no tiene ninguna.")
        materia.orientaciones.add(division.orientacion)


def importar_cursos(cursos):
    """Carga el horario de varios cursos leídos de un PDF, todo en una transacción. Crea lo que falte
    (año, orientación, división y materias) y vincula cada materia con su división.
    Cada curso: {anio, nombre, turno, orientacion, reemplazar, bloques: [{dia, hora_inicio, hora_fin,
    materia (Materia o None), materia_nombre}]}. Devuelve los totales."""
    from apps.academico.models import Anio, Division, Materia, Orientacion

    resumen = {"creados": 0, "existentes": 0, "eliminados": 0, "divisiones_creadas": 0, "materias_creadas": 0}
    errores = []
    with transaction.atomic():
        materias = {clave_texto(m.nombre): m for m in Materia.objects.all()}
        orientaciones = {clave_texto(o.nombre): o for o in Orientacion.objects.all()}
        for curso in cursos:
            anio, _ = Anio.objects.get_or_create(numero=curso["anio"])
            orientacion = None
            if curso["orientacion"]:
                clave = clave_texto(curso["orientacion"])
                if clave not in orientaciones:
                    orientaciones[clave] = Orientacion.objects.create(nombre=curso["orientacion"].strip())
                orientacion = orientaciones[clave]
            clave = clave_division(curso["nombre"])
            division = next((d for d in Division.objects.filter(anio=anio) if clave_division(d.nombre) == clave), None)
            if division is None:
                division = Division.objects.create(
                    anio=anio, nombre=curso["nombre"], turno=curso["turno"], orientacion=orientacion
                )
                resumen["divisiones_creadas"] += 1
            else:
                cambios = []
                if not division.turno:
                    division.turno = curso["turno"]
                    cambios.append("turno")
                if division.orientacion_id is None and orientacion:
                    division.orientacion = orientacion
                    cambios.append("orientacion")
                if cambios:
                    division.save(update_fields=cambios)
            if curso["reemplazar"]:
                resumen["eliminados"] += BloqueHorario.objects.filter(division=division).delete()[0]
            resueltos = []
            for b in curso["bloques"]:
                materia = b["materia"] or materias.get(clave_texto(b["materia_nombre"]))
                if materia is None:
                    materia = materias[clave_texto(b["materia_nombre"])] = Materia.objects.create(
                        nombre=b["materia_nombre"].strip()
                    )
                    resumen["materias_creadas"] += 1
                try:
                    vincular_materia(materia, division)
                except ErrorHorario as error:
                    errores.append(str(error))
                    continue
                resueltos.append({**b, "materia": materia})
            _guardar_bloques(division, resueltos, resumen, errores)
        if errores:
            transaction.set_rollback(True)
            raise ErrorHorario("No se guardó nada. " + " · ".join(dict.fromkeys(errores)))
    return resumen


LIMITE_MAYOR_PAD = 3


def mayor_pad_por_bloque(bloques, limite=LIMITE_MAYOR_PAD):
    """Para cada bloque, los `limite` docentes con mayor PAD entre quienes están dando clase en la
    escuela en ese día y horario (se superponen con él), en cualquier curso: son quienes asumirían la
    responsabilidad ante la falta de autoridades. Devuelve {id del bloque: [Personal, ...]}.

    Cuentan solo personas activas con PAD cargado, una sola vez aunque tengan varias designaciones.
    Orden: mayor PAD primero; a igual PAD, por apellido y nombre. Si en una materia de un curso hay
    titular y suplente, ambos figuran (el sistema no sabe quién concurre)."""
    from apps.rrhh.models import AsignacionDocente  # horarios solo depende de rrhh para esta consulta

    personas = {}  # (división, materia) -> {id de persona: Personal}
    asignaciones = AsignacionDocente.objects.filter(
        designacion__categoria__in=AsignacionDocente.CATEGORIAS_DOCENTES,
        designacion__personal__activo=True,
        designacion__personal__pad__isnull=False,
    ).select_related("designacion__personal")
    for a in asignaciones:
        persona = a.designacion.personal
        personas.setdefault((a.division_id, a.materia_id), {})[persona.id] = persona

    por_dia = {}
    for division_id, materia_id, dia, inicio, fin in BloqueHorario.objects.values_list(
        "division_id", "materia_id", "dia", "hora_inicio", "hora_fin"
    ):
        if (division_id, materia_id) in personas:
            por_dia.setdefault(dia, []).append((inicio, fin, personas[(division_id, materia_id)]))

    resultado = {}
    for bloque in bloques:
        candidatos = {}
        for inicio, fin, gente in por_dia.get(bloque.dia, []):
            if inicio < bloque.hora_fin and fin > bloque.hora_inicio:
                candidatos.update(gente)
        ranking = sorted(candidatos.values(), key=lambda p: (-p.pad, p.apellido, p.nombre))
        resultado[bloque.id] = ranking[:limite]
    return resultado
