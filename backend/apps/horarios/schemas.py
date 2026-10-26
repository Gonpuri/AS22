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
