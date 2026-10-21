from django.db import models

from apps.academico.models import Division, Materia


class BloqueHorario(models.Model):
    class Dia(models.IntegerChoices):
        LUNES = 1, "Lunes"
        MARTES = 2, "Martes"
        MIERCOLES = 3, "Miércoles"
        JUEVES = 4, "Jueves"
        VIERNES = 5, "Viernes"

    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="bloques")
    materia = models.ForeignKey(Materia, on_delete=models.PROTECT, related_name="bloques")
    dia = models.PositiveSmallIntegerField(choices=Dia.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        ordering = ["division", "dia", "hora_inicio"]
        verbose_name = "bloque horario"
        verbose_name_plural = "bloques horarios"

    def __str__(self):
        return f"{self.division} {self.get_dia_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M} {self.materia}"
