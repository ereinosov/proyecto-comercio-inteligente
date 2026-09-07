"""Registro de cliente y de visita (T007, T008). `registrar_visita` es idempotente por
`id_venta` (data-model.md: `visita.id_venta UNIQUE`) y nunca forma parte de la transacción de
`POST /ventas` de 001 — se llama después de que esa venta ya se confirmó (research.md #5).
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rasero.dominio.fuga_cliente import evaluar_estado_fuga
from rasero.dominio.identidad_cliente import validar_identificador
from rasero.dominio.valor_cliente import (
    AgregadoCliente,
    ValorCliente,
    calcular_intervalo_esperado,
    calcular_percentiles_y_compuesto,
)
from rasero.errores import (
    IdentificadorDuplicado,
    IdentificadorInvalido,
    RecursoNoEncontrado,
    VentaYaVinculada,
)
from rasero.persistencia.modelos import Cliente, IntervaloCompra, SenalFuga, Venta, Visita
from rasero.servicios import margen_resolver

ESTADOS_SENAL_ABIERTA = ("activa", "confirmada")


def _normalizar_identificador(identificador: str | None) -> str | None:
    """Cadena vacía o sólo espacios -> `None` (sin identificador). Un identificador con valor se
    valida contra el dominio (FR-017) y se rechaza 422 si está mal formado — nunca bloquea la
    venta porque nunca es obligatorio, pero si se provee tiene que ser correcto.
    """
    if identificador is None:
        return None
    limpio = identificador.strip()
    if limpio == "":
        return None
    if not validar_identificador(limpio):
        raise IdentificadorInvalido()
    return limpio


def _verificar_identificador_libre(
    sesion: Session, *, identificador: str, excluir_id_cliente: int | None = None
) -> None:
    """409 si `identificador` ya pertenece a otro cliente ACTIVO (no anonimizado). Nunca fusiona
    registros: el cajero debe buscar al cliente existente en vez de crear uno nuevo.
    """
    consulta = select(Cliente.id_cliente).where(
        Cliente.identificador == identificador, Cliente.anonimizado.is_(False)
    )
    if excluir_id_cliente is not None:
        consulta = consulta.where(Cliente.id_cliente != excluir_id_cliente)
    if sesion.execute(consulta).first() is not None:
        raise IdentificadorDuplicado()


def registrar_cliente(
    sesion: Session,
    *,
    nombre: str | None = None,
    fecha_nacimiento: date | None = None,
    contacto: str | None = None,
    identificador: str | None = None,
) -> Cliente:
    """`nombre` y `fecha_nacimiento` son opcionales: un cliente puede quedar registrado sólo por
    su identificador (o incluso sin nada, si el cajero sólo quiere anotarlo), igual que el modelo
    ORM los tiene NULL-ables. Sin `fecha_nacimiento` el cliente simplemente no será elegible para
    el cupón de cumpleaños de 005. El `identificador`, si se provee, se valida (422) y se
    comprueba que no exista ya en otro cliente activo (409); nunca es obligatorio (FR-003).
    """
    identificador = _normalizar_identificador(identificador)
    if identificador is not None:
        _verificar_identificador_libre(sesion, identificador=identificador)
    cliente = Cliente(
        nombre=nombre,
        fecha_nacimiento=fecha_nacimiento,
        contacto=contacto,
        identificador=identificador,
        fecha_alta=datetime.now(timezone.utc),
    )
    sesion.add(cliente)
    sesion.commit()
    return cliente


def actualizar_cliente(
    sesion: Session,
    *,
    id_cliente: int,
    nombre: str | None = None,
    fecha_nacimiento: date | None = None,
    contacto: str | None = None,
    identificador: str | None = None,
) -> Cliente:
    """Edición de un cliente ya registrado. NO requiere rol `encargado` (FR-063, enmienda
    v2.3.0): cualquier cajero puede
    editar un cliente, igual que ya puede crearlo desde la venta. Un cliente anonimizado
    (FR-015/FR-016 de 002) no se edita: sus datos personales ya no existen. El `identificador`,
    si se provee, se valida (422) y se comprueba unicidad contra otros clientes activos (409).
    """
    cliente = sesion.get(Cliente, id_cliente)
    if cliente is None:
        raise RecursoNoEncontrado(f"El cliente {id_cliente} no existe.")
    if cliente.anonimizado:
        raise RecursoNoEncontrado(
            "Este cliente fue anonimizado y sus datos personales ya no pueden editarse."
        )
    identificador = _normalizar_identificador(identificador)
    if identificador is not None:
        _verificar_identificador_libre(
            sesion, identificador=identificador, excluir_id_cliente=id_cliente
        )
    cliente.nombre = nombre
    cliente.fecha_nacimiento = fecha_nacimiento
    cliente.contacto = contacto
    cliente.identificador = identificador
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


def _clasificar_estado_fuga(intervalo_estado: str | None, senal_estado: str | None) -> str:
    """Clasificación única de fuga que comparten el detalle (`_fuga_a_respuesta`), el listado
    (`_resumen_cliente`) y el resumen por segmento: `datos_insuficientes` si el intervalo no
    está calculado; si no, el estado de la última señal (activa/confirmada/resuelta); si nunca
    hubo señal, `sin_senal`. Nunca se reimplementa en ninguno de esos tres sitios.
    """
    if intervalo_estado is None or intervalo_estado == "datos_insuficientes":
        return "datos_insuficientes"
    if senal_estado is not None:
        return senal_estado
    return "sin_senal"


def _estado_fuga_por_cliente(
    sesion: Session, ids_cliente: list[int] | None = None
) -> dict[int, str]:
    """Estado de fuga (misma clasificación que el detalle) indexado por `id_cliente`, resuelto
    en UNA sola query con la "última señal por cliente" por subconsulta — mismo patrón que
    `resumen_fuga_por_segmento`. Nunca una consulta por cliente en un loop: el listado es
    paginado y este cálculo se hace con una única query adicional por página.
    """
    subq_max = (
        select(
            SenalFuga.id_cliente,
            func.max(SenalFuga.id_senal_fuga).label("max_id"),
        )
        .group_by(SenalFuga.id_cliente)
        .subquery()
    )
    ultima_senal = (
        select(SenalFuga.id_cliente.label("id_cliente"), SenalFuga.estado.label("estado"))
        .join(subq_max, SenalFuga.id_senal_fuga == subq_max.c.max_id)
        .subquery()
    )
    consulta = (
        select(Cliente.id_cliente, IntervaloCompra.estado, ultima_senal.c.estado)
        .outerjoin(IntervaloCompra, IntervaloCompra.id_cliente == Cliente.id_cliente)
        .outerjoin(ultima_senal, ultima_senal.c.id_cliente == Cliente.id_cliente)
    )
    if ids_cliente is not None:
        consulta = consulta.where(Cliente.id_cliente.in_(ids_cliente))
    return {
        id_cliente: _clasificar_estado_fuga(intervalo_estado, senal_estado)
        for id_cliente, intervalo_estado, senal_estado in sesion.execute(consulta).all()
    }


def _resumen_cliente(
    cliente: Cliente,
    valores: dict[int, ValorCliente],
    montos: dict[int, Decimal],
    estados_fuga: dict[int, str],
) -> dict:
    valor = valores.get(cliente.id_cliente)
    return {
        "id_cliente": cliente.id_cliente,
        "nombre": cliente.nombre,
        "valor": valor.compuesto if valor else None,
        "monto_total": montos.get(cliente.id_cliente, Decimal("0")),
        # Campo aditivo (mismo patrón que `nombre_cliente` en cupones): un consumidor que lo
        # ignora no se rompe. Permite el tint de fuga por fila en Clientes.tsx sin pedir el
        # detalle de cada cliente (evita N+1).
        "estado_fuga": estados_fuga.get(cliente.id_cliente, "datos_insuficientes"),
    }


def listar_valor_clientes(
    sesion: Session, *, orden: str = "valor", busqueda: str | None = None
) -> list[dict]:
    """Registro de Análisis (FR-011b consume el detalle; esto es el listado resumen). Clientes
    anonimizados quedan fuera: sin nombre, no hay nada accionable que mostrar de ellos aquí.

    `busqueda` filtra por nombre (ILIKE '%busqueda%'); se combina con la paginación del
    endpoint, nunca la reemplaza. Un `busqueda` vacío o sólo espacios se ignora.
    """
    valores = obtener_valor_clientes(sesion)
    montos = _montos_por_cliente(sesion)
    consulta = select(Cliente).where(Cliente.anonimizado.is_(False))
    if busqueda and busqueda.strip():
        consulta = consulta.where(Cliente.nombre.ilike(f"%{busqueda.strip()}%"))
    clientes = sesion.execute(consulta).scalars().all()
    estados_fuga = _estado_fuga_por_cliente(sesion, [c.id_cliente for c in clientes])

    filas = [_resumen_cliente(c, valores, montos, estados_fuga) for c in clientes]
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
    estados_fuga = _estado_fuga_por_cliente(sesion, [c.id_cliente for c in clientes])
    return [_resumen_cliente(c, valores, montos, estados_fuga) for c in clientes]


def _fuga_a_respuesta(intervalo: IntervaloCompra | None, senal: SenalFuga | None) -> dict:
    estado = _clasificar_estado_fuga(
        intervalo.estado if intervalo else None, senal.estado if senal else None
    )

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
# Resumen de fuga por segmento (User Story 6, FR-018..FR-020) — lectura pura
# --------------------------------------------------------------------------

SEGMENTOS_FUGA = ("sin_senal", "datos_insuficientes", "activa", "confirmada", "resuelta")


def resumen_fuga_por_segmento(sesion: Session) -> dict[str, int]:
    """Distribución instantánea de los clientes (no anonimizados) por segmento de fuga, con la
    MISMA clasificación que `_fuga_a_respuesta` usa en el detalle: `datos_insuficientes` si el
    intervalo no está calculado; si no, el estado de la última señal (activa/confirmada/resuelta);
    si nunca hubo señal, `sin_senal`.

    Es un snapshot: `senal_fuga` no guarda un histórico periódico, así que no se inventa una
    serie temporal — se cuenta el estado actual.
    """
    subq_max = (
        select(
            SenalFuga.id_cliente,
            func.max(SenalFuga.id_senal_fuga).label("max_id"),
        )
        .group_by(SenalFuga.id_cliente)
        .subquery()
    )
    ultima_senal = (
        select(SenalFuga.id_cliente.label("id_cliente"), SenalFuga.estado.label("estado"))
        .join(subq_max, SenalFuga.id_senal_fuga == subq_max.c.max_id)
        .subquery()
    )

    filas = sesion.execute(
        select(Cliente.id_cliente, IntervaloCompra.estado, ultima_senal.c.estado)
        .outerjoin(IntervaloCompra, IntervaloCompra.id_cliente == Cliente.id_cliente)
        .outerjoin(ultima_senal, ultima_senal.c.id_cliente == Cliente.id_cliente)
        .where(Cliente.anonimizado.is_(False))
    ).all()

    conteo = {segmento: 0 for segmento in SEGMENTOS_FUGA}
    for _id_cliente, intervalo_estado, senal_estado in filas:
        conteo[_clasificar_estado_fuga(intervalo_estado, senal_estado)] += 1
    return conteo


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
