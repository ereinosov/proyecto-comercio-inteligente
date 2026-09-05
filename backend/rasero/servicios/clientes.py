"""Registro de cliente y de visita (T007, T008). `registrar_visita` es idempotente por
`id_venta` (data-model.md: `visita.id_venta UNIQUE`) y nunca forma parte de la transacción de
`POST /ventas` de 001 — se llama después de que esa venta ya se confirmó (research.md #5).
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.dominio.fuga_cliente import evaluar_estado_fuga
from rasero.dominio.valor_cliente import (
    AgregadoCliente,
    ValorCliente,
    calcular_intervalo_esperado,
    calcular_percentiles_y_compuesto,
)
from rasero.errores import RecursoNoEncontrado, VentaYaVinculada
from rasero.persistencia.modelos import Cliente, IntervaloCompra, SenalFuga, Venta, Visita
from rasero.servicios import margen_resolver

ESTADOS_SENAL_ABIERTA = ("activa", "confirmada")


def registrar_cliente(
    sesion: Session, *, nombre: str, fecha_nacimiento: date, contacto: str | None = None
) -> Cliente:
    """Nombre y fecha de nacimiento obligatorios (FR-001); ya los exige el esquema de la
    petición (Pydantic, no Optional) antes de llegar aquí.
    """
    cliente = Cliente(
        nombre=nombre,
        fecha_nacimiento=fecha_nacimiento,
        contacto=contacto,
        fecha_alta=datetime.now(timezone.utc),
    )
    sesion.add(cliente)
    sesion.commit()
    return cliente


def _recalcular_intervalo_compra(sesion: Session, *, id_cliente: int) -> None:
    instantes = list(
        sesion.execute(
            select(Visita.instante).where(Visita.id_cliente == id_cliente)
        ).scalars()
    )
    resultado = calcular_intervalo_esperado(instantes)

    intervalo = sesion.get(IntervaloCompra, id_cliente)
    if intervalo is None:
        intervalo = IntervaloCompra(id_cliente=id_cliente)
        sesion.add(intervalo)

    intervalo.intervalo_esperado_dias = resultado.intervalo_esperado_dias
    intervalo.visitas_consideradas = resultado.visitas_consideradas
    intervalo.estado = resultado.estado
    intervalo.instante_calculo = datetime.now(timezone.utc)
    sesion.flush()


def _senal_abierta(sesion: Session, *, id_cliente: int) -> SenalFuga | None:
    return sesion.execute(
        select(SenalFuga).where(
            SenalFuga.id_cliente == id_cliente, SenalFuga.estado.in_(ESTADOS_SENAL_ABIERTA)
        )
    ).scalar_one_or_none()


def _resolver_senal_fuga_si_abierta(sesion: Session, *, id_cliente: int) -> None:
    """FR-009: una nueva visita resuelve cualquier señal `activa` o `confirmada` — en este
    segundo caso, además cancela la anonimización programada (FR-015)."""
    senal = _senal_abierta(sesion, id_cliente=id_cliente)
    if senal is None:
        return
    senal.estado = "resuelta"
    senal.instante_resolucion = datetime.now(timezone.utc)
    senal.instante_purga_programada = None
    sesion.flush()


def registrar_visita(sesion: Session, *, id_cliente: int, id_venta: int) -> tuple[Visita, bool]:
    """Devuelve (visita, creada_ahora). `creada_ahora=False` en un reintento sobre la misma
    venta ya vinculada a este mismo cliente (idempotencia, igual patrón que `venta` en 001).
    """
    cliente = sesion.get(Cliente, id_cliente)
    if cliente is None:
        raise RecursoNoEncontrado(f"El cliente {id_cliente} no existe.")

    existente = sesion.execute(
        select(Visita).where(Visita.id_venta == id_venta)
    ).scalar_one_or_none()
    if existente is not None:
        if existente.id_cliente != id_cliente:
            raise VentaYaVinculada()
        return existente, False

    venta = sesion.get(Venta, id_venta)
    if venta is None:
        raise RecursoNoEncontrado(f"La venta {id_venta} no existe.")

    margen_relativo = margen_resolver.resolver_margen_visita(sesion, id_venta=id_venta)

    visita = Visita(
        id_cliente=id_cliente,
        id_venta=id_venta,
        instante=venta.instante,
        monto_total=venta.total,
        margen_relativo=margen_relativo,
    )
    sesion.add(visita)
    sesion.flush()

    _recalcular_intervalo_compra(sesion, id_cliente=id_cliente)
    _resolver_senal_fuga_si_abierta(sesion, id_cliente=id_cliente)

    sesion.commit()
    return visita, True


def buscar_clientes(sesion: Session, *, q: str, limite: int = 20) -> list[Cliente]:
    """Búsqueda para identificación opcional en el punto de venta (FR-003). Excluye clientes
    anonimizados: su `nombre` es NULL (data-model.md) y no puede coincidir con `q`.
    """
    return list(
        sesion.execute(
            select(Cliente)
            .where(Cliente.nombre.ilike(f"%{q}%"))
            .order_by(Cliente.nombre)
            .limit(limite)
        ).scalars()
    )


# --------------------------------------------------------------------------
# Valor de cliente (T018-T022, User Story 2)
# --------------------------------------------------------------------------


def obtener_valor_clientes(sesion: Session) -> dict[int, ValorCliente]:
    """Valor (percentiles + compuesto) indexado por `id_cliente`, para todos los clientes con
    `intervalo_compra.estado = 'calculado'`. Un cliente que no aparece en el resultado no tiene
    valor: no se le asigna ninguno por defecto (FR-007) — es responsabilidad de quien llama
    distinguir su ausencia, nunca inventarle un cero.
    """
    filas = sesion.execute(
        select(
            Cliente.id_cliente,
            IntervaloCompra.intervalo_esperado_dias,
            func.sum(Visita.monto_total).label("monto_total"),
            func.sum(Visita.monto_total * Visita.margen_relativo).label("monto_por_margen"),
        )
        .join(IntervaloCompra, IntervaloCompra.id_cliente == Cliente.id_cliente)
        .join(Visita, Visita.id_cliente == Cliente.id_cliente)
        .where(IntervaloCompra.estado == "calculado")
        .group_by(Cliente.id_cliente, IntervaloCompra.intervalo_esperado_dias)
    ).all()

    poblacion = [
        AgregadoCliente(
            id_cliente=fila.id_cliente,
            intervalo_esperado_dias=fila.intervalo_esperado_dias,
            monto_total=fila.monto_total,
            # Ratio de margen del cliente ponderado por el monto de cada visita — equivale a
            # margen bruto total / monto total (research.md #4), no un promedio simple de ratios.
            margen_ponderado=(fila.monto_por_margen / fila.monto_total)
            if fila.monto_total
            else Decimal("0"),
        )
        for fila in filas
    ]
    return {v.id_cliente: v for v in calcular_percentiles_y_compuesto(poblacion)}


def _montos_por_cliente(sesion: Session) -> dict[int, Decimal]:
    filas = sesion.execute(
        select(Visita.id_cliente, func.sum(Visita.monto_total)).group_by(Visita.id_cliente)
    ).all()
    return dict(filas)


def _resumen_cliente(
    cliente: Cliente, valores: dict[int, ValorCliente], montos: dict[int, Decimal]
) -> dict:
    valor = valores.get(cliente.id_cliente)
    return {
        "id_cliente": cliente.id_cliente,
        "nombre": cliente.nombre,
        "valor": valor.compuesto if valor else None,
        "monto_total": montos.get(cliente.id_cliente, Decimal("0")),
    }


def listar_valor_clientes(sesion: Session, *, orden: str = "valor") -> list[dict]:
    """Registro de Análisis (FR-011b consume el detalle; esto es el listado resumen). Clientes
    anonimizados quedan fuera: sin nombre, no hay nada accionable que mostrar de ellos aquí.
    """
    valores = obtener_valor_clientes(sesion)
    montos = _montos_por_cliente(sesion)
    clientes = sesion.execute(
        select(Cliente).where(Cliente.anonimizado.is_(False))
    ).scalars().all()

    filas = [_resumen_cliente(c, valores, montos) for c in clientes]
    if orden == "monto_total":
        filas.sort(key=lambda f: f["monto_total"], reverse=True)
    else:
        # Sin valor (datos_insuficientes) al final, nunca mezclado como si fuera un cero.
        filas.sort(key=lambda f: (f["valor"] is None, -(f["valor"] or 0)))
    return filas


def buscar_clientes_con_valor(sesion: Session, *, q: str, limite: int = 20) -> list[dict]:
    """Igual que `buscar_clientes` (FR-003), pero con la puntuación compuesta real ya conectada
    (T022) en vez del `valor: null` provisional de User Story 1.
    """
    clientes = buscar_clientes(sesion, q=q, limite=limite)
    valores = obtener_valor_clientes(sesion)
    montos = _montos_por_cliente(sesion)
    return [_resumen_cliente(c, valores, montos) for c in clientes]


def _fuga_a_respuesta(intervalo: IntervaloCompra | None, senal: SenalFuga | None) -> dict:
    if intervalo is None or intervalo.estado == "datos_insuficientes":
        estado = "datos_insuficientes"
    elif senal is not None:
        estado = senal.estado
    else:
        estado = "sin_senal"

    return {
        "estado": estado,
        "intervalo_esperado_dias": (
            float(intervalo.intervalo_esperado_dias)
            if intervalo and intervalo.intervalo_esperado_dias is not None
            else None
        ),
        "instante_deteccion": senal.instante_deteccion if senal else None,
        "instante_confirmacion": senal.instante_confirmacion if senal else None,
        "instante_resolucion": senal.instante_resolucion if senal else None,
    }


def obtener_detalle_cliente(sesion: Session, *, id_cliente: int) -> dict | None:
    """Registro de Análisis: cliente, desglose de valor (FR-011b) y estado de fuga (T035)."""
    cliente = sesion.get(Cliente, id_cliente)
    if cliente is None:
        return None

    valor = obtener_valor_clientes(sesion).get(id_cliente)
    detalle_valor = None
    if valor is not None:
        detalle_valor = {
            "compuesto": valor.compuesto,
            "percentil_frecuencia": valor.percentil_frecuencia,
            "percentil_monto": valor.percentil_monto,
            "percentil_margen": valor.percentil_margen,
        }

    intervalo = sesion.get(IntervaloCompra, id_cliente)
    # La señal más reciente, abierta o no: para mostrar "resuelta" en el detalle también hace
    # falta la última señal aunque ya no esté abierta.
    ultima_senal = sesion.execute(
        select(SenalFuga)
        .where(SenalFuga.id_cliente == id_cliente)
        .order_by(SenalFuga.id_senal_fuga.desc())
        .limit(1)
    ).scalar_one_or_none()

    return {
        "cliente": cliente,
        "valor": detalle_valor,
        "fuga": _fuga_a_respuesta(intervalo, ultima_senal),
    }


# --------------------------------------------------------------------------
# Fuga silenciosa (T028-T037, User Story 3)
# --------------------------------------------------------------------------


def evaluar_fugas_pendientes(sesion: Session) -> int:
    """Job de fondo (research.md #6): recorre clientes con `intervalo_compra.estado =
    'calculado'` que no tienen señal abierta o cuya señal está `activa`, y la crea o la
    escala a `confirmada` según `evaluar_estado_fuga` (FR-008, FR-014).

    NUNCA se invoca desde un endpoint HTTP — solo desde
    `tareas/mantenimiento_clientes.py` (T034) o pruebas. Devuelve cuántos clientes se
    tocaron, para que la tarea programada pueda registrarlo.
    """
    ahora = datetime.now(timezone.utc)
    tocados = 0

    candidatos = sesion.execute(
        select(Cliente.id_cliente, IntervaloCompra.intervalo_esperado_dias)
        .join(IntervaloCompra, IntervaloCompra.id_cliente == Cliente.id_cliente)
        .where(IntervaloCompra.estado == "calculado", Cliente.anonimizado.is_(False))
    ).all()

    for id_cliente, intervalo_esperado_dias in candidatos:
        senal = _senal_abierta(sesion, id_cliente=id_cliente)
        if senal is not None and senal.estado == "confirmada":
            continue  # ya confirmada: la anonimización, no esta evaluación, decide su destino

        ultima_visita = sesion.execute(
            select(func.max(Visita.instante)).where(Visita.id_cliente == id_cliente)
        ).scalar_one()
        dias_sin_visita = (ahora - ultima_visita).total_seconds() / 86400

        resultado = evaluar_estado_fuga(
            intervalo_esperado_dias=intervalo_esperado_dias,
            dias_sin_visita=dias_sin_visita,
            ahora=ahora,
        )

        if resultado.estado == "sin_senal":
            continue  # nada que crear ni cambiar (y una 'activa' no vuelve atrás sola: FR-009
            # la resuelve una visita nueva, no el paso del tiempo)

        if resultado.estado == "activa":
            if senal is None:
                sesion.add(
                    SenalFuga(id_cliente=id_cliente, estado="activa", instante_deteccion=ahora)
                )
                tocados += 1
            continue

        # resultado.estado == "confirmada"
        if senal is None:
            # No debería ocurrir si el job corre con regularidad (pasaría primero por
            # 'activa'); si corrió después de mucho tiempo sin ejecutarse, se aproxima
            # instante_deteccion a `ahora` por no tener un dato mejor — documentado aquí,
            # no es un caso silencioso.
            sesion.add(
                SenalFuga(
                    id_cliente=id_cliente,
                    estado="confirmada",
                    instante_deteccion=ahora,
                    instante_confirmacion=ahora,
                    instante_purga_programada=resultado.instante_purga_programada,
                )
            )
        else:
            senal.estado = "confirmada"
            senal.instante_confirmacion = ahora
            senal.instante_purga_programada = resultado.instante_purga_programada
        tocados += 1

    sesion.commit()
    return tocados


# --------------------------------------------------------------------------
# Cumpleaños (FR-012) — expuesto para que 005-promociones-inteligentes lo consuma
# --------------------------------------------------------------------------


def _mes_dia_en_rango(fecha_nacimiento: date, desde: date, hasta: date) -> bool:
    objetivo = (fecha_nacimiento.month, fecha_nacimiento.day)
    inicio, fin = (desde.month, desde.day), (hasta.month, hasta.day)
    if inicio <= fin:
        return inicio <= objetivo <= fin
    return objetivo >= inicio or objetivo <= fin  # rango que cruza el 31 dic -> 1 ene


def clientes_con_cumpleanos(sesion: Session, *, desde: date, hasta: date) -> list[Cliente]:
    """FR-012/FR-013: solo expone el dato: qué clientes cumplen años en el rango. No decide ni
    sugiere ninguna acción — eso es exclusivo de `005-promociones-inteligentes`. Excluye
    anonimizados: ya no tienen `fecha_nacimiento` (FR-016).
    """
    candidatos = sesion.execute(
        select(Cliente).where(
            Cliente.anonimizado.is_(False), Cliente.fecha_nacimiento.is_not(None)
        )
    ).scalars().all()
    return [c for c in candidatos if _mes_dia_en_rango(c.fecha_nacimiento, desde, hasta)]
