import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.academico.models import Anio, Division, Materia, Orientacion


def _cliente(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.get_or_create(user=user)[0].key}")
    return c


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_user("admin", password="clave-segura-123", is_staff=True)


@pytest.fixture
def common_user(db):
    return get_user_model().objects.create_user("comun", password="clave-segura-123")


@pytest.fixture
def admin_client(admin_user):
    return _cliente(admin_user)


@pytest.fixture
def common_client(common_user):
    return _cliente(common_user)


@pytest.fixture
def estructura(db):
    """4° año con orientación Economía; materias: una común al año, una de la orientación, una de otro año."""
    eco = Orientacion.objects.create(nombre="Economía")
    nat = Orientacion.objects.create(nombre="Naturales")
    a4 = Anio.objects.create(numero=4)
    a5 = Anio.objects.create(numero=5)
    div = Division.objects.create(anio=a4, orientacion=eco, nombre="1ª")
    matematica = Materia.objects.create(nombre="Matemática")
    matematica.anios.add(a4, a5)
    contabilidad = Materia.objects.create(nombre="Contabilidad")
    contabilidad.anios.add(a4)
    contabilidad.orientaciones.add(eco)
    biologia = Materia.objects.create(nombre="Biología")
    biologia.anios.add(a4)
    biologia.orientaciones.add(nat)
    historia = Materia.objects.create(nombre="Historia")
    historia.anios.add(a5)
    return dict(eco=eco, nat=nat, a4=a4, a5=a5, div=div, matematica=matematica,
                contabilidad=contabilidad, biologia=biologia, historia=historia)
