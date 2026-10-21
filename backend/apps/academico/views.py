from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Anio, Division, Materia, Orientacion
from .serializers import (
    AnioSerializer,
    DivisionSerializer,
    MateriaSerializer,
    OrientacionSerializer,
)


class OrientacionViewSet(viewsets.ModelViewSet):
    queryset = Orientacion.objects.all()
    serializer_class = OrientacionSerializer


class AnioViewSet(viewsets.ModelViewSet):
    queryset = Anio.objects.all()
    serializer_class = AnioSerializer


class DivisionViewSet(viewsets.ModelViewSet):
    queryset = Division.objects.select_related("anio", "orientacion")
    serializer_class = DivisionSerializer

    @action(detail=True, methods=["get"])
    def materias(self, request, pk=None):
        return Response(MateriaSerializer(self.get_object().materias(), many=True).data)


class MateriaViewSet(viewsets.ModelViewSet):
    queryset = Materia.objects.prefetch_related("anios", "orientaciones")
    serializer_class = MateriaSerializer
