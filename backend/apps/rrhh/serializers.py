from rest_framework import serializers

from .models import AsignacionDocente, Designacion, Personal


def _valor(serializer, attrs, clave):
    """Valor nuevo si viene en la petición; si no, el de la instancia que se edita."""
    return attrs.get(clave, getattr(serializer.instance, clave, None))


class PersonalSerializer(serializers.ModelSerializer):
    categorias = serializers.SerializerMethodField()

    class Meta:
        model = Personal
        fields = [
            "id", "apellido", "nombre", "dni", "cuil", "fecha_nacimiento", "domicilio",
            "telefono", "email", "fecha_ingreso", "activo", "categorias",
        ]

    def get_categorias(self, obj):
        return sorted({d.categoria for d in obj.designaciones.all()})

    def validate_dni(self, value):
        if not (value.isdigit() and 7 <= len(value) <= 8):
            raise serializers.ValidationError("El DNI debe tener 7 u 8 dígitos.")
        return value


class DesignacionSerializer(serializers.ModelSerializer):
    etiqueta = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Designacion
        fields = ["id", "personal", "categoria", "turno", "situacion_revista", "cargo", "etiqueta"]
        validators = []  # la unicidad se valida abajo con mensaje en español

    def validate(self, attrs):
        categoria = _valor(self, attrs, "categoria")
        repetida = Designacion.objects.filter(
            personal=_valor(self, attrs, "personal"), categoria=categoria, turno=_valor(self, attrs, "turno")
        )
        if self.instance:
            repetida = repetida.exclude(pk=self.instance.pk)
        if repetida.exists():
            raise serializers.ValidationError("La persona ya tiene esa categoría en ese turno.")
        if self.instance and categoria not in AsignacionDocente.CATEGORIAS_DOCENTES \
                and self.instance.asignaciones.exists():
            raise serializers.ValidationError("La designación tiene cursos y materias asignados.")
        if self.instance:
            es_suplente = _valor(self, attrs, "situacion_revista") == Designacion.SituacionRevista.SUPLENTE
            if not es_suplente and self.instance.asignaciones.filter(suplente_de__isnull=False).exists():
                raise serializers.ValidationError(
                    "Tiene asignaciones que reemplazan a otro docente: quitá el reemplazo primero."
                )
            if es_suplente and AsignacionDocente.objects.filter(suplente_de__designacion=self.instance).exists():
                raise serializers.ValidationError("Tiene suplentes asignados: no puede pasar a ser suplente.")
        return attrs


class AsignacionDocenteSerializer(serializers.ModelSerializer):
    etiqueta = serializers.CharField(source="__str__", read_only=True)
    situacion_revista = serializers.CharField(source="designacion.situacion_revista", read_only=True)

    class Meta:
        model = AsignacionDocente
        fields = ["id", "designacion", "division", "materia", "suplente_de", "etiqueta", "situacion_revista"]
        validators = []

    def validate(self, attrs):
        asignacion = AsignacionDocente(
            designacion=_valor(self, attrs, "designacion"),
            division=_valor(self, attrs, "division"),
            materia=_valor(self, attrs, "materia"),
            suplente_de=_valor(self, attrs, "suplente_de"),
        )
        repetida = AsignacionDocente.objects.filter(
            designacion=asignacion.designacion, division=asignacion.division, materia=asignacion.materia
        )
        if self.instance:
            repetida = repetida.exclude(pk=self.instance.pk)
        if repetida.exists():
            raise serializers.ValidationError("Esa asignación ya existe.")
        asignacion.clean()  # ValidationError de Django -> 400 vía manejador_excepciones
        return attrs
