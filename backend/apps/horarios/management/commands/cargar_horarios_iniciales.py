import json
import os
import re
import unicodedata
from datetime import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academico.models import Anio, Division, Materia
from apps.horarios.models import BloqueHorario
from apps.horarios.services import ErrorHorario, validar_bloque

ARCHIVO = Path(__file__).resolve().parents[2] / "datos" / "horarios_1er_anio_2026.json"


def _clave(texto: str) -> str:
    """Nombre comparable: sin tildes, en minúsculas y sin signos ("Cs. Naturales" == "cs naturales")."""
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", base.lower()).strip()


def _clave_division(nombre: str) -> str:
    """"2ª", "2°" y "2" son la misma división."""
    numeros = re.findall(r"\d+", nombre)
    return "".join(numeros) if numeros else _clave(nombre)


def _hora(texto: str) -> time:
    horas, minutos = texto.split(":")
    return time(int(horas), int(minutos))


class Command(BaseCommand):
    help = (
        "Carga los horarios de 1.º 2.ª a 1.º 6.ª (2026), tomados del Excel de la escuela. Crea el año, "
        "las divisiones y las materias que falten (reutiliza las existentes) y los bloques horarios. "
        "Es idempotente: se puede ejecutar más de una vez sin duplicar nada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--condicionado",
            action="store_true",
            help="Solo se ejecuta si la variable de entorno CARGAR_HORARIOS_INICIALES vale 1 (para el despliegue).",
        )

    def handle(self, *args, **options):
        if options["condicionado"] and os.environ.get("CARGAR_HORARIOS_INICIALES") != "1":
            self.stdout.write("CARGAR_HORARIOS_INICIALES no es 1: no se cargan horarios iniciales.")
            return
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        with transaction.atomic():
            resumen = self.cargar(datos)
        self.stdout.write(self.style.SUCCESS(
            f"Horarios iniciales: {resumen['bloques_creados']} bloques creados, "
            f"{resumen['bloques_existentes']} ya existían; "
            f"{resumen['materias_creadas']} materias y {resumen['divisiones_creadas']} divisiones nuevas; "
            f"turno completado en {resumen['turnos_completados']} divisiones."
        ))
        for aviso in resumen["omitidos"]:
            self.stdout.write(self.style.WARNING(f"OMITIDO: {aviso}"))

    def cargar(self, datos: dict) -> dict:
        resumen = {"materias_creadas": 0, "divisiones_creadas": 0, "bloques_creados": 0,
                   "bloques_existentes": 0, "turnos_completados": 0, "omitidos": []}
        anio, _ = Anio.objects.get_or_create(numero=datos["anio"])

        existentes = {_clave(m.nombre): m for m in Materia.objects.all()}
        materias: dict[str, Materia] = {}
        for m in datos["materias"]:
            materia = next((existentes[c] for c in map(_clave, [m["nombre"], *m["alias"]]) if c in existentes), None)
            if materia is None:
                materia = Materia.objects.create(nombre=m["nombre"])
                resumen["materias_creadas"] += 1
            materia.anios.add(anio)  # la materia debe dictarse en este año para poder usarse en sus divisiones
            materias[m["nombre"]] = materia

        divisiones = {_clave_division(d.nombre): d for d in Division.objects.filter(anio=anio)}
        for curso in datos["cursos"]:
            clave = _clave_division(curso["division"])
            division = divisiones.get(clave)
            if division is None:
                division = Division.objects.create(anio=anio, nombre=curso["division"], turno=curso["turno"])
                divisiones[clave] = division
                resumen["divisiones_creadas"] += 1
            elif not division.turno:  # divisiones cargadas antes de existir el turno: se completa, nunca se pisa
                division.turno = curso["turno"]
                division.save(update_fields=["turno"])
                resumen["turnos_completados"] += 1
            for b in curso["bloques"]:
                materia = materias[b["materia"]]
                campos = dict(division=division, materia=materia, dia=b["dia"],
                              hora_inicio=_hora(b["inicio"]), hora_fin=_hora(b["fin"]))
                if BloqueHorario.objects.filter(**campos).exists():
                    resumen["bloques_existentes"] += 1
                    continue
                try:
                    validar_bloque(**campos)
                except ErrorHorario as error:
                    resumen["omitidos"].append(
                        f"{division} día {b['dia']} {b['inicio']}-{b['fin']} {materia}: {error}"
                    )
                    continue
                BloqueHorario.objects.create(**campos)
                resumen["bloques_creados"] += 1
        return resumen
