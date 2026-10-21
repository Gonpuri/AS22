from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .modulos import listar_modulos
from .permissions import SoloAdministrador
from .serializers import UsuarioSerializer

User = get_user_model()


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = User.objects.order_by("username")
    serializer_class = UsuarioSerializer
    permission_classes = [SoloAdministrador]


@api_view(["GET"])
def yo(request):
    return Response(UsuarioSerializer(request.user).data)


@api_view(["GET"])
def modulos(request):
    return Response(listar_modulos())
