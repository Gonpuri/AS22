from rest_framework.permissions import SAFE_METHODS, BasePermission


def es_administrador(user) -> bool:
    """Administrador: usuario activo con permisos de staff o superusuario."""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


class LecturaAutenticadaEscrituraAdmin(BasePermission):
    """Cualquier usuario autenticado consulta; solo los administradores modifican."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or es_administrador(user)


class SoloAdministrador(BasePermission):
    def has_permission(self, request, view):
        return es_administrador(request.user)
