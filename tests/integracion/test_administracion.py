"""Administración de datos maestros (Parte 3): alta / edición / desactivación de sucursal,
producto, categoría, zona de exhibición y medio de pago desde la API; edición de cliente.

Contra PostgreSQL real, puerto 5442.

- crear / editar / desactivar requiere rol `admin` EN EXCLUSIVA (constitución v2.7.1: coincide
  con la tabla de "Autorización de pantalla" v2.5.0; un `encargado` recibe 403 igual que un
  `cajero`). User Story 11 (enmienda v2.4.0): la identidad del operador se deriva del token de
  sesión de turno (`Authorization: Bearer`), no del `id_operador` del cuerpo.
- editar un cliente NO requiere rol.
- el borrado nunca es físico: "desactivar" pone `activo = false` y la fila sigue existiendo.
- `contar_dependencias` informa con conteos reales y NUNCA bloquea la desactivación.
- los listados aceptan `pagina`/`tamano_pagina` y responden `{items, total}` (RespuestaPaginada).
"""

import uuid

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Categoria, Operador, Producto, Sucursal
from tests.apoyo import headers_sesion
from tests.apoyo_pagos import crear_operador, crear_sucursal, crear_turno

cliente = TestClient(app)


def _nombre(prefijo: str) -> str:
    return f"{prefijo} {uuid.uuid4().hex[:8]}"


def test_alta_edicion_y_desactivacion_de_sucursal_por_admin(sesion):
    admin = crear_operador(sesion, rol="admin")
    cab = headers_sesion(sesion, admin)
    sesion.commit()

    alta = cliente.post(
        "/administracion/sucursales",
        json={"nombre": _nombre("Suc"), "zona_horaria": "America/Guayaquil"},
        headers=cab,
    )
    assert alta.status_code == 201, alta.text
    id_suc = alta.json()["id_sucursal"]
    assert alta.json()["activo"] is True

    edit = cliente.put(
        f"/administracion/sucursales/{id_suc}",
        json={"nombre": _nombre("Suc-editada"), "zona_horaria": "America/Bogota"},
        headers=cab,
    )
    assert edit.status_code == 200
    assert edit.json()["zona_horaria"] == "America/Bogota"

    baja = cliente.post(
        f"/administracion/sucursales/{id_suc}/desactivacion",
        json={"activo": False},
        headers=cab,
    )
    assert baja.status_code == 200
    assert baja.json()["activo"] is False

    # No se borró: sigue en la base, sólo oculta de los listados por defecto.
    sesion.expire_all()
    assert sesion.get(Sucursal, id_suc) is not None
    visibles = cliente.get("/administracion/sucursales").json()["items"]
    assert id_suc not in [s["id_sucursal"] for s in visibles]
    con_inactivas = cliente.get(
        "/administracion/sucursales?incluir_inactivos=true"
    ).json()["items"]
    assert id_suc in [s["id_sucursal"] for s in con_inactivas]


def test_solo_admin_administra_datos_maestros(sesion):
    """Regresión de la auditoría (constitución v2.7.1): la administración de datos maestros es
    `admin` EN EXCLUSIVA. Un `cajero` y un `encargado` reciben 403 `rol_insuficiente`; sólo el
    `admin` crea.
    """
    cajero = crear_operador(sesion, es_encargado=False)
    encargado = crear_operador(sesion, rol="encargado")
    admin = crear_operador(sesion, rol="admin")
    cab_cajero = headers_sesion(sesion, cajero)
    cab_encargado = headers_sesion(sesion, encargado)
    cab_admin = headers_sesion(sesion, admin)
    sesion.commit()

    for cab in (cab_cajero, cab_encargado):
        r = cliente.post(
            "/administracion/categorias", json={"nombre": _nombre("Cat")}, headers=cab
        )
        assert r.status_code == 403
        assert r.json()["codigo"] == "rol_insuficiente"

    ok = cliente.post(
        "/administracion/categorias", json={"nombre": _nombre("Cat")}, headers=cab_admin
    )
    assert ok.status_code == 201, ok.text


def test_administracion_sin_token_es_rechazada(sesion):
    # User Story 11: sin `Authorization`, la petición nunca llega a verificar rol.
    r = cliente.post("/administracion/categorias", json={"nombre": _nombre("Cat")})
    assert r.status_code == 401
    assert r.json()["codigo"] == "sesion_invalida"


