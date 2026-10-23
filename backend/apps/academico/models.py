from django.db import models


class Turno(models.TextChoices):
    MANANA = "manana", "Mañana"
    TARDE = "tarde", "Tarde"
    VESPERTINO = "vespertino", "Vespertino"


class Orientacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "orientación"
        verbose_name_plural = "orientaciones"

    def __str__(self):
        return self.nombre


class Anio(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        ordering = ["numero"]
        verbose_name = "año"
        verbose_name_plural = "años"

    def __str__(self):
        return f"{self.numero}°"


class Division(models.Model):
    anio = models.ForeignKey(Anio, on_delete=models.PROTECT, related_name="divisiones")
    orientacion = models.ForeignKey(
        Orientacion, null=True, blank=True, on_delete=models.PROTECT, related_name="divisiones"
    )
    nombre = models.CharField(max_length=20)
    turno = models.CharField(
        max_length=20, choices=Turno.choices, blank=True,
        help_text="Turno en que cursa. Se exige al guardar por la API; puede quedar vacío en divisiones anteriores.",
    )

    class Meta:
        ordering = ["anio__numero", "nombre"]
        verbose_name = "división"
        verbose_name_plural = "divisiones"
        constraints = [
            models.UniqueConstraint(fields=["anio", "nombre"], name="division_unica_por_anio"),
        ]

    def __str__(self):
        return f"{self.anio} {self.nombre}"

    def materias(self):
        """Materias que se cursan en esta división: las del año y, si la materia
        está asociada a orientaciones, solo si incluye la de la división."""
        qs = Materia.objects.filter(anios=self.anio)
        if self.orientacion_id:
            return qs.filter(
                models.Q(orientaciones__isnull=True) | models.Q(orientaciones=self.orientacion_id)
            ).distinct()
        return qs.filter(orientaciones__isnull=True)


class Materia(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    anios = models.ManyToManyField(Anio, blank=True, related_name="materias")
    orientaciones = models.ManyToManyField(Orientacion, blank=True, related_name="materias")

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
