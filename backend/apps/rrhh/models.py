from django.core.exceptions import ValidationError
from django.db import models

from apps.academico.models import Division, Materia, Turno


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
    pad = models.DecimalField(
        "PAD", max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Puntaje del docente; se usa para ordenarlos (a mayor puntaje, mejor posición).",
    )
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

    Turno = Turno  # los mismos turnos que los de los cursos (apps.academico.models.Turno)

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
        validar_suplencia(
            self,
            mismo_destino=lambda r: (r.division_id, r.materia_id) == (self.division_id, self.materia_id),
            mensaje_destino="El docente reemplazado debe ser del mismo curso y materia.",
        )

    def __str__(self):
        return f"{self.designacion} · {self.division} · {self.materia}"


class AsignacionPreceptor(models.Model):
    """Curso (división) a cargo de una designación de preceptor. Un curso puede tener más de un
    preceptor (p. ej. uno por turno, o un titular y su suplente)."""

    designacion = models.ForeignKey(Designacion, on_delete=models.CASCADE, related_name="asignaciones_preceptor")
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="asignaciones_preceptor")
    suplente_de = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="suplentes",
        help_text="Asignación del preceptor al que reemplaza (mismo curso). Obligatoria para suplentes.",
    )

    class Meta:
        ordering = ["division", "designacion"]
        verbose_name = "preceptor por curso"
        verbose_name_plural = "preceptores por curso"
        constraints = [
            models.UniqueConstraint(fields=["designacion", "division"], name="asignacion_preceptor_unica"),
        ]

    def clean(self):
        if self.designacion.categoria != Designacion.Categoria.PRECEPTOR:
            raise ValidationError("Solo los preceptores tienen cursos a cargo.")
        validar_suplencia(
            self,
            mismo_destino=lambda r: r.division_id == self.division_id,
            mensaje_destino="El preceptor reemplazado debe ser del mismo curso.",
        )

    def __str__(self):
        return f"{self.designacion} · {self.division}"


def validar_suplencia(asignacion, mismo_destino, mensaje_destino):
    """Reglas de `suplente_de`, comunes a docentes y preceptores: obligatorio para suplentes, solo para
    ellos, hacia alguien del mismo destino que ocupe el cargo (no otro suplente) y que sea otra persona."""
    suplente = Designacion.SituacionRevista.SUPLENTE
    es_suplente = asignacion.designacion.situacion_revista == suplente
    if asignacion.suplente_de_id is None:
        if es_suplente:
            raise ValidationError("Un suplente debe indicar a quién reemplaza (suplente de).")
        return
    if not es_suplente:
        raise ValidationError("Solo un suplente puede indicar a quién reemplaza.")
    reemplazado = asignacion.suplente_de
    if not mismo_destino(reemplazado):
        raise ValidationError(mensaje_destino)
    if reemplazado.designacion.situacion_revista == suplente:
        raise ValidationError("Se reemplaza a un titular, titular interino o provisional, no a otro suplente.")
    if reemplazado.designacion.personal_id == asignacion.designacion.personal_id:
        raise ValidationError("Una persona no puede ser suplente de sí misma.")