def test_desactivar_categoria_con_productos_informa_pero_no_bloquea(sesion):
    admin = crear_operador(sesion, rol="admin")
    cab = headers_sesion(sesion, admin)
    categoria = Categoria(nombre=_nombre("Cat"), dias_umbral_inmovilizado=30)
    sesion.add(categoria)
    sesion.flush()
    producto = Producto(
        id_categoria=categoria.id_categoria,
        nombre=_nombre("Prod"),
        es_granel=False,
        precio_vigente="1.0000",
        lleva_caducidad=False,
    )
    sesion.add(producto)
    sesion.commit()

    deps = cliente.get(
        f"/administracion/categorias/{categoria.id_categoria}/dependencias"
    ).json()
    assert deps["tiene_dependencias"] is True
    assert any(d["conteo"] >= 1 for d in deps["dependencias"])

    baja = cliente.post(
        f"/administracion/categorias/{categoria.id_categoria}/desactivacion",
        json={"activo": False},
        headers=cab,
    )
    assert baja.status_code == 200  # informa, no bloquea
    assert baja.json()["activo"] is False


def test_crear_producto_nuevo_desde_administracion(sesion):
    admin = crear_operador(sesion, rol="admin")
    cab = headers_sesion(sesion, admin)
    categoria = Categoria(nombre=_nombre("Cat"))
    sesion.add(categoria)
    sesion.commit()

    r = cliente.post(
        "/administracion/productos",
        json={
            "nombre": _nombre("Prod"),
            "id_categoria": categoria.id_categoria,
            "es_granel": False,
            "precio_vigente": "2.5000",
            "lleva_caducidad": False,
        },
        headers=cab,
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["activo"] is True and cuerpo["precio_vigente"] == "2.5000"


def test_crear_y_editar_producto_persiste_url_imagen(sesion):
    """US12: la URL externa de imagen es opcional; si se envía, se persiste y se devuelve en el
    alta, en la edición y en el catálogo (GET /productos)."""
    admin = crear_operador(sesion, rol="admin")
    cab = headers_sesion(sesion, admin)
    categoria = Categoria(nombre=_nombre("Cat"))
    sesion.add(categoria)
    sesion.commit()

    url = "https://cdn.example.com/img/atun.jpg"
    alta = cliente.post(
        "/administracion/productos",
        json={
            "nombre": _nombre("Prod"),
            "id_categoria": categoria.id_categoria,
            "es_granel": False,
            "precio_vigente": "2.5000",
            "lleva_caducidad": False,
            "url_imagen": url,
        },
        headers=cab,
    )
    assert alta.status_code == 201, alta.text
    id_producto = alta.json()["id_producto"]
    assert alta.json()["url_imagen"] == url

    # aparece en el catálogo que consume la pantalla de Venta
    catalogo = cliente.get("/productos").json()
    fila = next(p for p in catalogo if p["id_producto"] == id_producto)
    assert fila["url_imagen"] == url

    # editar a vacío -> se guarda NULL (no todos los productos necesitan imagen)
    edit = cliente.put(
        f"/administracion/productos/{id_producto}",
        json={
            "nombre": alta.json()["nombre"],
            "id_categoria": categoria.id_categoria,
            "es_granel": False,
            "precio_vigente": "2.5000",
            "lleva_caducidad": False,
            "url_imagen": "  ",
        },
        headers=cab,
    )
    assert edit.status_code == 200, edit.text
    assert edit.json()["url_imagen"] is None


def test_crear_producto_con_url_imagen_malformada_es_rechazado(sesion):
    admin = crear_operador(sesion, rol="admin")
    cab = headers_sesion(sesion, admin)
    categoria = Categoria(nombre=_nombre("Cat"))
    sesion.add(categoria)
    sesion.commit()

    r = cliente.post(
        "/administracion/productos",
        json={
            "nombre": _nombre("Prod"),
            "id_categoria": categoria.id_categoria,
            "es_granel": False,
            "precio_vigente": "2.5000",
            "lleva_caducidad": False,
            "url_imagen": "atun.jpg",
        },
        headers=cab,
    )
    assert r.status_code >= 400 and r.status_code != 201, r.text


def test_precio_cero_o_negativo_es_rechazado_con_el_mismo_codigo(sesion):
    """Hallazgo #4 de la auditoría: `_valida_precio` usaba `< 0`, así que un producto activo a
    $0.00 quedaba vendible sin advertencia. Ahora `<= 0` -> mismo código `admin_precio_invalido`
    para el 0 y para un negativo.
    """
    admin = crear_operador(sesion, rol="admin")
    cab = headers_sesion(sesion, admin)
    categoria = Categoria(nombre=_nombre("Cat"))
    sesion.add(categoria)
    sesion.commit()

    for precio in ("0.0000", "-1.5000"):
        r = cliente.post(
            "/administracion/productos",
            json={
                "nombre": _nombre("Prod"),
                "id_categoria": categoria.id_categoria,
                "es_granel": False,
                "precio_vigente": precio,
                "lleva_caducidad": False,
            },
            headers=cab,
        )
        assert r.status_code >= 400 and r.status_code != 201, r.text
        assert r.json()["codigo"] == "admin_precio_invalido", (precio, r.text)


def test_editar_cliente_no_requiere_encargado(sesion):
    cajero = crear_operador(sesion, es_encargado=False)
    sesion.commit()

    alta = cliente.post(
        "/clientes",
        json={"nombre": "Cliente Editable", "fecha_nacimiento": "1990-01-01"},
    )
    id_cliente = alta.json()["id_cliente"]

    edit = cliente.put(
        f"/clientes/{id_cliente}",
        json={
            "nombre": "Cliente Renombrado",
            "fecha_nacimiento": "1991-02-02",
            "contacto": "0999999999",
        },
    )
    assert edit.status_code == 200, edit.text
    assert edit.json()["nombre"] == "Cliente Renombrado"
    assert edit.json()["contacto"] == "0999999999"


def test_listar_operadores_puede_incluir_desactivados(sesion):
    """Hallazgo #9 de la auditoría: sin `incluir_inactivos` no había forma de ver ni reactivar
    un operador desactivado (a diferencia de sucursales y productos). Por defecto siguen ocultos
    —es la lista de la apertura de turno—.
    """
    admin = crear_operador(sesion, rol="admin")
    cajero = crear_operador(sesion, es_encargado=False, id_sucursal=admin.id_sucursal)
    cab = headers_sesion(sesion, admin)
    sesion.commit()

    baja = cliente.post(
        f"/operadores/{cajero.id_operador}/activo", json={"activo": False}, headers=cab
    )
    assert baja.status_code == 200, baja.text

    activos = [o["id_operador"] for o in cliente.get("/operadores").json()]
    con_inactivos = [
        o["id_operador"] for o in cliente.get("/operadores?incluir_inactivos=true").json()
    ]
    assert cajero.id_operador not in activos
    assert cajero.id_operador in con_inactivos


def test_listado_paginado_devuelve_items_y_total_en_el_body(sesion):
    admin = crear_operador(sesion, rol="admin")
    cab = headers_sesion(sesion, admin)
    sesion.commit()
    for _ in range(3):
        r = cliente.post(
            "/administracion/medios", json={"nombre": _nombre("Medio")}, headers=cab
        )
        assert r.status_code == 201, r.text

    r = cliente.get("/administracion/medios?pagina=1&tamano_pagina=2")
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo["items"]) == 2
    assert cuerpo["total"] >= 3


