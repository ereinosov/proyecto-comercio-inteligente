"""T089 — Los 10 escenarios de `specs/001-core-ventas-inventario/quickstart.md`, de extremo a
extremo contra la API (TestClient sobre PostgreSQL real, puerto 5442). Un solo lugar donde se ve
que las reglas difíciles del módulo se cumplen juntas.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import (
    Categoria,
    Existencia,
    Lote,
    MovimientoInventario,
    Operador,
    Producto,
    Sucursal,
    Traspaso,
)
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.persistencia.sesion import SesionLocal
from rasero.seguridad import hashear_pin

cliente = TestClient(app)


def _sucursal(sesion, nombre):
    s = Sucursal(nombre=f"{nombre} {uuid.uuid4().hex[:6]}", zona_horaria="America/Guayaquil")
    sesion.add(s)
    sesion.flush()
    return s


def _operador(sesion, id_sucursal):
    # Enmienda v2.3.0: `operador` tiene `rol` e `id_sucursal` (sucursal fija) en vez de
    # `es_encargado`. Un `cajero` sólo abre turno en su propia sucursal, de ahí el parámetro.
    op = Operador(
        nombre=f"Op {uuid.uuid4().hex[:5]}", pin_hash="", rol="cajero",
        id_sucursal=id_sucursal, activo=True,
    )
    sesion.add(op)
    sesion.flush()
    op.pin_hash = hashear_pin("1234", str(op.id_operador))
    sesion.flush()
    return op


def _producto(sesion, *, es_granel=False, precio="2.5000", lleva_caducidad=False, id_categoria=None):
    p = Producto(
        nombre=f"Prod {uuid.uuid4().hex[:6]}",
        id_categoria=id_categoria,
        es_granel=es_granel,
        precio_vigente=Decimal(precio),
        lleva_caducidad=lleva_caducidad,
    )
    sesion.add(p)
    sesion.flush()
    return p


def _abrir_turno(id_operador, id_sucursal):
    r = cliente.post(
        "/turnos",
        json={"id_operador": id_operador, "id_sucursal": id_sucursal, "caja": "caja-1", "pin": "1234"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id_turno"]


def test_escenario_1_venta_mixta_con_producto_a_peso():
    s = SesionLocal()
    suc = _sucursal(s, "Quevedo Centro")
    op = _operador(s, suc.id_sucursal)
    unidad = _producto(s, es_granel=False, precio="1.7500")
    granel = _producto(s, es_granel=True, precio="7.3300")  # precio por kg impar
    s.commit()
    id_turno = _abrir_turno(op.id_operador, suc.id_sucursal)
    cliente.post("/entradas-inventario", json={
        "id_sucursal": suc.id_sucursal, "id_producto": unidad.id_producto,
        "cantidad": 10, "costo_unitario": "1.0000"})
    cliente.post("/entradas-inventario", json={
        "id_sucursal": suc.id_sucursal, "id_producto": granel.id_producto,
        "cantidad": 5000, "costo_unitario": "3.0000"})
    s.close()

    venta = cliente.post("/ventas", json={
        "clave_idempotencia": f"qs1-{uuid.uuid4()}",
        "id_turno": id_turno,
        "referencia_terminal_pago": "datafono-1",
        "renglones": [
            {"id_producto": unidad.id_producto, "cantidad_unidades": 2},
            {"id_producto": granel.id_producto, "cantidad_gramos": 700},
        ],
    })
    assert venta.status_code == 201
    cuerpo = venta.json()
    assert cuerpo["referencia_terminal_pago"] == "datafono-1"
    # Importe granel: 0,7 kg * 7,33 = 5,131 -> 5,13 ; total = 3,50 + 5,13 (suma de redondeados).
    importes = {r["id_producto"]: r["importe"] for r in cuerpo["renglones"]}
    assert importes[unidad.id_producto] == "3.50"
    assert importes[granel.id_producto] == "5.13"
    assert cuerpo["total"] == "8.63"

    verif = SesionLocal()
    try:
        saldo_granel = verif.execute(
            select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(
                Existencia.id_sucursal == suc.id_sucursal,
                Existencia.id_producto == granel.id_producto,
            )
        ).scalar_one()
        assert Decimal(saldo_granel) == Decimal(4300)  # 5000 - 700 g
    finally:
        verif.close()


def test_escenario_2_idempotencia_diez_reintentos():
    s = SesionLocal()
    suc = _sucursal(s, "Quevedo Centro")
    op = _operador(s, suc.id_sucursal)
    p = _producto(s)
    s.commit()
    id_turno = _abrir_turno(op.id_operador, suc.id_sucursal)
    cliente.post("/entradas-inventario", json={
        "id_sucursal": suc.id_sucursal, "id_producto": p.id_producto,
        "cantidad": 100, "costo_unitario": "1.0000"})
    s.close()

    cuerpo = {
        "clave_idempotencia": f"qs2-{uuid.uuid4()}",
        "id_turno": id_turno,
        "renglones": [{"id_producto": p.id_producto, "cantidad_unidades": 3}],
    }
    primera = cliente.post("/ventas", json=cuerpo)
    assert primera.status_code == 201
    id_venta = primera.json()["id_venta"]
    for _ in range(9):
        r = cliente.post("/ventas", json=cuerpo)
        assert r.status_code == 200
        assert r.json()["id_venta"] == id_venta

    verif = SesionLocal()
    try:
        movs = verif.execute(
            select(func.count()).select_from(MovimientoInventario).where(
                MovimientoInventario.id_producto == p.id_producto,
                MovimientoInventario.tipo == "salida_venta",
            )
        ).scalar_one()
        assert movs == 1  # un solo juego de movimientos
    finally:
        verif.close()


def test_escenario_3_seleccion_de_lote_por_caducidad():
    s = SesionLocal()
    suc = _sucursal(s, "Quevedo Centro")
    op = _operador(s, suc.id_sucursal)
    p = _producto(s, lleva_caducidad=True)
    ahora = datetime.now(timezone.utc)
    # Lote B: entró hace una semana, caduca en un mes.
    lote_b = Lote(id_producto=p.id_producto, id_sucursal=suc.id_sucursal, costo_unitario=Decimal("1.0000"),
                  fecha_caducidad=date.today() + timedelta(days=30),
                  instante_entrada=ahora - timedelta(days=7))
    s.add(lote_b)
    s.flush()
    registrar_movimiento(s, id_sucursal=suc.id_sucursal, id_producto=p.id_producto, id_lote=lote_b.id_lote,
                         tipo="entrada_compra", cantidad=Decimal(10), instante=ahora - timedelta(days=7))
    # Lote A: entró hoy, caduca en 3 días -> debe salir primero.
    lote_a = Lote(id_producto=p.id_producto, id_sucursal=suc.id_sucursal, costo_unitario=Decimal("1.0000"),
                  fecha_caducidad=date.today() + timedelta(days=3), instante_entrada=ahora)
    s.add(lote_a)
    s.flush()
    registrar_movimiento(s, id_sucursal=suc.id_sucursal, id_producto=p.id_producto, id_lote=lote_a.id_lote,
                         tipo="entrada_compra", cantidad=Decimal(10), instante=ahora)
    s.commit()
    id_turno = _abrir_turno(op.id_operador, suc.id_sucursal)
    s.close()

    venta = cliente.post("/ventas", json={
        "clave_idempotencia": f"qs3-{uuid.uuid4()}", "id_turno": id_turno,
        "renglones": [{"id_producto": p.id_producto, "cantidad_unidades": 4}]})
    assert venta.status_code == 201
    lotes = venta.json()["renglones"][0]["lotes_consumidos"]
    assert lotes == [{"id_lote": lote_a.id_lote, "cantidad": 4}], "sale primero el de caducidad más próxima"


def test_escenario_4_saldo_negativo_y_reconstruccion():
    s = SesionLocal()
    suc = _sucursal(s, "Quevedo Centro")
    op = _operador(s, suc.id_sucursal)
    p = _producto(s)
    s.commit()
    id_turno = _abrir_turno(op.id_operador, suc.id_sucursal)
    cliente.post("/entradas-inventario", json={
        "id_sucursal": suc.id_sucursal, "id_producto": p.id_producto,
        "cantidad": 3, "costo_unitario": "1.0000"})
    s.close()

    venta = cliente.post("/ventas", json={
        "clave_idempotencia": f"qs4-{uuid.uuid4()}", "id_turno": id_turno,
        "renglones": [{"id_producto": p.id_producto, "cantidad_unidades": 5}]})
    assert venta.status_code == 201
    assert any(a["codigo"] == "saldo_negativo" for a in venta.json()["advertencias"])

    verif = SesionLocal()
    try:
        reconstruido = verif.execute(
            select(func.coalesce(func.sum(MovimientoInventario.cantidad), 0)).where(
                MovimientoInventario.id_sucursal == suc.id_sucursal,
                MovimientoInventario.id_producto == p.id_producto,
            )
        ).scalar_one()
        consultado = verif.execute(
            select(func.coalesce(func.sum(Existencia.cantidad), 0)).where(
                Existencia.id_sucursal == suc.id_sucursal,
                Existencia.id_producto == p.id_producto,
            )
        ).scalar_one()
        assert Decimal(reconstruido) == Decimal(-2)
        assert Decimal(consultado) == Decimal(-2)
    finally:
        verif.close()


def test_escenario_5_traspaso_con_mercancia_en_transito():
    s = SesionLocal()
    origen = _sucursal(s, "Quevedo Centro")
    destino = _sucursal(s, "Buena Fe")
    p = _producto(s)
    s.commit()
    cliente.post("/entradas-inventario", json={
        "id_sucursal": origen.id_sucursal, "id_producto": p.id_producto,
        "cantidad": 20, "costo_unitario": "1.5000"})
    s.close()

    def total_sistema():
        v = SesionLocal()
        try:
            ex = v.execute(select(func.coalesce(func.sum(Existencia.cantidad), 0))).scalar_one()
            tr = v.execute(
                select(func.coalesce(func.sum(func.abs(MovimientoInventario.cantidad)), 0))
                .join(Traspaso, Traspaso.id_traspaso == MovimientoInventario.id_traspaso)
                .where(MovimientoInventario.tipo == "salida_traspaso", Traspaso.estado == "en_transito")
            ).scalar_one()
            return Decimal(ex) + Decimal(tr)
        finally:
            v.close()

    antes = total_sistema()
    despacho = cliente.post("/traspasos", json={
        "id_sucursal_origen": origen.id_sucursal, "id_sucursal_destino": destino.id_sucursal,
        "renglones": [{"id_producto": p.id_producto, "cantidad": 8}]})
    assert despacho.status_code == 201
    id_traspaso = despacho.json()["id_traspaso"]
    assert total_sistema() == antes, "el total no cambia al despachar"

    recepcion = cliente.post(f"/traspasos/{id_traspaso}/recepcion", json={
        "renglones": [{"id_producto": p.id_producto, "cantidad_recibida": 7}]})
    assert recepcion.status_code == 200
    assert recepcion.json()["renglones"][0]["discrepancia"] == -1


def test_escenario_6_reconciliacion_offline():
    s = SesionLocal()
    suc = _sucursal(s, "Quevedo Centro")
    op = _operador(s, suc.id_sucursal)
    p = _producto(s)
    s.commit()
    id_turno = _abrir_turno(op.id_operador, suc.id_sucursal)
    s.close()

    recurso = f"qs6-{uuid.uuid4()}"
    base = datetime.now(timezone.utc) - timedelta(hours=2)
    vieja = {"id_operacion_pendiente": str(uuid.uuid4()), "tipo_operacion": "consulta_no_atendida",
             "carga": {"id_producto": p.id_producto, "id_turno": id_turno},
             "recurso_afectado": recurso, "marca_tiempo_origen": base.isoformat()}
    nueva = {"id_operacion_pendiente": str(uuid.uuid4()), "tipo_operacion": "consulta_no_atendida",
             "carga": {"id_producto": p.id_producto, "id_turno": id_turno},
             "recurso_afectado": recurso,
             "marca_tiempo_origen": (base + timedelta(minutes=15)).isoformat()}

    r = cliente.post("/operaciones-pendientes/sincronizacion", json={"operaciones": [nueva, vieja]})
    assert r.status_code == 200
    por_id = {o["id_operacion_pendiente"]: o for o in r.json()}
    assert por_id[vieja["id_operacion_pendiente"]]["estado"] == "sincronizada"
    assert por_id[nueva["id_operacion_pendiente"]]["estado"] == "conflicto_resuelto"
    assert (
        por_id[nueva["id_operacion_pendiente"]]["id_operacion_prevaleciente"]
        == vieja["id_operacion_pendiente"]
    )


def test_escenario_7_consulta_no_atendida_en_dos_toques():
    s = SesionLocal()
    suc = _sucursal(s, "Quevedo Centro")
    op = _operador(s, suc.id_sucursal)
    p = _producto(s)
    s.commit()
    id_turno = _abrir_turno(op.id_operador, suc.id_sucursal)
    s.close()

    r = cliente.post("/consultas-no-atendidas", json={"id_producto": p.id_producto, "id_turno": id_turno})
    assert r.status_code == 201
    assert r.json()["saldo_en_el_instante"] == 0
    # No acepta datos de cliente.
    con_cliente = cliente.post(
        "/consultas-no-atendidas",
        json={"id_producto": p.id_producto, "id_turno": id_turno, "nombre_cliente": "X"},
    )
    assert con_cliente.status_code == 422


def test_escenario_8_comparacion_de_precios_con_antiguedad():
    s = SesionLocal()
    suc = _sucursal(s, "Quevedo Centro")
    p = _producto(s, es_granel=True, precio="6.0000")  # por kg
    s.commit()
    s.close()

    canales = []
    for nombre in ("Canal Uno", "Canal Dos", "Canal Tres"):
        c = cliente.post("/canales-competencia", json={"nombre": f"{nombre} {uuid.uuid4().hex[:4]}"})
        canales.append(c.json())

    # Dos comparables (gramos) y una en otra presentación no convertible (unidad).
    cliente.post("/observaciones-precio", json={
        "id_producto": p.id_producto, "id_canal_competencia": canales[0]["id_canal_competencia"],
        "presentacion_cantidad": "500", "presentacion_unidad": "gramo",
        "precio_observado": "3.10", "fuente": "visita", "origen_captura": "manual"})
    cliente.post("/observaciones-precio", json={
        "id_producto": p.id_producto, "id_canal_competencia": canales[1]["id_canal_competencia"],
        "presentacion_cantidad": "1000", "presentacion_unidad": "gramo",
        "precio_observado": "6.40", "fuente": "folleto", "origen_captura": "archivo"})
    cliente.post("/observaciones-precio", json={
        "id_producto": p.id_producto, "id_canal_competencia": canales[2]["id_canal_competencia"],
        "presentacion_cantidad": "1", "presentacion_unidad": "unidad",
        "precio_observado": "5.00", "fuente": "foto", "origen_captura": "manual"})

    comp = cliente.get(
        f"/productos/{p.id_producto}/comparacion-precios?id_sucursal={suc.id_sucursal}"
    ).json()
    assert comp["precio_propio_por_unidad_medida"] == "6.0000"
    assert len(comp["observaciones"]) == 3
    for o in comp["observaciones"]:
        # Tres portadores: forma (enum), texto y (en el frontend) color; nunca solo color.
        assert o["indicador_forma"] in {"lleno", "medio", "hueco"}
        assert o["antiguedad_texto"]
    comparables = [o for o in comp["observaciones"] if o["comparable"]]
    no_comparables = [o for o in comp["observaciones"] if not o["comparable"]]
    assert len(comparables) == 2 and len(no_comparables) == 1
    assert no_comparables[0]["precio_por_unidad_medida"] is None


def test_escenario_9_conteo_fisico_y_diferencia():
    s = SesionLocal()
    suc = _sucursal(s, "Quevedo Centro")
    p = _producto(s)
    s.commit()
    cliente.post("/entradas-inventario", json={
        "id_sucursal": suc.id_sucursal, "id_producto": p.id_producto,
        "cantidad": 40, "costo_unitario": "1.0000"})
    s.close()

    abrir = cliente.post("/conteos-fisicos", json={
        "id_sucursal": suc.id_sucursal, "id_productos": [p.id_producto]})
    assert abrir.status_code == 201
    id_conteo = abrir.json()["id_conteo_fisico"]
    resuelto = cliente.post(f"/conteos-fisicos/{id_conteo}/resolucion", json={
        "renglones": [{"id_producto": p.id_producto, "cantidad_contada": 37}]})
    assert resuelto.status_code == 200
    r = resuelto.json()["renglones"][0]
    assert r["cantidad_esperada"] == 40 and r["cantidad_contada"] == 37 and r["diferencia"] == -3

    verif = SesionLocal()
    try:
        ajuste = verif.execute(
            select(MovimientoInventario).where(
                MovimientoInventario.id_conteo_fisico == id_conteo,
                MovimientoInventario.tipo == "ajuste_conteo",
            )
        ).scalar_one()
        assert ajuste.cantidad == Decimal(-3)
        total = verif.execute(
            select(func.coalesce(func.sum(MovimientoInventario.cantidad), 0)).where(
                MovimientoInventario.id_producto == p.id_producto
            )
        ).scalar_one()
        assert Decimal(total) == Decimal(37)  # reconstruible
    finally:
        verif.close()


def test_escenario_10_capital_inmovilizado_por_categoria():
    s = SesionLocal()
    suc = _sucursal(s, "Quevedo Centro")
    frescos = Categoria(nombre=f"Frescos {uuid.uuid4().hex[:5]}", dias_umbral_inmovilizado=5)
    largo = Categoria(nombre=f"Abarrote {uuid.uuid4().hex[:5]}", dias_umbral_inmovilizado=60)
    s.add_all([frescos, largo])
    s.flush()
    p_fresco = _producto(s, id_categoria=frescos.id_categoria)
    p_largo = _producto(s, id_categoria=largo.id_categoria)
    p_sin_umbral = _producto(s, id_categoria=None)
    ahora = datetime.now(timezone.utc)

    def lote_parado(prod, dias, costo="4.0000"):
        lote = Lote(id_producto=prod.id_producto, id_sucursal=suc.id_sucursal,
                    costo_unitario=Decimal(costo), fecha_caducidad=None,
                    instante_entrada=ahora - timedelta(days=dias))
        s.add(lote)
        s.flush()
        registrar_movimiento(s, id_sucursal=suc.id_sucursal, id_producto=prod.id_producto,
                             id_lote=lote.id_lote, tipo="entrada_compra", cantidad=Decimal(10),
                             instante=ahora - timedelta(days=dias))
        return lote

    l_fresco = lote_parado(p_fresco, 40)
    l_largo = lote_parado(p_largo, 40)
    l_global = lote_parado(p_sin_umbral, 120)
    l_sin_costo = lote_parado(p_fresco, 30, costo="0.0000")
    s.commit()
    s.close()

    listado = cliente.get(f"/capital-inmovilizado?id_sucursal={suc.id_sucursal}").json()
    por_lote = {f["id_lote"]: f for f in listado}
    assert l_fresco.id_lote in por_lote
    assert l_largo.id_lote not in por_lote
    assert por_lote[l_global.id_lote]["umbral_heredado_del_global"] is True
    assert por_lote[l_sin_costo.id_lote]["valor_calculable"] is False
    assert por_lote[l_sin_costo.id_lote]["valor_inmovilizado"] is None
