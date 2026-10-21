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
