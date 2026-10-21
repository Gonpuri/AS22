import pytest

from apps.rrhh.models import Designacion, Personal

pytestmark = pytest.mark.django_db
PERSONAL = "/api/rrhh/personal/"
DESIGNACIONES = "/api/rrhh/designaciones/"
ASIGNACIONES = "/api/rrhh/asignaciones/"


def _datos(**extra):
    return {"apellido": "Pérez", "nombre": "Ana", "dni": "30123456", **extra}


@pytest.fixture
def ana(db):
    return Personal.objects.create(**_datos())


def _designar(ana, categoria="profesor", turno="manana"):
    return Designacion.objects.create(
        personal=ana, categoria=categoria, turno=turno, situacion_revista="titular"
    )


def test_permisos(common_client, admin_client):
    assert common_client.get(PERSONAL).status_code == 200
    assert common_client.post(PERSONAL, _datos()).status_code == 403
    assert admin_client.post(PERSONAL, _datos()).status_code == 201


def test_dni_valido_y_unico(admin_client):
    assert admin_client.post(PERSONAL, _datos(dni="abc")).status_code == 400
    assert admin_client.post(PERSONAL, _datos(dni="123")).status_code == 400
    assert admin_client.post(PERSONAL, _datos()).status_code == 201
    assert admin_client.post(PERSONAL, _datos(apellido="Otro")).status_code == 400


def test_datos_completos_edicion_y_baja(admin_client):
    r = admin_client.post(PERSONAL, _datos(
        cuil="20-30123456-7", fecha_nacimiento="1980-05-01", domicilio="Calle 1", telefono="1122334455",
        email="ana@escuela.edu.ar", fecha_ingreso="2010-03-01",
    ))
    assert r.status_code == 201 and r.data["activo"] is True and r.data["categorias"] == []
    pk = r.data["id"]
    assert admin_client.patch(f"{PERSONAL}{pk}/", {"activo": False}).data["activo"] is False
    assert admin_client.delete(f"{PERSONAL}{pk}/").status_code == 204


@pytest.mark.parametrize("categoria", ["preceptor", "directivo", "profesor", "ematp", "otro"])
def test_categorias_validas(admin_client, ana, categoria):
    r = admin_client.post(DESIGNACIONES, {"personal": ana.pk, "categoria": categoria, "turno": "tarde", "situacion_revista": "titular"})
    assert r.status_code == 201


def test_categoria_o_turno_invalidos(admin_client, ana):
    assert admin_client.post(DESIGNACIONES, {"personal": ana.pk, "categoria": "conserje", "turno": "tarde", "situacion_revista": "titular"}).status_code == 400
    assert admin_client.post(DESIGNACIONES, {"personal": ana.pk, "categoria": "preceptor", "turno": "noche", "situacion_revista": "titular"}).status_code == 400


def test_preceptor_en_un_turno_y_profesor_en_otro(admin_client, ana):
    assert admin_client.post(DESIGNACIONES, {"personal": ana.pk, "categoria": "preceptor", "turno": "manana", "situacion_revista": "titular"}).status_code == 201
    assert admin_client.post(DESIGNACIONES, {"personal": ana.pk, "categoria": "profesor", "turno": "tarde", "situacion_revista": "titular"}).status_code == 201
    persona = admin_client.get(f"{PERSONAL}{ana.pk}/").data
    assert persona["categorias"] == ["preceptor", "profesor"]


def test_designacion_repetida(admin_client, ana):
    d = {"personal": ana.pk, "categoria": "preceptor", "turno": "manana", "situacion_revista": "titular"}
    admin_client.post(DESIGNACIONES, d)
    r = admin_client.post(DESIGNACIONES, {**d, "cargo": "otro"})
    assert r.status_code == 400


def test_filtrar_personal_por_categoria_y_turno(admin_client, ana):
    beto = Personal.objects.create(**_datos(apellido="Gómez", dni="30999999"))
    _designar(ana, "profesor", "manana")
    _designar(ana, "preceptor", "tarde")
    _designar(beto, "ematp", "tarde")
    assert len(admin_client.get(PERSONAL).data) == 2
    assert [p["dni"] for p in admin_client.get(PERSONAL, {"categoria": "ematp"}).data] == ["30999999"]
    assert [p["dni"] for p in admin_client.get(PERSONAL, {"categoria": "preceptor", "turno": "tarde", "situacion_revista": "titular"}).data] == ["30123456"]
    assert admin_client.get(PERSONAL, {"categoria": "preceptor", "turno": "manana", "situacion_revista": "titular"}).data == []


def test_filtrar_designaciones(admin_client, ana):
    _designar(ana, "profesor", "manana")
    _designar(ana, "preceptor", "tarde")
    assert len(admin_client.get(DESIGNACIONES, {"personal": ana.pk}).data) == 2
    assert len(admin_client.get(DESIGNACIONES, {"turno": "tarde", "situacion_revista": "titular"}).data) == 1


