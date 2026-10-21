from rest_framework.permissions import SAFE_METHODS, BasePermission


class LecturaAutenticadaEscrituraAdmin(BasePermission):
    """Cualquier usuario autenticado consulta; solo los administradores modifican."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or user.is_staff


class SoloAdministrador(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)
