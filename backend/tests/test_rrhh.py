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


# --- Suplentes: a quién reemplazan ---------------------------------------------------------------

def _asignar(cliente, designacion, e, materia="matematica", **extra):
    return cliente.post(ASIGNACIONES, {"designacion": designacion.pk, "division": e["div"].pk,
                                       "materia": e[materia].pk, **extra})


def _persona(dni, apellido="Otro"):
    return Personal.objects.create(apellido=apellido, nombre="Ana", dni=dni)


def _suplente(dni):
    return Designacion.objects.create(
        personal=_persona(dni), categoria="profesor", turno="tarde", situacion_revista="suplente"
    )


@pytest.mark.parametrize("situacion", ["titular", "titular_interino", "provisional"])
def test_suplente_indica_a_quien_reemplaza(admin_client, ana, estructura, situacion):
    titular = Designacion.objects.create(personal=ana, categoria="profesor", turno="tarde", situacion_revista=situacion)
    a_titular = _asignar(admin_client, titular, estructura).data
    r = _asignar(admin_client, _suplente("40000001"), estructura, suplente_de=a_titular["id"])
    assert r.status_code == 201 and r.data["suplente_de"] == a_titular["id"]
    assert r.data["situacion_revista"] == "suplente" and "Matemática" in r.data["etiqueta"]


def test_el_suplente_debe_indicar_a_quien_reemplaza(admin_client, estructura):
    r = _asignar(admin_client, _suplente("40000001"), estructura)
    assert r.status_code == 400 and "reemplaza" in str(r.data)


def test_solo_un_suplente_puede_reemplazar(admin_client, ana, estructura):
    a_titular = _asignar(admin_client, _designar(ana), estructura).data
    otro = Designacion.objects.create(
        personal=_persona("40000001"), categoria="profesor", turno="tarde", situacion_revista="titular"
    )
    assert _asignar(admin_client, otro, estructura, suplente_de=a_titular["id"]).status_code == 400


def test_el_reemplazado_debe_ser_del_mismo_curso_y_materia(admin_client, ana, estructura):
    a_mate = _asignar(admin_client, _designar(ana), estructura).data
    r = _asignar(admin_client, _suplente("40000001"), estructura, materia="contabilidad", suplente_de=a_mate["id"])
    assert r.status_code == 400 and "mismo curso y materia" in str(r.data)


def test_no_se_reemplaza_a_otro_suplente_ni_a_uno_mismo(admin_client, ana, estructura):
    a_titular = _asignar(admin_client, _designar(ana), estructura).data
    a_sup1 = _asignar(admin_client, _suplente("40000001"), estructura, suplente_de=a_titular["id"]).data
    assert _asignar(admin_client, _suplente("40000002"), estructura, suplente_de=a_sup1["id"]).status_code == 400
    # una persona con dos designaciones (titular y suplente) no puede reemplazarse a sí misma
    mismo = Designacion.objects.create(personal=ana, categoria="profesor", turno="tarde", situacion_revista="suplente")
    assert _asignar(admin_client, mismo, estructura, suplente_de=a_titular["id"]).status_code == 400


def test_no_se_borra_a_un_titular_que_tiene_suplentes(admin_client, ana, estructura):
    a_titular = _asignar(admin_client, _designar(ana), estructura).data
    _asignar(admin_client, _suplente("40000001"), estructura, suplente_de=a_titular["id"])
    assert admin_client.delete(f"{ASIGNACIONES}{a_titular['id']}/").status_code == 409
    assert admin_client.delete(f"{PERSONAL}{ana.pk}/").status_code == 409


def test_cambios_de_situacion_que_dejarian_datos_incoherentes(admin_client, ana, estructura):
    titular = _designar(ana)
    a_titular = _asignar(admin_client, titular, estructura).data
    sup = _suplente("40000001")
    _asignar(admin_client, sup, estructura, suplente_de=a_titular["id"])
    # el suplente no puede dejar de serlo mientras reemplaza a alguien
    assert admin_client.patch(f"{DESIGNACIONES}{sup.pk}/", {"situacion_revista": "titular"}).status_code == 400
    # el titular no puede pasar a suplente mientras tiene suplentes
    assert admin_client.patch(f"{DESIGNACIONES}{titular.pk}/", {"situacion_revista": "suplente"}).status_code == 400
    assert admin_client.patch(f"{DESIGNACIONES}{titular.pk}/", {"situacion_revista": "provisional"}).status_code == 200


def test_listado_de_asignaciones_incluye_etiqueta_y_situacion(admin_client, ana, estructura):
    _asignar(admin_client, _designar(ana), estructura)
    fila = admin_client.get(ASIGNACIONES).data[0]
    assert fila["situacion_revista"] == "titular" and fila["suplente_de"] is None
    assert "Pérez, Ana" in fila["etiqueta"] and "4° 1ª" in fila["etiqueta"]


# --- Preceptores por curso -----------------------------------------------------------------------

PRECEPTORES = "/api/rrhh/preceptores/"


def _preceptor(persona, turno="tarde", situacion="titular"):
    return Designacion.objects.create(personal=persona, categoria="preceptor", turno=turno, situacion_revista=situacion)


