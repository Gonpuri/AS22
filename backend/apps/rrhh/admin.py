from django.contrib import admin

from .models import AsignacionDocente, Designacion, Personal

admin.site.register([Personal, Designacion, AsignacionDocente])
