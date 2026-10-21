from datetime import time

from pydantic import BaseModel, Field


class BloqueIn(BaseModel):
    division: int
    materia: int
    dia: int = Field(ge=1, le=5, description="1=lunes … 5=viernes")
    hora_inicio: time
    hora_fin: time


class BloqueOut(BloqueIn):
    id: int
