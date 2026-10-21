from rest_framework import viewsets

from .models import AsignacionDocente, Designacion, Personal
from .serializers import AsignacionDocenteSerializer, DesignacionSerializer, PersonalSerializer


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
