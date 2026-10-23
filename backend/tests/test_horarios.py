import pytest
from fastapi.testclient import TestClient
from rest_framework.authtoken.models import Token

from config.asgi import app

# TestClient ejecuta los endpoints en otro hilo: se necesita la base fuera de la transacción de prueba.
pytestmark = pytest.mark.django_db(transaction=True)
URL = "/api/horarios/bloques"


@pytest.fixture
def api_admin(admin_user):
    return TestClient(app, headers={"Authorization": f"Token {Token.objects.get_or_create(user=admin_user)[0].key}"})


@pytest.fixture
def api_comun(common_user):
    return TestClient(app, headers={"Authorization": f"Token {Token.objects.get_or_create(user=common_user)[0].key}"})


def _bloque(e, materia="matematica", **extra):
    return {"division": e["div"].pk, "materia": e[materia].pk, "dia": 1,
            "hora_inicio": "07:30:00", "hora_fin": "08:10:00", **extra}


def test_sin_credenciales(estructura):
    assert TestClient(app).get(URL).status_code == 401
    assert TestClient(app, headers={"Authorization": "Token falso"}).get(URL).status_code == 401


def test_usuario_comun_solo_lee(api_comun, estructura):
    assert api_comun.get(URL).status_code == 200
    assert api_comun.post(URL, json=_bloque(estructura)).status_code == 403


def test_crear_y_listar(api_admin, estructura):
    r = api_admin.post(URL, json=_bloque(estructura))
    assert r.status_code == 201
    assert r.json()["materia"] == estructura["matematica"].pk
    assert len(api_admin.get(URL).json()) == 1
    assert api_admin.get(URL, params={"division": 999}).json() == []
    assert api_admin.get(f"{URL}/{r.json()['id']}").status_code == 200


def test_hora_fin_posterior(api_admin, estructura):
    r = api_admin.post(URL, json=_bloque(estructura, hora_fin="07:30:00"))
    assert r.status_code == 422


def test_dia_fuera_de_rango(api_admin, estructura):
    assert api_admin.post(URL, json=_bloque(estructura, dia=6)).status_code == 422


def test_materia_debe_corresponder_a_la_division(api_admin, estructura):
    for materia in ("biologia", "historia"):
        r = api_admin.post(URL, json=_bloque(estructura, materia=materia))
        assert r.status_code == 422 and "no corresponde" in r.json()["detail"]
    assert api_admin.post(URL, json=_bloque(estructura, materia="contabilidad")).status_code == 201


def test_division_o_materia_inexistente(api_admin, estructura):
    assert api_admin.post(URL, json={**_bloque(estructura), "division": 999}).status_code == 422
    assert api_admin.post(URL, json={**_bloque(estructura), "materia": 999}).status_code == 422


def test_no_se_superponen_bloques(api_admin, estructura):
    api_admin.post(URL, json=_bloque(estructura))
    r = api_admin.post(URL, json=_bloque(estructura, materia="contabilidad", hora_inicio="08:00:00", hora_fin="08:40:00"))
    assert r.status_code == 422 and "superpone" in r.json()["detail"]
    # contiguo, o en otro día, es válido
    assert api_admin.post(URL, json=_bloque(estructura, materia="contabilidad", hora_inicio="08:10:00", hora_fin="08:50:00")).status_code == 201
    assert api_admin.post(URL, json=_bloque(estructura, dia=2)).status_code == 201


def test_actualizar_puede_mantener_su_propio_horario(api_admin, estructura):
    pk = api_admin.post(URL, json=_bloque(estructura)).json()["id"]
    r = api_admin.put(f"{URL}/{pk}", json=_bloque(estructura, materia="contabilidad", hora_fin="08:20:00"))
    assert r.status_code == 200 and r.json()["hora_fin"] == "08:20:00"
    assert api_admin.put(f"{URL}/9999", json=_bloque(estructura)).status_code == 404


def test_eliminar(api_admin, estructura):
    pk = api_admin.post(URL, json=_bloque(estructura)).json()["id"]
    assert api_admin.delete(f"{URL}/{pk}").status_code == 204
    assert api_admin.get(f"{URL}/{pk}").status_code == 404


def test_division_con_horario_no_se_elimina(admin_client, api_admin, estructura):
    api_admin.post(URL, json=_bloque(estructura))
    assert admin_client.delete(f"/api/academico/divisiones/{estructura['div'].pk}/").status_code == 409


def test_django_se_sirve_desde_la_misma_app(admin_user):
    r = TestClient(app).post("/api/auth/login/", data={"username": "admin", "password": "clave-segura-123"})
    assert r.status_code == 200 and "token" in r.json()


def _docente(estructura, materia, apellido, dni, situacion="titular", suplente_de=None):
    from apps.rrhh.models import AsignacionDocente, Designacion, Personal
    persona = Personal.objects.create(apellido=apellido, nombre="Ana", dni=dni)
    des = Designacion.objects.create(personal=persona, categoria="profesor", turno="tarde", situacion_revista=situacion)
    return AsignacionDocente.objects.create(
        designacion=des, division=estructura["div"], materia=estructura[materia], suplente_de=suplente_de
    )


