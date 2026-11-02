import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured

from config import settings


def _recargar(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    return settings._base_de_datos()


def test_tolera_espacios_y_comillas(monkeypatch):
    cfg = _recargar(monkeypatch, '  "postgresql://u:p@host:5432/escuela"\n')
    assert (cfg["NAME"], cfg["HOST"], cfg["USER"]) == ("escuela", "host", "u")


def test_url_invalida_explica_que_revisar_sin_mostrar_la_clave(monkeypatch):
    with pytest.raises(ImproperlyConfigured) as e:
        _recargar(monkeypatch, "postgresql://u:sec ret#@host:99999999/db")
    assert "DATABASE_URL" in str(e.value) and "sec ret" not in str(e.value)


def test_sin_variable_usa_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert settings._base_de_datos()["ENGINE"].endswith("sqlite3")