def _a_cargo(cliente, designacion, e, **extra):
    return cliente.post(PRECEPTORES, {"designacion": designacion.pk, "division": e["div"].pk, **extra})


def test_preceptor_a_cargo_de_un_curso(admin_client, ana, estructura):
    r = _a_cargo(admin_client, _preceptor(ana), estructura)
    assert r.status_code == 201 and r.data["division"] == estructura["div"].pk
    assert r.data["situacion_revista"] == "titular" and "4° 1ª" in r.data["etiqueta"]


def test_permisos_de_preceptores(common_client, admin_client, ana, estructura):
    assert common_client.get(PRECEPTORES).status_code == 200
    assert _a_cargo(common_client, _preceptor(ana), estructura).status_code == 403


def test_solo_los_preceptores_tienen_cursos_a_cargo(admin_client, ana, estructura):
    r = _a_cargo(admin_client, _designar(ana, "profesor"), estructura)
    assert r.status_code == 400 and "preceptores" in str(r.data)


def test_un_curso_puede_tener_varios_preceptores_pero_no_repetir(admin_client, ana, estructura):
    otra = _persona("40000010")
    assert _a_cargo(admin_client, _preceptor(ana, "manana"), estructura).status_code == 201
    assert _a_cargo(admin_client, _preceptor(otra, "tarde"), estructura).status_code == 201
    d = _preceptor(ana, "vespertino")
    assert _a_cargo(admin_client, d, estructura).status_code == 201
    assert _a_cargo(admin_client, d, estructura).status_code == 400  # mismo preceptor y curso
    assert len(admin_client.get(PRECEPTORES, {"division": estructura["div"].pk}).data) == 3


def test_suplente_de_preceptor(admin_client, ana, estructura):
    titular = _a_cargo(admin_client, _preceptor(ana, situacion="provisional"), estructura).data
    sup = _preceptor(_persona("40000011"), situacion="suplente")
    assert _a_cargo(admin_client, sup, estructura).status_code == 400  # debe indicar a quién reemplaza
    r = _a_cargo(admin_client, sup, estructura, suplente_de=titular["id"])
    assert r.status_code == 201 and r.data["suplente_de"] == titular["id"]


def test_suplente_de_preceptor_reglas(admin_client, ana, estructura):
    from apps.academico.models import Division
    otro_curso = Division.objects.create(anio=estructura["a5"], nombre="1ª")
    titular = _a_cargo(admin_client, _preceptor(ana), estructura).data
    sup = _preceptor(_persona("40000011"), situacion="suplente")
    r = admin_client.post(PRECEPTORES, {"designacion": sup.pk, "division": otro_curso.pk, "suplente_de": titular["id"]})
    assert r.status_code == 400 and "mismo curso" in str(r.data)
    a_sup = _a_cargo(admin_client, sup, estructura, suplente_de=titular["id"]).data
    sup2 = _preceptor(_persona("40000012"), situacion="suplente")
    assert _a_cargo(admin_client, sup2, estructura, suplente_de=a_sup["id"]).status_code == 400  # no de otro suplente
    otro_titular = _preceptor(_persona("40000013"), situacion="titular")
    assert _a_cargo(admin_client, otro_titular, estructura, suplente_de=titular["id"]).status_code == 400  # no es suplente


def test_no_se_borra_lo_que_tiene_dependencias(admin_client, ana, estructura):
    titular = _a_cargo(admin_client, _preceptor(ana), estructura).data
    _a_cargo(admin_client, _preceptor(_persona("40000011"), situacion="suplente"), estructura, suplente_de=titular["id"])
    assert admin_client.delete(f"{PRECEPTORES}{titular['id']}/").status_code == 409  # tiene suplentes
    assert admin_client.delete(f"/api/academico/divisiones/{estructura['div'].pk}/").status_code == 409  # tiene preceptores


def test_cambios_de_designacion_que_dejarian_datos_incoherentes(admin_client, ana, estructura):
    d_titular = _preceptor(ana)
    titular = _a_cargo(admin_client, d_titular, estructura).data
    d_sup = _preceptor(_persona("40000011"), situacion="suplente")
    _a_cargo(admin_client, d_sup, estructura, suplente_de=titular["id"])
    assert admin_client.patch(f"{DESIGNACIONES}{d_titular.pk}/", {"categoria": "profesor"}).status_code == 400  # tiene curso a cargo
    assert admin_client.patch(f"{DESIGNACIONES}{d_sup.pk}/", {"situacion_revista": "titular"}).status_code == 400  # reemplaza a alguien
    assert admin_client.patch(f"{DESIGNACIONES}{d_titular.pk}/", {"situacion_revista": "suplente"}).status_code == 400  # tiene suplentes
    assert admin_client.patch(f"{DESIGNACIONES}{d_titular.pk}/", {"turno": "manana"}).status_code == 200


def test_eliminar_persona_elimina_sus_cursos_a_cargo(admin_client, ana, estructura):
    _a_cargo(admin_client, _preceptor(ana), estructura)
    assert admin_client.delete(f"{PERSONAL}{ana.pk}/").status_code == 204
    assert admin_client.get(PRECEPTORES).data == []
