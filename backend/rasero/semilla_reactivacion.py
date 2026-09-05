"""Datos de demostración del experimento de reactivación (005-promociones-inteligentes, T048).

    python -m rasero.semilla_reactivacion

Crea 325 clientes de "Despensa Los Ríos" con `senal_fuga` ACTIVA — margen operativo sobre el
mínimo real de diseño `n* = 242` (research.md #10c). El atrezo se construye **exclusivamente con
los servicios públicos de 002 (`registrar_cliente`, `registrar_visita`) y de 001 (`registrar_venta`)**:
005 nunca escribe directo en `visita` ni en `senal_fuga`. Es `evaluar_fugas_pendientes` de 002
quien asigna la señal, porque la última compra de cada cliente quedó lo bastante atrás.

`simular_retornos(id_experimento, tasa_control=0.15, tasa_tratamiento=0.29)` registra las visitas
de retorno de la ventana de medición a esas tasas por grupo (también vía `registrar_visita` de
002) y adelanta `instante_asignacion` del experimento para que la ventana ya haya vencido, de modo
que `POST /promociones/experimentos/{id}/cierre` arroje `veredicto = 'efectivo'` de forma
**reproducible** con `SEMILLA_ALEATORIZACION = 20260905` (quickstart.md, escenario 7).

**Datos de demostración para el examen, no un supuesto del modelo ni un parámetro de diseño.** El
mínimo real que el diseño experimental exige sigue siendo `n* = 242`; si la población real fuera
menor, el sistema responde `muestra_insuficiente`, no una conclusión inventada (FR-025).
"""

import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.config import promociones as cfg
from rasero.dominio.experimento import tamano_minimo_muestra
from rasero.persistencia.modelos import (
    AsignacionExperimento,
    ExperimentoReactivacion,
    Lote,
    Operador,
    Producto,
    SenalFuga,
    Sucursal,
    Turno,
)
from rasero.persistencia.movimientos import registrar_movimiento
from rasero.persistencia.sesion import SesionLocal
from rasero.seguridad import hashear_pin
from rasero.servicios.clientes import (
    evaluar_fugas_pendientes,
    registrar_cliente,
    registrar_visita,
)
from rasero.servicios.ventas import RenglonEntrada, registrar_venta

N_CLIENTES = 325  # margen operativo sobre n* = 242 (research.md #10c)
INTERVALO_DIAS = 25
DIAS_ULTIMA_COMPRA = 80  # > INTERVALO y < 365 -> senal_fuga 'activa', no 'confirmada'
_NOMBRE_SUCURSAL = "Despensa Los Ríos — Reactivación"
_NOMBRE_PRODUCTO = "Arroz 1 kg (reactivación)"


def _escenario(sesion: Session) -> dict:
    """Reutiliza el atrezo si ya existe (idempotente); si no, lo crea con stock amplio vía
    `registrar_movimiento` (mismo criterio que `rasero/semilla.py`).
    """
    sucursal = sesion.execute(
        select(Sucursal).where(Sucursal.nombre == _NOMBRE_SUCURSAL)
    ).scalar_one_or_none()
    if sucursal is None:
        sucursal = Sucursal(nombre=_NOMBRE_SUCURSAL, zona_horaria="America/Guayaquil")
        sesion.add(sucursal)
        sesion.flush()

    producto = sesion.execute(
        select(Producto).where(Producto.nombre == _NOMBRE_PRODUCTO)
    ).scalar_one_or_none()
    if producto is None:
        producto = Producto(
            nombre=_NOMBRE_PRODUCTO,
            es_granel=False,
            precio_vigente=Decimal("1.2000"),
            lleva_caducidad=False,
        )
        sesion.add(producto)
        sesion.flush()

    operador = sesion.execute(
        select(Operador).where(Operador.nombre == "Cajera Reactivación")
    ).scalar_one_or_none()
    if operador is None:
        operador = Operador(
            nombre="Cajera Reactivación", pin_hash="", es_encargado=False, activo=True
        )
        sesion.add(operador)
        sesion.flush()
        operador.pin_hash = hashear_pin("1234", str(operador.id_operador))
        sesion.flush()

    turno = sesion.execute(
        select(Turno)
        .where(Turno.id_sucursal == sucursal.id_sucursal, Turno.instante_cierre.is_(None))
        .limit(1)
    ).scalar_one_or_none()
    if turno is None:
        turno = Turno(
            id_operador=operador.id_operador,
            id_sucursal=sucursal.id_sucursal,
            caja="caja-reactivacion",
            instante_apertura=datetime.now(timezone.utc) - timedelta(days=400),
        )
        sesion.add(turno)
        sesion.flush()

    lote = sesion.execute(
        select(Lote).where(
            Lote.id_producto == producto.id_producto,
            Lote.id_sucursal == sucursal.id_sucursal,
        )
    ).scalar_one_or_none()
    if lote is None:
        lote = Lote(
            id_producto=producto.id_producto,
            id_sucursal=sucursal.id_sucursal,
            costo_unitario=Decimal("0.8000"),
            fecha_caducidad=None,
            instante_entrada=datetime.now(timezone.utc) - timedelta(days=400),
        )
        sesion.add(lote)
        sesion.flush()

    registrar_movimiento(
        sesion,
        id_sucursal=sucursal.id_sucursal,
        id_producto=producto.id_producto,
        id_lote=lote.id_lote,
        tipo="entrada_compra",
        cantidad=Decimal(N_CLIENTES * 8),
        instante=datetime.now(timezone.utc) - timedelta(days=400),
    )
    sesion.commit()
    return {"sucursal": sucursal, "producto": producto, "turno": turno}


