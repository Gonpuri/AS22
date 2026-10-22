import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Crea el administrador inicial con ADMIN_USERNAME y ADMIN_PASSWORD (variables de entorno). "
        "No hace nada si faltan o si el usuario ya existe; nunca cambia la contraseña de un usuario existente."
    )

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME")
        password = os.environ.get("ADMIN_PASSWORD")
        if not (username and password):
            self.stdout.write("ADMIN_USERNAME/ADMIN_PASSWORD no definidas: no se crea administrador.")
            return
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"El usuario '{username}' ya existe: no se modifica.")
            return
        User.objects.create_superuser(username=username, password=password)
        self.stdout.write(self.style.SUCCESS(f"Administrador '{username}' creado."))
