from django.contrib import admin

from .models import AsignacionDocente, AsignacionPreceptor, Designacion, Personal

admin.site.register([Personal, Designacion, AsignacionDocente, AsignacionPreceptor])
