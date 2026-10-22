import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Crea el administrador inicial con ADMIN_USERNAME y ADMIN_PASSWORD (variables de entorno). "
        "No hace nada si faltan. Si el usuario ya existe no lo modifica, salvo que ADMIN_RESET_PASSWORD=1: "
        "en ese caso restablece su contraseña y lo deja activo y como administrador."
    )

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME")
        password = os.environ.get("ADMIN_PASSWORD")
        if not (username and password):
            self.stdout.write("ADMIN_USERNAME/ADMIN_PASSWORD no definidas: no se crea administrador.")
            return
        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user is None:
            User.objects.create_superuser(username=username, password=password)
            self.stdout.write(self.style.SUCCESS(f"Administrador '{username}' creado."))
        elif os.environ.get("ADMIN_RESET_PASSWORD") == "1":
            user.set_password(password)
            user.is_active = user.is_staff = user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Contraseña de '{username}' restablecida."))
        else:
            self.stdout.write(f"El usuario '{username}' ya existe: no se modifica.")
