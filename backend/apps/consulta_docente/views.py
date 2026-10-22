from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from .services import MAX_DIAS, buscar_docente, clases_del_docente, normalizar_cuil


class ConsultaSerializer(serializers.Serializer):
    cuil = serializers.CharField()
    desde = serializers.DateField()
    hasta = serializers.DateField(required=False)

    def validate_cuil(self, value):
        digitos = normalizar_cuil(value)
        if len(digitos) != 11:
            raise serializers.ValidationError("El CUIL debe tener 11 dígitos.")
        return digitos

    def validate(self, attrs):
        attrs.setdefault("hasta", attrs["desde"])  # sin "hasta": se consulta un solo día
        if attrs["hasta"] < attrs["desde"]:
            raise serializers.ValidationError({"hasta": "La fecha final no puede ser anterior a la inicial."})
        if (attrs["hasta"] - attrs["desde"]).days + 1 > MAX_DIAS:
            raise serializers.ValidationError({"hasta": f"El intervalo no puede superar {MAX_DIAS} días."})
        return attrs


@api_view(["GET"])
def consulta(request):
    """GET /api/consulta_docente/?cuil=…&desde=AAAA-MM-DD[&hasta=AAAA-MM-DD]"""
    datos = ConsultaSerializer(data=request.query_params)
    datos.is_valid(raise_exception=True)
    docente = buscar_docente(datos.validated_data["cuil"])
    if docente is None:
        raise NotFound("No hay personal registrado con ese CUIL.")
    return Response(clases_del_docente(docente, datos.validated_data["desde"], datos.validated_data["hasta"]))
