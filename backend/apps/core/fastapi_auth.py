"""Autenticación por token (la misma de DRF) para los módulos implementados con FastAPI."""
from fastapi import Depends, Header, HTTPException, status
from rest_framework.authtoken.models import Token

from .permissions import es_administrador


def usuario_actual(authorization: str | None = Header(default=None)):
    if authorization:
        tipo, _, valor = authorization.partition(" ")
        if tipo.lower() == "token" and valor:
            token = Token.objects.select_related("user").filter(key=valor.strip()).first()
            if token and token.user.is_active:
                return token.user
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas o ausentes.")


def administrador(user=Depends(usuario_actual)):
    if not es_administrador(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo los administradores pueden modificar.")
    return user