def test_listado_admite_busqueda_por_nombre_combinada_con_paginacion(sesion):
    admin = crear_operador(sesion, rol="admin")
    cab = headers_sesion(sesion, admin)
    sesion.commit()
    marca = uuid.uuid4().hex[:8]
    cliente.post(
        "/administracion/categorias", json={"nombre": f"Refrescos {marca}"}, headers=cab
    )
    cliente.post(
        "/administracion/categorias", json={"nombre": f"Congelados {marca}"}, headers=cab
    )

    r = cliente.get(f"/administracion/categorias?busqueda=refrescos {marca}&tamano_pagina=50")
    assert r.status_code == 200
    nombres = [f["nombre"] for f in r.json()["items"]]
    assert nombres == [f"Refrescos {marca}"]
    assert r.json()["total"] == 1


def test_ultimo_turno_de_sucursal_para_la_pantalla_de_apertura(sesion):
    sucursal = crear_sucursal(sesion)
    admin = crear_operador(sesion, rol="admin")
    sesion.commit()

    # Sin turnos: null, nunca un placeholder.
    vacio = cliente.get(f"/turnos/ultimo?id_sucursal={sucursal.id_sucursal}")
    assert vacio.status_code == 200
    assert vacio.json() is None

    crear_turno(
        sesion, id_operador=admin.id_operador, id_sucursal=sucursal.id_sucursal
    )
    sesion.commit()

    con = cliente.get(f"/turnos/ultimo?id_sucursal={sucursal.id_sucursal}")
    assert con.status_code == 200
    assert con.json()["instante_apertura"] is not None
