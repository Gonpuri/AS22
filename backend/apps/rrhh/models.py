from django.core.exceptions import ValidationError
from django.db import models

from apps.academico.models import Division, Materia


class Personal(models.Model):
    apellido = models.CharField(max_length=100)
    nombre = models.CharField(max_length=100)
    dni = models.CharField(max_length=8, unique=True)
    cuil = models.CharField(max_length=13, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    domicilio = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["apellido", "nombre"]
        verbose_name = "personal"
        verbose_name_plural = "personal"

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"


class Designacion(models.Model):
    """Función que una persona cumple en un turno. Una misma persona puede tener varias
    (p. ej. preceptor a la mañana y profesor a la tarde)."""

    class Categoria(models.TextChoices):
        PRECEPTOR = "preceptor", "Preceptor"
        DIRECTIVO = "directivo", "Equipo directivo"
        PROFESOR = "profesor", "Profesor"
        EMATP = "ematp", "EMATP"
        OTRO = "otro", "Otro"

    class Turno(models.TextChoices):
        MANANA = "manana", "Mañana"
        TARDE = "tarde", "Tarde"
        VESPERTINO = "vespertino", "Vespertino"

    class SituacionRevista(models.TextChoices):
        TITULAR = "titular", "Titular"
        TITULAR_INTERINO = "titular_interino", "Titular interino"
        SUPLENTE = "suplente", "Suplente"
        PROVISIONAL = "provisional", "Provisional"

    personal = models.ForeignKey(Personal, on_delete=models.CASCADE, related_name="designaciones")
    categoria = models.CharField(max_length=20, choices=Categoria.choices)
    turno = models.CharField(max_length=20, choices=Turno.choices)
    situacion_revista = models.CharField(max_length=20, choices=SituacionRevista.choices)
    cargo = models.CharField(max_length=100, blank=True, help_text="Cargo o función (p. ej. Director, Bibliotecario)")

    class Meta:
        ordering = ["personal", "turno", "categoria"]
        verbose_name = "designación"
        verbose_name_plural = "designaciones"
        constraints = [
            models.UniqueConstraint(fields=["personal", "categoria", "turno"], name="designacion_unica"),
        ]

    def __str__(self):
        return f"{self.personal} · {self.get_categoria_display()} ({self.get_turno_display()})"


class AsignacionDocente(models.Model):
    """Curso (división) y materia que dicta una designación de profesor o EMATP.
    Un docente puede tener varias asignaciones: distintos cursos y distintas materias."""

    CATEGORIAS_DOCENTES = (Designacion.Categoria.PROFESOR, Designacion.Categoria.EMATP)

    designacion = models.ForeignKey(Designacion, on_delete=models.CASCADE, related_name="asignaciones")
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="asignaciones_docentes")
    materia = models.ForeignKey(Materia, on_delete=models.PROTECT, related_name="asignaciones_docentes")
    suplente_de = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="suplentes",
        help_text="Asignación del docente al que reemplaza (mismo curso y materia). Obligatoria para suplentes.",
    )

    class Meta:
        ordering = ["designacion", "division", "materia"]
        verbose_name = "asignación docente"
        verbose_name_plural = "asignaciones docentes"
        constraints = [
            models.UniqueConstraint(fields=["designacion", "division", "materia"], name="asignacion_unica"),
        ]

    def clean(self):
        if self.designacion.categoria not in self.CATEGORIAS_DOCENTES:
            raise ValidationError("Solo los profesores y EMATPs tienen cursos y materias asignados.")
        if not self.division.materias().filter(pk=self.materia_id).exists():
            raise ValidationError("La materia no corresponde al año/orientación de la división.")
        suplente = Designacion.SituacionRevista.SUPLENTE
        es_suplente = self.designacion.situacion_revista == suplente
        if self.suplente_de_id is None:
            if es_suplente:
                raise ValidationError("Un suplente debe indicar a quién reemplaza (suplente de).")
            return
        if not es_suplente:
            raise ValidationError("Solo un suplente puede indicar a quién reemplaza.")
        reemplazado = self.suplente_de
        if (reemplazado.division_id, reemplazado.materia_id) != (self.division_id, self.materia_id):
            raise ValidationError("El docente reemplazado debe ser del mismo curso y materia.")
        if reemplazado.designacion.situacion_revista == suplente:
            raise ValidationError("Se reemplaza a un titular, titular interino o provisional, no a otro suplente.")
        if reemplazado.designacion.personal_id == self.designacion.personal_id:
            raise ValidationError("Una persona no puede ser suplente de sí misma.")

    def __str__(self):
        return f"{self.designacion} · {self.division} · {self.materia}"
