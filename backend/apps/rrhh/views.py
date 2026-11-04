from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from . import importar_excel

from .models import AsignacionDocente, AsignacionPreceptor, Designacion, Personal
from .serializers import (
    AsignacionDocenteSerializer,
    AsignacionPreceptorSerializer,
    DesignacionSerializer,
    PersonalSerializer,
)


def _filtrar(qs, request, **filtros):
    """Filtra por query string. Se aplica en un solo filter() para que las condiciones sobre una
    misma relación (p. ej. categoría y turno de la designación) valgan para la misma fila."""
    condiciones = {
        lookup: request.query_params[parametro]
        for parametro, lookup in filtros.items()
        if request.query_params.get(parametro)
    }
    return qs.filter(**condiciones).distinct()


class PersonalViewSet(viewsets.ModelViewSet):
    serializer_class = PersonalSerializer

    def get_queryset(self):
        qs = Personal.objects.prefetch_related("designaciones")
        return _filtrar(qs, self.request, categoria="designaciones__categoria", turno="designaciones__turno")

    @action(detail=False, methods=["post"], url_path="importar-excel/previsualizar",
            parser_classes=[MultiPartParser, FormParser])
    def previsualizar_excel(self, request):
        """Lee una planilla Excel y propone qué se crearía o actualizaría (por DNI). No guarda nada."""
        archivo = request.FILES.get("archivo")
        if archivo is None:
            return Response({"detail": "Falta el archivo."}, status=status.HTTP_400_BAD_REQUEST)
        if archivo.size > importar_excel.MAX_BYTES:
            return Response({"detail": "La planilla supera los 5 MB."}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        try:
            filas = importar_excel.leer_planilla(archivo.read())
        except importar_excel.ErrorPlanilla as e:
            return Response({"detail": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response({"filas": filas})

    @action(detail=False, methods=["post"], url_path="importar-excel", parser_classes=[JSONParser])
    def guardar_excel(self, request):
        """Guarda (todo o nada) las filas revisadas: crea las personas nuevas y actualiza las existentes por DNI."""
        try:
            return Response(importar_excel.aplicar(request.data.get("filas", [])), status=status.HTTP_201_CREATED)
        except importar_excel.ErrorPlanilla as e:
            return Response({"detail": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class DesignacionViewSet(viewsets.ModelViewSet):
    serializer_class = DesignacionSerializer

    def get_queryset(self):
        qs = Designacion.objects.select_related("personal")
        return _filtrar(qs, self.request, personal="personal", categoria="categoria", turno="turno",
                        situacion_revista="situacion_revista")


class AsignacionDocenteViewSet(viewsets.ModelViewSet):
    serializer_class = AsignacionDocenteSerializer

    def get_queryset(self):
        qs = AsignacionDocente.objects.select_related("designacion__personal", "division", "materia")
        return _filtrar(qs, self.request, designacion="designacion", division="division", materia="materia")


class AsignacionPreceptorViewSet(viewsets.ModelViewSet):
    serializer_class = AsignacionPreceptorSerializer

    def get_queryset(self):
        qs = AsignacionPreceptor.objects.select_related("designacion__personal", "division__anio")
        return _filtrar(qs, self.request, designacion="designacion", division="division")