def _venta(sesion: Session, escenario: dict, *, instante: datetime) -> int:
    venta, _c, _a, _l = registrar_venta(
        sesion,
        clave_idempotencia=f"reactivacion-{uuid.uuid4()}",
        id_turno=escenario["turno"].id_turno,
        referencia_terminal_pago=None,
        instante_origen=instante,
        renglones=[
            RenglonEntrada(
                id_producto=escenario["producto"].id_producto,
                cantidad_unidades=1,
                cantidad_gramos=None,
            )
        ],
    )
    return venta.id_venta


def sembrar() -> dict:
    sesion = SesionLocal()
    try:
        escenario = _escenario(sesion)
        ahora = datetime.now(timezone.utc)
        # 3 visitas (2 intervalos) -> intervalo_compra 'calculado'; la última hace
        # DIAS_ULTIMA_COMPRA días -> senal_fuga 'activa' tras evaluar_fugas_pendientes.
        offsets = [
            DIAS_ULTIMA_COMPRA + 2 * INTERVALO_DIAS,
            DIAS_ULTIMA_COMPRA + 1 * INTERVALO_DIAS,
            DIAS_ULTIMA_COMPRA,
        ]
        creados = 0
        for i in range(N_CLIENTES):
            cliente = registrar_cliente(
                sesion,
                nombre=f"Cliente reactivación {i + 1:03d}",
                fecha_nacimiento=date(1988, ((i % 12) + 1), ((i % 27) + 1)),
            )
            for offset in offsets:
                id_venta = _venta(sesion, escenario, instante=ahora - timedelta(days=offset))
                registrar_visita(sesion, id_cliente=cliente.id_cliente, id_venta=id_venta)
            creados += 1

        tocados = evaluar_fugas_pendientes(sesion)
        activas = sesion.execute(
            select(func.count()).select_from(SenalFuga).where(SenalFuga.estado == "activa")
        ).scalar_one()
        print(
            f"Sembrados {creados} clientes de reactivación; "
            f"evaluar_fugas_pendientes tocó {tocados}; "
            f"señales de fuga activas en la base: {activas}."
        )
        print(
            f"Sucursal de demostración: id={escenario['sucursal'].id_sucursal} ({_NOMBRE_SUCURSAL})"
        )
        print(f"n* de diseño = {2 * _n_star()} elegibles mínimos ({N_CLIENTES} disponibles).")
        return {
            "id_sucursal": escenario["sucursal"].id_sucursal,
            "clientes_creados": creados,
            "senales_activas": activas,
        }
    finally:
        sesion.close()


def _n_star() -> int:
    return tamano_minimo_muestra(
        p_control=cfg.TASA_RETORNO_BASE_ESPERADA,
        mde_puntos_porcentuales=cfg.MDE_REACTIVACION_PP,
        z_alfa_medios=cfg.Z_ALFA_MEDIOS,
        z_beta=cfg.Z_BETA,
    )


def simular_retornos(
    id_experimento: int,
    *,
    tasa_control: float = 0.15,
    tasa_tratamiento: float = 0.29,
) -> dict:
    """Registra las visitas de retorno de la ventana de medición a las tasas dadas por grupo y
    adelanta `instante_asignacion` para que la ventana ya haya vencido. Determinista: elige los
    clientes que "vuelven" por orden de `id_asignacion_experimento`, de modo que el cierre dé el
    mismo `veredicto` en cada corrida.
    """
    sesion = SesionLocal()
    try:
        experimento = sesion.get(ExperimentoReactivacion, id_experimento)
        if experimento is None:
            raise SystemExit(f"El experimento {id_experimento} no existe.")
        if experimento.veredicto not in ("en_curso", "efectivo", "no_efectivo"):
            raise SystemExit(
                f"El experimento {id_experimento} está en '{experimento.veredicto}': "
                "no hay grupos que medir."
            )

        escenario = _escenario(sesion)
        ventana = experimento.ventana_medicion_dias
        nueva_asignacion = datetime.now(timezone.utc) - timedelta(days=ventana + 1)
        experimento.instante_asignacion = nueva_asignacion
        experimento.instante_cierre = None
        sesion.flush()

        instante_retorno = nueva_asignacion + timedelta(days=max(1, ventana // 3))
        resumen = {}
        for grupo, tasa in (
            ("control", tasa_control),
            ("tratamiento", tasa_tratamiento),
        ):
            asignaciones = list(
                sesion.execute(
                    select(AsignacionExperimento)
                    .where(
                        AsignacionExperimento.id_experimento_reactivacion == id_experimento,
                        AsignacionExperimento.grupo == grupo,
                    )
                    .order_by(AsignacionExperimento.id_asignacion_experimento)
                ).scalars()
            )
            cuantos = round(len(asignaciones) * tasa)
            for asignacion in asignaciones[:cuantos]:
                id_venta = _venta(sesion, escenario, instante=instante_retorno)
                registrar_visita(sesion, id_cliente=asignacion.id_cliente, id_venta=id_venta)
            resumen[grupo] = {"total": len(asignaciones), "retornaron": cuantos}
        sesion.commit()
        print(
            f"Retornos simulados para el experimento {id_experimento}: "
            f"tratamiento {resumen['tratamiento']['retornaron']}/{resumen['tratamiento']['total']}, "
            f"control {resumen['control']['retornaron']}/{resumen['control']['total']}. "
            "Ventana de medición vencida: ya puede cerrarse."
        )
        return resumen
    finally:
        sesion.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "simular-retornos":
        simular_retornos(int(args[1]))
    else:
        sembrar()
