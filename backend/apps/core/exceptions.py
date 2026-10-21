from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def manejador_excepciones(exc, context):
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "No se puede eliminar: hay registros que dependen de este."},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(exc.message_dict if hasattr(exc, "error_dict") else exc.messages)
    return exception_handler(exc, context)
