"""T029 — Prueba obligatoria (Principio III): una fuga confirmada con 90 días vencidos sin
nueva visita anonimiza al cliente conservando sus métricas agregadas (FR-015, FR-016); una
nueva visita antes de vencer ese plazo cancela la anonimización programada.

Técnica: las visitas se crean con `instante_origen` en el pasado (hace más de 12 meses) para
que `evaluar_fugas_pendientes` — que usa el reloj real, nunca uno inyectado, porque es un job de
fondo (research.md #6) — confirme la fuga de inmediato contra el "ahora" real de la prueba. Solo
`instante_purga_programada` se adelanta manualmente para no esperar 90 días reales: es la fecha
límite la que se simula, no el estado de negocio, que sí lo produce la lógica real.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from rasero.persistencia.modelos import IntervaloCompra, SenalFuga
from rasero.servicios.anonimizacion import anonimizar_clientes_vencidos
from rasero.servicios.clientes import evaluar_fugas_pendientes, registrar_cliente, registrar_visita
from rasero.servicios.ventas import RenglonEntrada, registrar_venta
from tests.apoyo import crear_escenario_basico


def _crear_cliente_con_historial_antiguo(sesion, *, nombre: str):
    """Cliente con 3 visitas cada 10 días, la última hace 380 días: intervalo_esperado_dias=10,
    y ya muy por encima del umbral de confirmación (max(5x10, 365) = 365 días) para el reloj
    real de la prueba.
    """
    escenario = crear_escenario_basico(sesion, existencia_inicial=1000)
    cliente = registrar_cliente(
        sesion, nombre=nombre, fecha_nacimiento=datetime(1990, 1, 1).date()
    )

    ahora = datetime.now(timezone.utc)
    offsets_dias = [400, 390, 380]
    for offset in offsets_dias:
        venta, _creada, _adv, _lotes = registrar_venta(
            sesion,
            clave_idempotencia=f"antiguo-{nombre}-{uuid.uuid4()}",
            id_turno=escenario["turno"].id_turno,
            referencia_terminal_pago=None,
            instante_origen=ahora - timedelta(days=offset),
            renglones=[
                RenglonEntrada(
                    id_producto=escenario["producto"].id_producto,
                    cantidad_unidades=1,
                    cantidad_gramos=None,
                )
            ],
        )
        registrar_visita(sesion, id_cliente=cliente.id_cliente, id_venta=venta.id_venta)

    return cliente, escenario


def test_fuga_confirmada_con_90_dias_vencidos_anonimiza_conservando_metricas(sesion):
    cliente, _escenario = _crear_cliente_con_historial_antiguo(sesion, nombre="Fuga Vencida")

    intervalo_antes = sesion.get(IntervaloCompra, cliente.id_cliente)
    assert intervalo_antes.estado == "calculado"
    assert intervalo_antes.intervalo_esperado_dias == 10

    tocados = evaluar_fugas_pendientes(sesion)
    assert tocados == 1

    senal = sesion.execute(
        select(SenalFuga).where(SenalFuga.id_cliente == cliente.id_cliente)
    ).scalar_one()
    assert senal.estado == "confirmada"
    assert senal.instante_purga_programada is not None

    # Simula el paso de los 90 días de retención adelantando solo la fecha límite.
    senal.instante_purga_programada = datetime.now(timezone.utc) - timedelta(days=1)
    sesion.commit()

    anonimizados = anonimizar_clientes_vencidos(sesion)
    assert anonimizados == 1

    sesion.expire_all()
    cliente_anonimizado = sesion.get(type(cliente), cliente.id_cliente)
    assert cliente_anonimizado.nombre is None
    assert cliente_anonimizado.fecha_nacimiento is None
    assert cliente_anonimizado.contacto is None
    assert cliente_anonimizado.anonimizado is True
    assert cliente_anonimizado.instante_anonimizacion is not None

    # Las métricas agregadas sobreviven (FR-016): ni intervalo_compra ni senal_fuga se borran.
    intervalo_despues = sesion.get(IntervaloCompra, cliente.id_cliente)
    assert intervalo_despues is not None
    assert intervalo_despues.intervalo_esperado_dias == 10
    senal_despues = sesion.get(SenalFuga, senal.id_senal_fuga)
    assert senal_despues is not None
    assert senal_despues.estado == "confirmada"


def test_nueva_visita_antes_de_vencer_la_purga_cancela_la_anonimizacion(sesion):
    cliente, escenario = _crear_cliente_con_historial_antiguo(sesion, nombre="Fuga Cancelada")

    evaluar_fugas_pendientes(sesion)
    senal = sesion.execute(
        select(SenalFuga).where(SenalFuga.id_cliente == cliente.id_cliente)
    ).scalar_one()
    assert senal.estado == "confirmada"

    # Purga programada en el futuro cercano (no vencida todavía) — a diferencia del otro
    # escenario, aquí sí debe importar que el plazo NO haya vencido.
    senal.instante_purga_programada = datetime.now(timezone.utc) + timedelta(days=5)
    sesion.commit()

    # El cliente vuelve a comprar antes de que venza el plazo.
    venta_regreso, _creada, _adv, _lotes = registrar_venta(
        sesion,
        clave_idempotencia=f"regreso-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=None,
        renglones=[
            RenglonEntrada(
                id_producto=escenario["producto"].id_producto,
                cantidad_unidades=1,
                cantidad_gramos=None,
            )
        ],
    )
    registrar_visita(sesion, id_cliente=cliente.id_cliente, id_venta=venta_regreso.id_venta)

    sesion.expire_all()
    senal_resuelta = sesion.get(SenalFuga, senal.id_senal_fuga)
    assert senal_resuelta.estado == "resuelta"
    assert senal_resuelta.instante_purga_programada is None

    anonimizados = anonimizar_clientes_vencidos(sesion)
    assert anonimizados == 0

    cliente_intacto = sesion.get(type(cliente), cliente.id_cliente)
    assert cliente_intacto.anonimizado is False
    assert cliente_intacto.nombre == "Fuga Cancelada"
