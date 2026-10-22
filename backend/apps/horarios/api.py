"""API de horarios (FastAPI). Se publica en /api/horarios/."""
from fastapi import APIRouter, Depends, HTTPException, Response, status

from apps.academico.models import Division, Materia
from apps.core.fastapi_auth import administrador, usuario_actual
from apps.rrhh.models import AsignacionDocente

from .models import BloqueHorario
from .schemas import BloqueGrilla, BloqueIn, BloqueOut, DivisionOut, DocenteOut, GrillaOut
from .services import ErrorHorario, validar_bloque

router = APIRouter(tags=["horarios"])

SIN_PROCESAR = 422


def _salida(bloque: BloqueHorario) -> BloqueOut:
    return BloqueOut(
        id=bloque.id,
        division=bloque.division_id,
        materia=bloque.materia_id,
        dia=bloque.dia,
        hora_inicio=bloque.hora_inicio,
        hora_fin=bloque.hora_fin,
    )


def _obtener(modelo, pk, nombre):
    obj = modelo.objects.filter(pk=pk).first()
    if obj is None:
        raise HTTPException(SIN_PROCESAR, f"{nombre} inexistente.")
    return obj


def _validar(datos: BloqueIn, excluir_id=None):
    division = _obtener(Division, datos.division, "División")
    materia = _obtener(Materia, datos.materia, "Materia")
    try:
        validar_bloque(
            division=division, materia=materia, dia=datos.dia,
            hora_inicio=datos.hora_inicio, hora_fin=datos.hora_fin, excluir_id=excluir_id,
        )
    except ErrorHorario as e:
        raise HTTPException(SIN_PROCESAR, str(e))
    return division, materia


def _bloque_o_404(pk):
    bloque = BloqueHorario.objects.filter(pk=pk).first()
    if bloque is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bloque inexistente.")
    return bloque


@router.get("/grilla", response_model=GrillaOut)
def grilla(division: int, _=Depends(usuario_actual)):
    """Horario de una división con los docentes de cada materia (titulares y suplentes)."""
    div = Division.objects.select_related("anio", "orientacion").filter(pk=division).first()
    if div is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "División inexistente.")
    docentes: dict[int, list[DocenteOut]] = {}
    asignaciones = AsignacionDocente.objects.filter(division=div).select_related("designacion__personal")
    for a in asignaciones:
        docentes.setdefault(a.materia_id, []).append(DocenteOut(
            nombre=str(a.designacion.personal),
            situacion_revista=a.designacion.get_situacion_revista_display(),
        ))
    bloques = BloqueHorario.objects.filter(division=div).select_related("materia")
    return GrillaOut(
        division=DivisionOut(
            id=div.id, anio=div.anio.numero, nombre=div.nombre,
            orientacion=div.orientacion.nombre if div.orientacion else None,
        ),
        bloques=[
            BloqueGrilla(
                id=b.id, dia=b.dia, hora_inicio=b.hora_inicio, hora_fin=b.hora_fin,
                materia=b.materia.nombre, docentes=docentes.get(b.materia_id, []),
            )
            for b in bloques
        ],
    )


@router.get("/bloques", response_model=list[BloqueOut])
def listar(division: int | None = None, _=Depends(usuario_actual)):
    qs = BloqueHorario.objects.all()
    if division is not None:
        qs = qs.filter(division_id=division)
    return [_salida(b) for b in qs]


@router.get("/bloques/{pk}", response_model=BloqueOut)
def detalle(pk: int, _=Depends(usuario_actual)):
    return _salida(_bloque_o_404(pk))


@router.post("/bloques", response_model=BloqueOut, status_code=status.HTTP_201_CREATED)
def crear(datos: BloqueIn, _=Depends(administrador)):
    division, materia = _validar(datos)
    return _salida(BloqueHorario.objects.create(
        division=division, materia=materia, dia=datos.dia,
        hora_inicio=datos.hora_inicio, hora_fin=datos.hora_fin,
    ))


@router.put("/bloques/{pk}", response_model=BloqueOut)
def actualizar(pk: int, datos: BloqueIn, _=Depends(administrador)):
    bloque = _bloque_o_404(pk)
    division, materia = _validar(datos, excluir_id=pk)
    bloque.division, bloque.materia, bloque.dia = division, materia, datos.dia
    bloque.hora_inicio, bloque.hora_fin = datos.hora_inicio, datos.hora_fin
    bloque.save()
    return _salida(bloque)


@router.delete("/bloques/{pk}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(pk: int, _=Depends(administrador)):
    _bloque_o_404(pk).delete()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
