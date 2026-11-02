from datetime import time
from decimal import Decimal

from pydantic import BaseModel, Field


class BloqueIn(BaseModel):
    division: int
    materia: int
    dia: int = Field(ge=1, le=5, description="1=lunes … 5=viernes")
    hora_inicio: time
    hora_fin: time


class BloqueOut(BloqueIn):
    id: int


class ReemplazoOut(BaseModel):
    personal_id: int
    nombre: str
    situacion_revista: str


class DocenteOut(BaseModel):
    personal_id: int
    nombre: str
    situacion_revista: str
    es_suplente: bool = False
    suplente_de: ReemplazoOut | None = None


class ResponsableOut(BaseModel):
    personal_id: int
    nombre: str
    pad: Decimal


class BloqueGrilla(BaseModel):
    id: int
    dia: int
    hora_inicio: time
    hora_fin: time
    materia: str
    docentes: list[DocenteOut]
    mayor_pad: list[ResponsableOut] = []  # los 3 con mayor PAD dando clase en ese día y horario


class DivisionOut(BaseModel):
    id: int
    anio: int
    nombre: str
    turno: str
    orientacion: str | None


class GrillaOut(BaseModel):
    preceptores: list[DocenteOut] = []
    division: DivisionOut
    bloques: list[BloqueGrilla]


class BloquePropuesto(BaseModel):
    dia: int
    hora_inicio: time
    hora_fin: time
    materia: int | None  # None: no se reconoció el texto del PDF
    texto: str  # lo que decía la celda del PDF


class PropuestaOut(BaseModel):
    division: int
    bloques: list[BloquePropuesto]


class BloqueRevisado(BaseModel):
    dia: int = Field(ge=1, le=5)
    hora_inicio: time
    hora_fin: time
    materia: int


class ImportacionIn(BaseModel):
    division: int
    bloques: list[BloqueRevisado]
    reemplazar: bool = False  # borra antes los bloques actuales de la división


class ImportacionOut(BaseModel):
    creados: int
    existentes: int
    eliminados: int


class BloqueLeido(BaseModel):
    dia: int
    hora_inicio: time
    hora_fin: time
    materia: int | None  # id si ya existe en el sistema
    materia_nombre: str  # nombre leído (se crea la materia si no existe)


class CursoLeido(BaseModel):
    anio: int
    division: str
    turno: str
    modalidad: str
    preceptor: str
    division_id: int | None  # None: la división todavía no existe y se creará
    bloques: list[BloqueLeido]
    advertencias: list[str] = []


class LecturaOut(BaseModel):
    paginas: int
    pagina: int
    curso: CursoLeido


class CursoImportIn(BaseModel):
    anio: int = Field(ge=1, le=7)
    division: str = Field(min_length=1, max_length=20)
    turno: str = Field(pattern="^(manana|tarde|vespertino)$")
    modalidad: str = ""
    reemplazar: bool = False
    bloques: list[BloqueLeido]


class ImportacionCursosIn(BaseModel):
    cursos: list[CursoImportIn]


class ImportacionCursosOut(ImportacionOut):
    divisiones_creadas: int
    materias_creadas: int
