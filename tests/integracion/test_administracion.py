"""Administración de datos maestros (Parte 3): alta / edición / desactivación de sucursal,
producto, categoría, zona de exhibición y medio de pago desde la API; edición de cliente.

Contra PostgreSQL real, puerto 5442.

- crear / editar / desactivar requiere `operador.es_encargado` (mismo mecanismo que 007).
- editar un cliente NO requiere `es_encargado`.
- el borrado nunca es físico: "desactivar" pone `activo = false` y la fila sigue existiendo.
- `contar_dependencias` informa con conteos reales y NUNCA bloquea la desactivación.
- los listados aceptan `pagina`/`tamano_pagina` y responden `{items, total}` (RespuestaPaginada).
"""

import uuid

from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Categoria, Operador, Producto, Sucursal
from tests.apoyo_pagos import crear_operador, crear_sucursal, crear_turno

cliente = TestClient(app)


def _nombre(prefijo: str) -> str:
    return f"{prefijo} {uuid.uuid4().hex[:8]}"


def test_alta_edicion_y_desactivacion_de_sucursal_por_encargado(sesion):
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()

    alta = cliente.post(
        "/administracion/sucursales",
        json={
            "nombre": _nombre("Suc"),
            "zona_horaria": "America/Guayaquil",
            "id_operador": encargado.id_operador,
        },
    )
    assert alta.status_code == 201, alta.text
    id_suc = alta.json()["id_sucursal"]
    assert alta.json()["activo"] is True

    edit = cliente.put(
        f"/administracion/sucursales/{id_suc}",
        json={
            "nombre": _nombre("Suc-editada"),
            "zona_horaria": "America/Bogota",
            "id_operador": encargado.id_operador,
        },
    )
    assert edit.status_code == 200
    assert edit.json()["zona_horaria"] == "America/Bogota"

    baja = cliente.post(
        f"/administracion/sucursales/{id_suc}/desactivacion",
        json={"activo": False, "id_operador": encargado.id_operador},
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


def test_no_encargado_no_puede_administrar_maestros(sesion):
    cajero = crear_operador(sesion, es_encargado=False)
    sesion.commit()

    r = cliente.post(
        "/administracion/categorias",
        json={"nombre": _nombre("Cat"), "id_operador": cajero.id_operador},
    )
    # Enmienda v2.3.0: la verificación pasa por el mecanismo central `requiere_rol`, que
    # devuelve 403 `rol_insuficiente` en vez del antiguo 400 `admin_operador_no_encargado`.
    assert r.status_code == 403
    assert r.json()["codigo"] == "rol_insuficiente"


def test_desactivar_categoria_con_productos_informa_pero_no_bloquea(sesion):
    encargado = crear_operador(sesion, es_encargado=True)
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
        json={"activo": False, "id_operador": encargado.id_operador},
    )
    assert baja.status_code == 200  # informa, no bloquea
    assert baja.json()["activo"] is False


def test_crear_producto_nuevo_desde_administracion(sesion):
    encargado = crear_operador(sesion, es_encargado=True)
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
            "id_operador": encargado.id_operador,
        },
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["activo"] is True and cuerpo["precio_vigente"] == "2.5000"


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


def test_listado_paginado_devuelve_items_y_total_en_el_body(sesion):
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()
    for _ in range(3):
        cliente.post(
            "/administracion/medios",
            json={"nombre": _nombre("Medio"), "id_operador": encargado.id_operador},
        )

    r = cliente.get("/administracion/medios?pagina=1&tamano_pagina=2")
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo["items"]) == 2
    assert cuerpo["total"] >= 3


def test_listado_admite_busqueda_por_nombre_combinada_con_paginacion(sesion):
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()
    marca = uuid.uuid4().hex[:8]
    cliente.post(
        "/administracion/categorias",
        json={"nombre": f"Refrescos {marca}", "id_operador": encargado.id_operador},
    )
    cliente.post(
        "/administracion/categorias",
        json={"nombre": f"Congelados {marca}", "id_operador": encargado.id_operador},
    )

    r = cliente.get(f"/administracion/categorias?busqueda=refrescos {marca}&tamano_pagina=50")
    assert r.status_code == 200
    nombres = [f["nombre"] for f in r.json()["items"]]
    assert nombres == [f"Refrescos {marca}"]
    assert r.json()["total"] == 1


def test_ultimo_turno_de_sucursal_para_la_pantalla_de_apertura(sesion):
    sucursal = crear_sucursal(sesion)
    encargado = crear_operador(sesion, es_encargado=True)
    sesion.commit()

    # Sin turnos: null, nunca un placeholder.
    vacio = cliente.get(f"/turnos/ultimo?id_sucursal={sucursal.id_sucursal}")
    assert vacio.status_code == 200
    assert vacio.json() is None

    crear_turno(
        sesion, id_operador=encargado.id_operador, id_sucursal=sucursal.id_sucursal
    )
    sesion.commit()

    con = cliente.get(f"/turnos/ultimo?id_sucursal={sucursal.id_sucursal}")
    assert con.status_code == 200
    assert con.json()["instante_apertura"] is not None
