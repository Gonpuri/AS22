from django.contrib import admin

from .models import Anio, Division, Materia, Orientacion

admin.site.register([Orientacion, Anio, Division, Materia])
