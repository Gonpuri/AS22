from .models import BloqueHorario


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