def test_profesor_con_varios_cursos_y_materias(admin_client, ana, estructura):
    from apps.academico.models import Division
    d2 = Division.objects.create(anio=estructura["a5"], nombre="1ª")
    prof = _designar(ana)
    combos = [(estructura["div"], estructura["matematica"]), (estructura["div"], estructura["contabilidad"]),
              (d2, estructura["matematica"])]
    for div, mat in combos:
        r = admin_client.post(ASIGNACIONES, {"designacion": prof.pk, "division": div.pk, "materia": mat.pk})
        assert r.status_code == 201
    assert len(admin_client.get(ASIGNACIONES, {"designacion": prof.pk}).data) == 3
    assert len(admin_client.get(ASIGNACIONES, {"division": d2.pk}).data) == 1


def test_ematp_tambien_puede_tener_asignaciones(admin_client, ana, estructura):
    d = _designar(ana, "ematp")
    r = admin_client.post(ASIGNACIONES, {"designacion": d.pk, "division": estructura["div"].pk, "materia": estructura["matematica"].pk})
    assert r.status_code == 201


def test_solo_docentes_tienen_asignaciones(admin_client, ana, estructura):
    prec = _designar(ana, "preceptor")
    r = admin_client.post(ASIGNACIONES, {"designacion": prec.pk, "division": estructura["div"].pk, "materia": estructura["matematica"].pk})
    assert r.status_code == 400


def test_materia_debe_corresponder_a_la_division(admin_client, ana, estructura):
    prof = _designar(ana)
    for materia in ("biologia", "historia"):
        r = admin_client.post(ASIGNACIONES, {"designacion": prof.pk, "division": estructura["div"].pk, "materia": estructura[materia].pk})
        assert r.status_code == 400


def test_asignacion_repetida(admin_client, ana, estructura):
    prof = _designar(ana)
    d = {"designacion": prof.pk, "division": estructura["div"].pk, "materia": estructura["matematica"].pk}
    assert admin_client.post(ASIGNACIONES, d).status_code == 201
    assert admin_client.post(ASIGNACIONES, d).status_code == 400


def test_no_se_cambia_a_no_docente_con_asignaciones(admin_client, ana, estructura):
    prof = _designar(ana)
    admin_client.post(ASIGNACIONES, {"designacion": prof.pk, "division": estructura["div"].pk, "materia": estructura["matematica"].pk})
    assert admin_client.patch(f"{DESIGNACIONES}{prof.pk}/", {"categoria": "preceptor"}).status_code == 400
    assert admin_client.patch(f"{DESIGNACIONES}{prof.pk}/", {"turno": "tarde", "situacion_revista": "titular"}).status_code == 200


def test_eliminar_persona_elimina_designaciones_y_asignaciones(admin_client, ana, estructura):
    prof = _designar(ana)
    admin_client.post(ASIGNACIONES, {"designacion": prof.pk, "division": estructura["div"].pk, "materia": estructura["matematica"].pk})
    assert admin_client.delete(f"{PERSONAL}{ana.pk}/").status_code == 204
    assert admin_client.get(ASIGNACIONES).data == []


def test_division_con_docentes_no_se_elimina(admin_client, ana, estructura):
    prof = _designar(ana)
    admin_client.post(ASIGNACIONES, {"designacion": prof.pk, "division": estructura["div"].pk, "materia": estructura["matematica"].pk})
    assert admin_client.delete(f"/api/academico/divisiones/{estructura['div'].pk}/").status_code == 409


@pytest.mark.parametrize("situacion", ["titular", "titular_interino", "suplente", "provisional"])
def test_situaciones_de_revista_validas(admin_client, ana, situacion):
    d = {"personal": ana.pk, "categoria": "profesor", "turno": "tarde", "situacion_revista": situacion}
    r = admin_client.post(DESIGNACIONES, d)
    assert r.status_code == 201 and r.data["situacion_revista"] == situacion


def test_situacion_de_revista_obligatoria_y_valida(admin_client, ana):
    d = {"personal": ana.pk, "categoria": "profesor", "turno": "tarde"}
    assert admin_client.post(DESIGNACIONES, d).status_code == 400
    assert admin_client.post(DESIGNACIONES, {**d, "situacion_revista": "interina"}).status_code == 400


def test_misma_persona_distinta_situacion_segun_turno(admin_client, ana):
    base = {"personal": ana.pk, "categoria": "profesor"}
    assert admin_client.post(DESIGNACIONES, {**base, "turno": "manana", "situacion_revista": "titular"}).status_code == 201
    assert admin_client.post(DESIGNACIONES, {**base, "turno": "tarde", "situacion_revista": "suplente"}).status_code == 201
    assert len(admin_client.get(DESIGNACIONES, {"situacion_revista": "suplente"}).data) == 1
