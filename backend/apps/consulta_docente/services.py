import re
from datetime import date, timedelta

from django.db.models import F, Value
from django.db.models.functions import Replace

from apps.horarios.models import BloqueHorario
from apps.rrhh.models import AsignacionDocente, Personal

MAX_DIAS = 366
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def normalizar_cuil(valor: str) -> str:
    """Deja solo los dígitos: acepta 20-30123456-7, 20 30123456 7 o 20301234567."""
    return re.sub(r"\D", "", valor or "")


def buscar_docente(cuil: str):
    """Personal cuyo CUIL (guardado con o sin guiones/espacios) coincide con `cuil`."""
    buscado = normalizar_cuil(cuil)
    sin_formato = Replace(Replace(F("cuil"), Value("-"), Value("")), Value(" "), Value(""))
    return Personal.objects.annotate(cuil_digitos=sin_formato).filter(cuil_digitos=buscado).first()


def clases_del_docente(personal: Personal, desde: date, hasta: date) -> dict:
    """Clases del docente por fecha: sus asignaciones (curso + materia) cruzadas con los bloques
    del horario de ese curso, según el día de la semana. No considera feriados ni asuetos."""
    asignaciones = list(
        AsignacionDocente.objects.filter(
            designacion__personal=personal,
            designacion__categoria__in=AsignacionDocente.CATEGORIAS_DOCENTES,
        ).select_related("designacion", "division__anio", "materia")
    )
    situaciones = {(a.division_id, a.materia_id): a.designacion.get_situacion_revista_display() for a in asignaciones}
    bloques = BloqueHorario.objects.filter(division_id__in={d for d, _ in situaciones}).select_related(
        "division__anio", "materia"
    )
    por_dia: dict[int, list[dict]] = {}
    for b in bloques:
        if (b.division_id, b.materia_id) not in situaciones:
            continue
        por_dia.setdefault(b.dia, []).append({
            "hora_inicio": b.hora_inicio.strftime("%H:%M"),
            "hora_fin": b.hora_fin.strftime("%H:%M"),
            "curso": str(b.division),
            "materia": b.materia.nombre,
            "situacion_revista": situaciones[(b.division_id, b.materia_id)],
        })
    for clases in por_dia.values():
        clases.sort(key=lambda c: (c["hora_inicio"], c["curso"]))

    dias = []
    for n in range((hasta - desde).days + 1):
        fecha = desde + timedelta(days=n)
        dias.append({
            "fecha": fecha.isoformat(),
            "dia": DIAS_SEMANA[fecha.weekday()],
            "clases": por_dia.get(fecha.weekday() + 1, []),  # BloqueHorario.dia: 1=lunes … 5=viernes
        })
    return {
        "docente": {"id": personal.id, "apellido": personal.apellido, "nombre": personal.nombre, "cuil": personal.cuil},
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "cursos_asignados": len(situaciones),
        "tiene_clases": any(d["clases"] for d in dias),
        "dias": dias,
    }