def test_grilla_muestra_al_suplente_con_el_docente_que_reemplaza(api_admin, estructura):
    api_admin.post(URL, json=_bloque(estructura))
    api_admin.post(URL, json=_bloque(estructura, materia="contabilidad", dia=2))
    titular = _docente(estructura, "matematica", "Nievas", "30000001", situacion="titular_interino")
    suplente = _docente(estructura, "matematica", "Ramírez", "30000002", situacion="suplente", suplente_de=titular)
    r = api_admin.get("/api/horarios/grilla", params={"division": estructura["div"].pk})
    assert r.status_code == 200
    datos = r.json()
    assert datos["division"] == {"id": estructura["div"].pk, "anio": 4, "nombre": "1ª", "orientacion": "Economía"}
    por_materia = {b["materia"]: b for b in datos["bloques"]}
    assert por_materia["Matemática"]["docentes"] == [
        {"personal_id": titular.designacion.personal_id, "nombre": "Nievas, Ana",
         "situacion_revista": "Titular interino", "es_suplente": False, "suplente_de": None},
        {"personal_id": suplente.designacion.personal_id, "nombre": "Ramírez, Ana",
         "situacion_revista": "Suplente", "es_suplente": True,
         "suplente_de": {"personal_id": titular.designacion.personal_id, "nombre": "Nievas, Ana",
                         "situacion_revista": "Titular interino"}},
    ]
    assert por_materia["Contabilidad"]["docentes"] == []


def test_grilla_suplente_sin_titular_indicado_y_orden(api_admin, estructura):
    api_admin.post(URL, json=_bloque(estructura))
    _docente(estructura, "matematica", "Aaa", "30000003", situacion="suplente")  # dato anterior a la regla
    _docente(estructura, "matematica", "Zzz", "30000004", situacion="titular")
    bloque = api_admin.get("/api/horarios/grilla", params={"division": estructura["div"].pk}).json()["bloques"][0]
    docentes = bloque["docentes"]
    assert [d["nombre"] for d in docentes] == ["Zzz, Ana", "Aaa, Ana"]  # los suplentes van después
    assert docentes[1]["es_suplente"] is True and docentes[1]["suplente_de"] is None


def test_grilla_division_inexistente_y_sin_login(api_admin, estructura):
    assert api_admin.get("/api/horarios/grilla", params={"division": 999}).status_code == 404
    assert TestClient(app).get("/api/horarios/grilla", params={"division": 1}).status_code == 401


def test_cors_en_las_rutas_de_fastapi(api_admin, estructura):
    origen = "http://localhost:5173"
    r = api_admin.get(URL, headers={"Origin": origen})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == origen
    pre = api_admin.options(URL, headers={
        "Origin": origen, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert pre.status_code == 200 and "authorization" in pre.headers["access-control-allow-headers"].lower()
    assert api_admin.get(URL, headers={"Origin": "https://intruso.example"}).headers.get("access-control-allow-origin") is None


def test_cors_sin_cabeceras_duplicadas_en_las_rutas_de_django(estructura):
    # Django (corsheaders) y FastAPI configuran CORS: el navegador rechaza la cabecera repetida.
    r = TestClient(app).get("/api/academico/anios/", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get_list("access-control-allow-origin") == ["http://localhost:5173"]


def _preceptor_del_curso(estructura, apellido, dni, situacion="titular", suplente_de=None):
    from apps.rrhh.models import AsignacionPreceptor, Designacion, Personal
    persona = Personal.objects.create(apellido=apellido, nombre="Marcela", dni=dni)
    des = Designacion.objects.create(personal=persona, categoria="preceptor", turno="tarde", situacion_revista=situacion)
    return AsignacionPreceptor.objects.create(designacion=des, division=estructura["div"], suplente_de=suplente_de)


def test_grilla_incluye_al_preceptor_y_a_su_suplente(api_admin, estructura):
    titular = _preceptor_del_curso(estructura, "Furchs", "50000001")
    suplente = _preceptor_del_curso(estructura, "Zárate", "50000002", situacion="suplente", suplente_de=titular)
    r = api_admin.get("/api/horarios/grilla", params={"division": estructura["div"].pk})
    assert r.status_code == 200
    assert r.json()["preceptores"] == [
        {"personal_id": titular.designacion.personal_id, "nombre": "Furchs, Marcela",
         "situacion_revista": "Titular", "es_suplente": False, "suplente_de": None},
        {"personal_id": suplente.designacion.personal_id, "nombre": "Zárate, Marcela",
         "situacion_revista": "Suplente", "es_suplente": True,
         "suplente_de": {"personal_id": titular.designacion.personal_id, "nombre": "Furchs, Marcela",
                         "situacion_revista": "Titular"}},
    ]


def test_grilla_sin_preceptor_y_solo_los_del_curso(api_admin, estructura):
    from apps.academico.models import Division
    assert api_admin.get("/api/horarios/grilla", params={"division": estructura["div"].pk}).json()["preceptores"] == []
    otro_curso = Division.objects.create(anio=estructura["a5"], nombre="1ª")
    otro = _preceptor_del_curso(estructura, "Otra", "50000003")
    otro.division = otro_curso
    otro.save()
    assert api_admin.get("/api/horarios/grilla", params={"division": estructura["div"].pk}).json()["preceptores"] == []
    assert len(api_admin.get("/api/horarios/grilla", params={"division": otro_curso.pk}).json()["preceptores"]) == 1
