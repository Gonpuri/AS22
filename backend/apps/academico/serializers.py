from rest_framework import serializers

from .models import Anio, Division, Materia, Orientacion


class OrientacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orientacion
        fields = ["id", "nombre"]


class AnioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anio
        fields = ["id", "numero"]

    def validate_numero(self, value):
        if value < 1:
            raise serializers.ValidationError("El año debe ser mayor o igual a 1.")
        return value


class DivisionSerializer(serializers.ModelSerializer):
    etiqueta = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Division
        fields = ["id", "anio", "orientacion", "nombre", "turno", "etiqueta"]
        validators = []  # la unicidad (anio, nombre) se valida abajo con mensaje en español

    def validate(self, attrs):
        if not attrs.get("turno", getattr(self.instance, "turno", "")):
            raise serializers.ValidationError({"turno": "El turno es obligatorio."})
        anio = attrs.get("anio", getattr(self.instance, "anio", None))
        nombre = attrs.get("nombre", getattr(self.instance, "nombre", None))
        repetida = Division.objects.filter(anio=anio, nombre=nombre)
        if self.instance:
            repetida = repetida.exclude(pk=self.instance.pk)
        if repetida.exists():
            raise serializers.ValidationError("Ya existe una división con ese nombre en el año.")
        return attrs


class MateriaSerializer(serializers.ModelSerializer):
    anios = serializers.PrimaryKeyRelatedField(many=True, queryset=Anio.objects.all(), required=False)
    orientaciones = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Orientacion.objects.all(), required=False
    )

    class Meta:
        model = Materia
        fields = ["id", "nombre", "anios", "orientaciones"]
