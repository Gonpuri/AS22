import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, override_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from config.cors import desde_entorno, opciones_fastapi

PATRON = r"^https://frontend(-[a-z0-9-]+)?-gonpuri1\.vercel\.app$"
PRINCIPAL = "https://frontend-gonpuri1.vercel.app"
RAMA = "https://frontend-git-main-gonpuri1.vercel.app"
DESPLIEGUE = "https://frontend-8k2x9abcd-gonpuri1.vercel.app"
AJENOS = ["https://frontend-gonpuri1.vercel.app.evil.com", "https://otro-gonpuri1.vercel.app", "http://frontend-gonpuri1.vercel.app"]


def test_lista_de_origenes_se_limpia_y_el_regex_es_opcional():
    origenes, patron = desde_entorno({"CORS_ALLOWED_ORIGINS": f" {PRINCIPAL} , {RAMA},,"})
    assert origenes == [PRINCIPAL, RAMA] and patron is None


def test_valores_por_defecto():
    assert desde_entorno({}) == (["http://localhost:5173"], None)


def test_regex_valido_y_regex_roto():
    assert desde_entorno({"CORS_ALLOWED_ORIGIN_REGEX": PATRON})[1] == PATRON
    with pytest.raises(ImproperlyConfigured, match="CORS_ALLOWED_ORIGIN_REGEX"):
        desde_entorno({"CORS_ALLOWED_ORIGIN_REGEX": "(sin cerrar"})


def _app_fastapi(origenes, patron):
    app = FastAPI()
    app.add_middleware(CORSMiddleware, **opciones_fastapi(origenes, patron))

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


@pytest.mark.parametrize("origen, permitido", [
    (PRINCIPAL, True), (RAMA, True), (DESPLIEGUE, True),
    *[(o, False) for o in AJENOS],
])
def test_fastapi_acepta_las_direcciones_del_proyecto_y_nada_mas(origen, permitido):
    r = _app_fastapi([], PATRON).get("/ping", headers={"Origin": origen})
    assert (r.headers.get("access-control-allow-origin") == origen) is permitido


def test_fastapi_sigue_aceptando_origenes_exactos_sin_regex():
    cliente = _app_fastapi([PRINCIPAL], None)
    assert cliente.get("/ping", headers={"Origin": PRINCIPAL}).headers["access-control-allow-origin"] == PRINCIPAL
    assert "access-control-allow-origin" not in cliente.get("/ping", headers={"Origin": RAMA}).headers


@pytest.mark.django_db
@pytest.mark.parametrize("origen, permitido", [(RAMA, True), (DESPLIEGUE, True), (AJENOS[0], False)])
def test_django_acepta_las_direcciones_del_proyecto(origen, permitido):
    with override_settings(CORS_ALLOWED_ORIGINS=[PRINCIPAL], CORS_ALLOWED_ORIGIN_REGEXES=[PATRON]):
        r = Client().options(
            "/api/auth/login/", HTTP_ORIGIN=origen, HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )
    assert (r.headers.get("access-control-allow-origin") == origen) is permitido
