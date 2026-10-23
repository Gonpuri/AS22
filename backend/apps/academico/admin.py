from django.contrib import admin

from .models import Anio, Division, Materia, Orientacion


@admin.register(Orientacion)
class OrientacionAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Anio)
class AnioAdmin(admin.ModelAdmin):
    list_display = ["__str__"]


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "anio", "orientacion", "turno"]
    list_filter = ["anio", "orientacion", "turno"]
    search_fields = ["nombre"]


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "años", "orientaciones_asociadas"]
    list_filter = ["anios", "orientaciones"]
    search_fields = ["nombre"]
    filter_horizontal = ["anios", "orientaciones"]

    @admin.display(description="Años")
    def años(self, obj):
        return ", ".join(str(a) for a in obj.anios.all()) or "-"

    @admin.display(description="Orientaciones")
    def orientaciones_asociadas(self, obj):
        return ", ".join(o.nombre for o in obj.orientaciones.all()) or "Todas"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("anios", "orientaciones")
