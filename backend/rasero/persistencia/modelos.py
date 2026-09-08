"""Modelos SQLAlchemy 2.x de las 20 tablas de data-model.md (constitución v2.2.0).

Nomenclatura: español, snake_case, singular, sin "ñ", claves foráneas id_ + tabla referida.
Ningún tipo de coma flotante: importes NUMERIC(12,2)/(12,4), pesos INTEGER/NUMERIC(14,0) enteros.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    BigInteger,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# Catálogo y estructura
# --------------------------------------------------------------------------


class Sucursal(Base):
    __tablename__ = "sucursal"

    id_sucursal: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    zona_horaria: Mapped[str] = mapped_column(String, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Categoria(Base):
    __tablename__ = "categoria"

    id_categoria: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    dias_umbral_inmovilizado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Producto(Base):
    __tablename__ = "producto"

    id_producto: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_categoria: Mapped[int | None] = mapped_column(ForeignKey("categoria.id_categoria"))
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    es_granel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    precio_vigente: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    lleva_caducidad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # US12: URL externa de una imagen del producto para el catálogo de Venta. Opcional —
    # `NULL` cae al ícono de familia de categoría (La Regla del Ícono por Categoría). El
    # frontend además hace fallback en runtime si la URL falla al cargar. Aditivo puro: los
    # consumidores de `producto` que no lo conozcan lo ignoran.
    url_imagen: Mapped[str | None] = mapped_column(String, nullable=True)


class ProductoPrecioSucursal(Base):
    """Override opcional del precio base de `producto` por sucursal (constitución v2.1.2)."""

    __tablename__ = "producto_precio_sucursal"

    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), primary_key=True)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), primary_key=True)
    precio_vigente: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")


class ZonaExhibicion(Base):
    __tablename__ = "zona_exhibicion"

    id_zona_exhibicion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    grado_privilegio: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# --------------------------------------------------------------------------
# Personas y turnos
# --------------------------------------------------------------------------


class Operador(Base):
    __tablename__ = "operador"

    id_operador: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    pin_hash: Mapped[str] = mapped_column(String, nullable=False)
    # Enmienda v2.3.0 (Principio VI): `id_sucursal` (sucursal fija, uno-a-uno) y `rol`
    # (ENUM cerrado cajero<encargado<admin) reemplazan al booleano de encargado anterior.
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    rol: Mapped[str] = mapped_column(String, nullable=False, default="cajero")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("rol IN ('cajero','encargado','admin')", name="ck_operador_rol"),
    )


class Turno(Base):
    __tablename__ = "turno"

    id_turno: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_operador: Mapped[int] = mapped_column(ForeignKey("operador.id_operador"), nullable=False)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    caja: Mapped[str] = mapped_column(String, nullable=False)
    instante_apertura: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    instante_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --------------------------------------------------------------------------
# Inventario
# --------------------------------------------------------------------------


class Lote(Base):
    __tablename__ = "lote"

    id_lote: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    fecha_caducidad: Mapped[date | None] = mapped_column(Date, nullable=True)
    instante_entrada: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"

    id_movimiento_inventario: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_lote: Mapped[int | None] = mapped_column(ForeignKey("lote.id_lote"), nullable=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False)
    instante: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    id_venta: Mapped[int | None] = mapped_column(ForeignKey("venta.id_venta"), nullable=True)
    id_traspaso: Mapped[int | None] = mapped_column(ForeignKey("traspaso.id_traspaso"), nullable=True)
    id_conteo_fisico: Mapped[int | None] = mapped_column(
        ForeignKey("conteo_fisico.id_conteo_fisico"), nullable=True
    )
    id_anulacion_venta: Mapped[int | None] = mapped_column(
        ForeignKey("anulacion_venta.id_anulacion_venta"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('entrada_compra','salida_venta','entrada_anulacion',"
            "'salida_traspaso','entrada_traspaso','ajuste_conteo')",
            name="ck_movimiento_tipo",
        ),
        CheckConstraint(
            "(tipo = 'entrada_compra' AND id_venta IS NULL AND id_traspaso IS NULL"
            "   AND id_conteo_fisico IS NULL AND id_anulacion_venta IS NULL)"
            " OR (tipo = 'salida_venta' AND id_venta IS NOT NULL AND id_traspaso IS NULL"
            "   AND id_conteo_fisico IS NULL AND id_anulacion_venta IS NULL)"
            " OR (tipo = 'entrada_anulacion' AND id_anulacion_venta IS NOT NULL"
            "   AND id_venta IS NULL AND id_traspaso IS NULL AND id_conteo_fisico IS NULL)"
            " OR (tipo IN ('salida_traspaso','entrada_traspaso') AND id_traspaso IS NOT NULL"
            "   AND id_venta IS NULL AND id_conteo_fisico IS NULL AND id_anulacion_venta IS NULL)"
            " OR (tipo = 'ajuste_conteo' AND id_conteo_fisico IS NOT NULL"
            "   AND id_venta IS NULL AND id_traspaso IS NULL AND id_anulacion_venta IS NULL)",
            name="ck_movimiento_origen_unico",
        ),
    )


class Existencia(Base):
    """Agregación derivada, no autoritativa (data-model.md). Ante discrepancia gana la
    recomputación desde movimiento_inventario.

    Corrección de implementación: PostgreSQL prohíbe columnas NULL en una PRIMARY KEY, y
    data-model.md declaraba id_lote nulo como parte de la PK compuesta. Se usa una clave
    sustituta (id_existencia) más UNIQUE NULLS NOT DISTINCT (PG15+) sobre las tres columnas
    de identidad, que sí admite NULL en id_lote tratando todos los NULL como equivalentes
    entre sí — el mismo efecto que una PK, con NULL admitido.
    """

    __tablename__ = "existencia"

    id_existencia: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_lote: Mapped[int | None] = mapped_column(ForeignKey("lote.id_lote"), nullable=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False, default=Decimal(0))

    __table_args__ = (
        UniqueConstraint(
            "id_sucursal",
            "id_producto",
            "id_lote",
            name="uq_existencia_identidad",
            postgresql_nulls_not_distinct=True,
        ),
    )


class Traspaso(Base):
    __tablename__ = "traspaso"

    id_traspaso: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_sucursal_origen: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    id_sucursal_destino: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String, nullable=False, default="en_transito")
    instante_despacho: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    instante_recepcion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("id_sucursal_origen <> id_sucursal_destino", name="ck_traspaso_distinto"),
        CheckConstraint("estado IN ('en_transito','recibido')", name="ck_traspaso_estado"),
    )


# --------------------------------------------------------------------------
# Venta
# --------------------------------------------------------------------------


class Venta(Base):
    __tablename__ = "venta"

    id_venta: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    clave_idempotencia: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    id_turno: Mapped[int] = mapped_column(ForeignKey("turno.id_turno"), nullable=False)
    referencia_terminal_pago: Mapped[str | None] = mapped_column(String, nullable=True)
    # Medio de pago que eligió el cliente en el POS (enmienda v2.7.2). Aditivo puro: `NULL` en
    # toda venta anterior a la enmienda y en cualquier cobro que no lo declare. Es la CATEGORÍA
    # del pago (efectivo, tarjeta, transferencia…), nunca un dato de instrumento — el PAN/CVV
    # siguen fuera de todo módulo. FK de sólo lectura al catálogo `medio_pago` de 007.
    id_medio_pago: Mapped[int | None] = mapped_column(
        ForeignKey("medio_pago.id_medio_pago"), nullable=True
    )
    instante: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    renglones: Mapped[list["RenglonVenta"]] = relationship(
        back_populates="venta", order_by="RenglonVenta.id_renglon_venta"
    )


class RenglonVenta(Base):
    __tablename__ = "renglon_venta"

    id_renglon_venta: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_venta: Mapped[int] = mapped_column(ForeignKey("venta.id_venta"), nullable=False)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    cantidad_unidades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cantidad_gramos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    precio_aplicado: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    importe: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    venta: Mapped["Venta"] = relationship(back_populates="renglones")

    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN cantidad_unidades IS NOT NULL THEN 1 ELSE 0 END"
            " + CASE WHEN cantidad_gramos IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_renglon_una_cantidad",
        ),
        CheckConstraint(
            "(cantidad_unidades IS NULL OR cantidad_unidades > 0)"
            " AND (cantidad_gramos IS NULL OR cantidad_gramos > 0)",
            name="ck_renglon_cantidad_positiva",
        ),
    )


class AnulacionVenta(Base):
    __tablename__ = "anulacion_venta"

    id_anulacion_venta: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_venta: Mapped[int] = mapped_column(ForeignKey("venta.id_venta"), unique=True, nullable=False)
    id_operador: Mapped[int] = mapped_column(ForeignKey("operador.id_operador"), nullable=False)
    instante: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String, nullable=True)


# --------------------------------------------------------------------------
# Señales del punto de venta
# --------------------------------------------------------------------------


class ConsultaNoAtendida(Base):
    __tablename__ = "consulta_no_atendida"

    id_consulta_no_atendida: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    id_turno: Mapped[int] = mapped_column(ForeignKey("turno.id_turno"), nullable=False)
    instante: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    saldo_en_el_instante: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False)


# --------------------------------------------------------------------------
# Competencia
# --------------------------------------------------------------------------


class CanalCompetencia(Base):
    __tablename__ = "canal_competencia"

    id_canal_competencia: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    nombre_normalizado: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class ObservacionPrecio(Base):
    __tablename__ = "observacion_precio"

    id_observacion_precio: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_canal_competencia: Mapped[int] = mapped_column(
        ForeignKey("canal_competencia.id_canal_competencia"), nullable=False
    )
    presentacion_cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    presentacion_unidad: Mapped[str] = mapped_column(String, nullable=False)
    precio_observado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    fuente: Mapped[str] = mapped_column(String, nullable=False)
    origen_captura: Mapped[str] = mapped_column(String, nullable=False)
    instante_captura: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    id_turno: Mapped[int | None] = mapped_column(ForeignKey("turno.id_turno"), nullable=True)
    comparable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint(
            "presentacion_unidad IN ('unidad','gramo','mililitro')",
            name="ck_observacion_presentacion_unidad",
        ),
        CheckConstraint(
            "origen_captura IN ('manual','archivo')", name="ck_observacion_origen_captura"
        ),
    )


# --------------------------------------------------------------------------
# Verificación de inventario
# --------------------------------------------------------------------------


class ConteoFisico(Base):
    __tablename__ = "conteo_fisico"

    id_conteo_fisico: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="abierto")
    alcance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    instante_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    instante_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("estado IN ('abierto','resuelto')", name="ck_conteo_estado"),
    )


class ConteoRenglon(Base):
    __tablename__ = "conteo_renglon"

    id_conteo_renglon: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_conteo_fisico: Mapped[int] = mapped_column(
        ForeignKey("conteo_fisico.id_conteo_fisico"), nullable=False
    )
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_lote: Mapped[int | None] = mapped_column(ForeignKey("lote.id_lote"), nullable=True)
    cantidad_contada: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False)
    cantidad_esperada: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False)
    diferencia: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False)


# --------------------------------------------------------------------------
# Reconciliación offline
# --------------------------------------------------------------------------


class OperacionPendiente(Base):
    __tablename__ = "operacion_pendiente"

    id_operacion_pendiente: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tipo_operacion: Mapped[str] = mapped_column(String, nullable=False)
    carga: Mapped[dict] = mapped_column(JSONB, nullable=False)
    recurso_afectado: Mapped[str] = mapped_column(String, nullable=False)
    marca_tiempo_origen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    instante_recepcion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estado: Mapped[str] = mapped_column(
        String, nullable=False, default="pendiente_de_sincronizar"
    )
    id_operacion_prevaleciente: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("operacion_pendiente.id_operacion_pendiente"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "tipo_operacion IN ('venta','consulta_no_atendida','anulacion_venta',"
            "'recepcion_traspaso','resolucion_conteo')",
            name="ck_operacion_pendiente_tipo",
        ),
        CheckConstraint(
            "estado IN ('pendiente_de_sincronizar','sincronizada','conflicto_resuelto')",
            name="ck_operacion_pendiente_estado",
        ),
    )


# --------------------------------------------------------------------------
# Clientes y fidelización (002-clientes-fidelizacion, data-model.md)
# --------------------------------------------------------------------------


class Cliente(Base):
    __tablename__ = "cliente"

    id_cliente: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    contacto: Mapped[str | None] = mapped_column(String, nullable=True)
    # Cédula (10 díg.) o RUC de persona natural (13). Opcional (FR-003/FR-017): sólo sirve para
    # no duplicar al mismo cliente entre visitas. Índice único parcial en 0009 (WHERE NOT NULL
    # AND anonimizado = false); se vacía a NULL al anonimizar, igual que `contacto`.
    identificador: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha_alta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    anonimizado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    instante_anonimizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Visita(Base):
    """`monto_total` y `margen_relativo` son snapshots congelados al crear la visita, no se
    recalculan si `venta` o el costo del lote cambian después (FR-005, research.md #2 de 002).
    `margen_relativo` es un RATIO sobre el precio de venta, nunca un monto.
    """

    __tablename__ = "visita"

    id_visita: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_cliente: Mapped[int] = mapped_column(ForeignKey("cliente.id_cliente"), nullable=False)
    id_venta: Mapped[int] = mapped_column(ForeignKey("venta.id_venta"), unique=True, nullable=False)
    instante: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    margen_relativo: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)


class IntervaloCompra(Base):
    """Una fila por cliente, actualizada en el sitio con cada nueva visita (research.md #3 de
    002: mediana de los intervalos entre visitas consecutivas, mínimo 3 visitas).
    """

    __tablename__ = "intervalo_compra"

    id_cliente: Mapped[int] = mapped_column(
        ForeignKey("cliente.id_cliente"), primary_key=True
    )
    intervalo_esperado_dias: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    visitas_consideradas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="datos_insuficientes")
    instante_calculo: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "estado IN ('datos_insuficientes','calculado')", name="ck_intervalo_compra_estado"
        ),
    )


class SenalFuga(Base):
    """Máquina de estados de data-model.md: activa (supera 1x el intervalo esperado) →
    confirmada (supera 5x, o 12 meses, el mayor — FR-014) → resuelta (nueva visita). A lo sumo
    una fila abierta (activa/confirmada) por cliente a la vez — índice único parcial en la
    migración 0002, no expresable como CheckConstraint de SQLAlchemy.
    """

    __tablename__ = "senal_fuga"

    id_senal_fuga: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_cliente: Mapped[int] = mapped_column(ForeignKey("cliente.id_cliente"), nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False)
    instante_deteccion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    instante_confirmacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    instante_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    instante_purga_programada: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('activa','confirmada','resuelta')", name="ck_senal_fuga_estado"
        ),
    )


# --------------------------------------------------------------------------
# Precios y márgenes (003-precios-margenes, data-model.md)
# --------------------------------------------------------------------------


class RolProducto(Base):
    """Tabla propia de 003, no columna de `producto`: alterar el esquema de `producto`
    (propiedad de 001) desde 003 está prohibido por la constitución (research.md #3 de 003).
    Ausencia de fila para un `id_producto` = "sin clasificar" (FR-007).
    """

    __tablename__ = "rol_producto"

    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), primary_key=True)
    rol: Mapped[str] = mapped_column(String, nullable=False)
    instante_asignacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "rol IN ('gancho_trafico','generador_margen')", name="ck_rol_producto_rol"
        ),
    )


class MargenCalculado(Base):
    """Se recalcula y sobrescribe (upsert) en cada lectura, nunca por disparador ni tarea de
    fondo (research.md #4 de 003). `costo_vigente`/`margen` son `NULL` cuando el producto no
    tiene existencia con lote (FR-003), no cero. `confiable = False` cuando el costo vigente es
    cero o negativo (FR-004).
    """

    __tablename__ = "margen_calculado"

    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), primary_key=True)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), primary_key=True)
    costo_vigente: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    precio_vigente: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    margen: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    confiable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    instante_calculo: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SugerenciaPrecio(Base):
    """Append-only (Principio IV): cada sugerencia generada es una fila nueva. `margen_usado` y
    `rol_usado` son snapshots del instante de generación, no referencias mutables a
    `margen_calculado`/`rol_producto` (que sí cambian con cada lectura/reclasificación) — así la
    sugerencia sigue siendo explicable después, aunque el margen o el rol actuales ya sean otros
    (data-model.md, FR-014).
    """

    __tablename__ = "sugerencia_precio"

    id_sugerencia_precio: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    precio_sugerido: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    margen_usado: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    rol_usado: Mapped[str | None] = mapped_column(String, nullable=True)
    id_observacion_precio_usada: Mapped[int | None] = mapped_column(
        ForeignKey("observacion_precio.id_observacion_precio"), nullable=True
    )
    instante_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aplicada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    instante_aplicacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "rol_usado IS NULL OR rol_usado IN ('gancho_trafico','generador_margen')",
            name="ck_sugerencia_precio_rol_usado",
        ),
    )


class SugerenciaColocacion(Base):
    """Append-only, mismo principio que `SugerenciaPrecio`. Referencia una `zona_exhibicion` ya
    catalogada por 001; nunca crea zonas nuevas (FR-016 de 003).
    """

    __tablename__ = "sugerencia_colocacion"

    id_sugerencia_colocacion: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    id_zona_exhibicion: Mapped[int] = mapped_column(
        ForeignKey("zona_exhibicion.id_zona_exhibicion"), nullable=False
    )
    margen_usado: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    rol_usado: Mapped[str | None] = mapped_column(String, nullable=True)
    instante_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aplicada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    instante_aplicacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "rol_usado IS NULL OR rol_usado IN ('gancho_trafico','generador_margen')",
            name="ck_sugerencia_colocacion_rol_usado",
        ),
    )


# --------------------------------------------------------------------------
# Pronóstico de demanda (004-pronostico-demanda, data-model.md, constitución v2.2.4)
# --------------------------------------------------------------------------


class DemandaObservada(Base):
    """Serie histórica de demanda tal como se registró, por producto, sucursal y día local de la
    sucursal. Registro de hechos: no se modifica retroactivamente (FR-004). Se materializa por
    upsert sobre la ventana de días pedida al leer (recompute-on-read, research.md #3), nunca por
    disparador ni tarea de fondo. `demanda_latente_verdadera` se puebla SOLO en filas sintéticas
    de períodos de quiebre (User Story 2, FR-013); es `NULL` en todo dato real.
    """

    __tablename__ = "demanda_observada"

    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), primary_key=True)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), primary_key=True)
    periodo: Mapped[date] = mapped_column(Date, primary_key=True)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False)
    dias_en_quiebre: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=Decimal(0)
    )
    precio_vigente_periodo: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    con_promocion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    es_sintetico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    demanda_latente_verdadera: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    # Conteo sintético de consultas no atendidas del período, contrapartida del
    # `consulta_no_atendida.saldo_en_el_instante` de 001. Solo se puebla en filas sintéticas de
    # períodos de quiebre que declaran ese escenario (FR-016): deja los datos listos para que la
    # rama de evidencia real (FR-007 / T014, bloqueada por 001) se pueda validar cuando exista.
    # NULL en todo dato real y en períodos sintéticos sin consultas declaradas.
    consultas_no_atendidas_sinteticas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    instante_materializacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DemandaCorregida(Base):
    """Serie derivada de `demanda_observada` tras aplicar, en orden fijo (research.md #3), las
    correcciones por quiebre (User Story 1), precio (User Story 4), promoción (User Story 5) y la
    señal de sustitución (User Story 6). `valor_observado` es un snapshot de partida, no una FK,
    para que la serie corregida sea explicable aunque la observada se recompute (FR-010).

    Con `censura_total = True` (FR-012), `valor` queda en 0 SOLO como marcador no expuesto: el
    servicio lo devuelve como `null` con estado "no_estimable_censura_total", nunca ese 0.
    """

    __tablename__ = "demanda_corregida"

    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), primary_key=True)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), primary_key=True)
    periodo: Mapped[date] = mapped_column(Date, primary_key=True)
    valor_observado: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    correccion_quiebre: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal(0)
    )
    respaldo_quiebre: Mapped[str] = mapped_column(String, nullable=False, default="no_aplica")
    ajuste_cruzado_sustituto: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal(0)
    )
    correccion_precio: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal(0)
    )
    elasticidad_usada: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    excluido_por_promocion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    censura_total: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    es_sintetico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    instante_materializacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "respaldo_quiebre IN ('no_aplica','metodo_base','consulta_no_atendida')",
            name="ck_demanda_corregida_respaldo_quiebre",
        ),
    )


class Pronostico(Base):
    """Append-only (Principio IV): cada generación es una fila nueva con sus factores, su período
    de datos y el valor de la línea base determinista (FR-021). Se deriva de `demanda_corregida`,
    nunca de `demanda_observada` cruda (FR-018). Un producto sin histórico suficiente no recibe
    números: `vigente = False`, `serie_pronosticada` vacía y `motivo_no_vigente` (FR-023).
    """

    __tablename__ = "pronostico"

    id_pronostico: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_sucursal: Mapped[int] = mapped_column(ForeignKey("sucursal.id_sucursal"), nullable=False)
    horizonte: Mapped[str] = mapped_column(String, nullable=False)
    dias_horizonte: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    serie_pronosticada: Mapped[list] = mapped_column(JSONB, nullable=False)
    nivel_suavizado: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    alfa_usado: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    multiplicadores_tramo: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    periodo_datos_desde: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_datos_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    valor_linea_base: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    error_retrospectivo: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    error_linea_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    vigente: Mapped[bool] = mapped_column(Boolean, nullable=False)
    motivo_no_vigente: Mapped[str | None] = mapped_column(String, nullable=True)
    es_sintetico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    instante_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("horizonte IN ('corto','medio')", name="ck_pronostico_horizonte"),
    )


class SustitucionProducto(Base):
    """Relación declarada MANUALMENTE entre un producto y otro que puede sustituirlo (FR-032). No
    se infiere de correlación de ventas. Tabla propia de 004, no atributo de `producto` (001) —
    mismo patrón que `rol_producto` de 003. La dirección importa: `id_producto` es el que, al
    quedar en quiebre, empuja demanda hacia `id_producto_sustituto` (FR-033, FR-009 b). Una
    relación mutua son dos filas; una circular está permitida.
    """

    __tablename__ = "sustitucion_producto"

    id_sustitucion_producto: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"), nullable=False)
    id_producto_sustituto: Mapped[int] = mapped_column(
        ForeignKey("producto.id_producto"), nullable=False
    )
    instante_declaracion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "id_producto <> id_producto_sustituto", name="ck_sustitucion_producto_distinto"
        ),
        UniqueConstraint(
            "id_producto", "id_producto_sustituto", name="uq_sustitucion_producto_dirigida"
        ),
    )


# Promociones inteligentes (005-promociones-inteligentes, data-model.md, constitución v2.2.5)
# --------------------------------------------------------------------------


class Campania(Base):
    """Paraguas de una corrida de promoción de UN SOLO mecanismo (Lectura Crítica n.º 6). Agrupa
    los cupones de un rango, o las ofertas de recompra de una detección, o el experimento de una
    reactivación. `id_sucursal = NULL` = toda la cadena. Sin recompute: registro de una decisión.
    Sin ruta de lectura propia en el contrato (Assumption de spec.md): se alcanza por el
    `id_campania` de sus mecanismos hijos.
    """

    __tablename__ = "campania"

    id_campania: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    id_sucursal: Mapped[int | None] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    ventana_desde: Mapped[date] = mapped_column(Date, nullable=False)
    ventana_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    instante_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('fecha_fija','recompra','reactivacion')", name="ck_campania_tipo"
        ),
        CheckConstraint("ventana_hasta >= ventana_desde", name="ck_campania_ventana"),
    )


class Cupon(Base):
    """Mecanismo 1: cupón por fecha fija (cumpleaños). Regla directa —fecha objetivo dentro de la
    ventana -> cupón—, sin inferencia, sin grupo de control, sin medición (FR-001, FR-006).
    `fecha_objetivo` lo trae la consulta de cumpleañeros de 002; `005` nunca lee
    `cliente.fecha_nacimiento` (FR-002). Idempotencia por `UNIQUE (id_cliente, fecha_objetivo)`
    (FR-007). El estado pasa a 'redimido' al registrarse su redención (US1), a 'vencido' al
    superar la fecha actual `valido_hasta` sin redención.
    """

    __tablename__ = "cupon"

    id_cupon: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_campania: Mapped[int] = mapped_column(
        ForeignKey("campania.id_campania"), nullable=False
    )
    id_cliente: Mapped[int] = mapped_column(
        ForeignKey("cliente.id_cliente"), nullable=False
    )
    motivo: Mapped[str] = mapped_column(
        String, nullable=False, default="fecha_fija_cumpleanos"
    )
    fecha_objetivo: Mapped[date] = mapped_column(Date, nullable=False)
    valido_desde: Mapped[date] = mapped_column(Date, nullable=False)
    valido_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    porcentaje_descuento: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="generado")
    instante_generacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint("motivo IN ('fecha_fija_cumpleanos')", name="ck_cupon_motivo"),
        CheckConstraint(
            "estado IN ('generado','redimido','vencido','anulado')", name="ck_cupon_estado"
        ),
        UniqueConstraint(
            "id_cliente", "fecha_objetivo", name="uq_cupon_cliente_fecha_objetivo"
        ),
    )


class OfertaRecompra(Base):
    """Mecanismo 2: empuje por patrón de recompra con RESERVA DE PRECIO (FR-010).
    `precio_garantizado` es lo único que la reserva garantiza; NO aparta stock ni escribe contra
    `existencia` / `movimiento_inventario` de 001 (FR-011). `justificacion` (JSONB) guarda qué
    compras del propio cliente sustentan la elección del producto (FR-009, explicable). A lo sumo
    una oferta con `desenlace = 'pendiente'` por (id_cliente, id_producto) — índice único parcial
    (FR-014).
    """

    __tablename__ = "oferta_recompra"

    id_oferta_recompra: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_campania: Mapped[int] = mapped_column(
        ForeignKey("campania.id_campania"), nullable=False
    )
    id_cliente: Mapped[int] = mapped_column(
        ForeignKey("cliente.id_cliente"), nullable=False
    )
    id_producto: Mapped[int] = mapped_column(
        ForeignKey("producto.id_producto"), nullable=False
    )
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    intervalo_esperado_dias_disparo: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False
    )
    justificacion: Mapped[dict] = mapped_column(JSONB, nullable=False)
    precio_garantizado: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    reserva_desde: Mapped[date] = mapped_column(Date, nullable=False)
    reserva_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    estado_reserva: Mapped[str] = mapped_column(
        String, nullable=False, default="vigente"
    )
    desenlace: Mapped[str] = mapped_column(String, nullable=False, default="pendiente")
    instante_generacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "estado_reserva IN ('vigente','vencida')",
            name="ck_oferta_recompra_estado_reserva",
        ),
        CheckConstraint(
            "desenlace IN ('pendiente','comprado','no_comprado','reserva_vencida')",
            name="ck_oferta_recompra_desenlace",
        ),
    )


class ExperimentoReactivacion(Base):
    """Mecanismo 3: la corrida experimental de reactivación (FR-015 a FR-025). Guarda toda su
    parametrización (semilla, ventana, tamaño mínimo de muestra) y su resultado (tasas por grupo,
    estadístico z, valor p, veredicto). Append + estado (`veredicto`), nunca se recomputa.
    `veredicto = 'muestra_insuficiente'` al crear si `n_elegibles < 2 * tamano_minimo_muestra`;
    `efectivo` al cerrar si `incrementalidad > 0 AND valor_p < alfa`; `no_efectivo` en cualquier
    otro cierre (FR-021, Edge Case de incrementalidad negativa).
    `motivo_muestra_insuficiente` NO es columna: se calcula al serializar la respuesta.
    """

    __tablename__ = "experimento_reactivacion"

    id_experimento_reactivacion: Mapped[int] = mapped_column(
        BigInteger, primary_key=True
    )
    id_campania: Mapped[int] = mapped_column(
        ForeignKey("campania.id_campania"), nullable=False
    )
    id_sucursal: Mapped[int | None] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=True
    )
    semilla: Mapped[int] = mapped_column(BigInteger, nullable=False)
    algoritmo: Mapped[str] = mapped_column(String, nullable=False)
    proporcion_tratamiento: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False
    )
    ventana_medicion_dias: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    porcentaje_descuento: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    tasa_retorno_base_esperada: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False
    )
    mde_puntos_porcentuales: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    alfa: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    poder: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    tamano_minimo_muestra: Mapped[int] = mapped_column(Integer, nullable=False)
    n_elegibles: Mapped[int] = mapped_column(Integer, nullable=False)
    n_tratamiento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_control: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retorno_tratamiento: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    retorno_control: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    incrementalidad: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    estadistico_z: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    valor_p: Mapped[Decimal | None] = mapped_column(Numeric(7, 6), nullable=True)
    veredicto: Mapped[str] = mapped_column(String, nullable=False, default="en_curso")
    instante_asignacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    instante_cierre: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "veredicto IN ('en_curso','efectivo','no_efectivo','muestra_insuficiente')",
            name="ck_experimento_reactivacion_veredicto",
        ),
    )


class AsignacionExperimento(Base):
    """Una fila por cliente inactivo elegible, con su grupo y su desenlace de retorno. Es la
    materialización del GRUPO DE CONTROL OBLIGATORIO (Lectura Crítica n.º 6, FR-023): `grupo` no
    admite un tercer valor "sin grupo". `id_senal_fuga` es la `senal_fuga` de 002 que hizo
    elegible al cliente — referencia de auditoría; `005` nunca modifica `senal_fuga` (FR-028).
    `retorno` se fija al cerrar el experimento mirando `visita` de 002 (research.md #11), no por
    la redención.
    """

    __tablename__ = "asignacion_experimento"

    id_asignacion_experimento: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_experimento_reactivacion: Mapped[int] = mapped_column(
        ForeignKey("experimento_reactivacion.id_experimento_reactivacion"),
        nullable=False,
    )
    id_cliente: Mapped[int] = mapped_column(
        ForeignKey("cliente.id_cliente"), nullable=False
    )
    id_senal_fuga: Mapped[int] = mapped_column(BigInteger, nullable=False)
    grupo: Mapped[str] = mapped_column(String, nullable=False)
    retorno: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    id_venta_retorno: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    instante_retorno: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "grupo IN ('tratamiento','control')", name="ck_asignacion_experimento_grupo"
        ),
        UniqueConstraint(
            "id_experimento_reactivacion",
            "id_cliente",
            name="uq_asignacion_experimento_cliente",
        ),
    )


class RedencionPromocion(Base):
    """El hecho de que un `cupon`, una `oferta_recompra` o una `asignacion_experimento`
    (tratamiento) se usó en una VENTA de 001. Registro inmutable. Referencia la venta por FK de
    sólo lectura (mismo patrón que `visita.id_venta` de 002), sin copiar sus datos.
    `id_sucursal`/`periodo` se denormalizan de `venta -> turno -> sucursal` —valores inmutables—
    para la consulta de "marca de promoción activa" que 004 consume (research.md #4).
    Idempotencia y "una redención por origen": índices únicos parciales sobre cada `id_*`.
    Un solo endpoint y un solo servicio (`registrar_redencion`), construidos en US1 y reutilizados
    por US2/US3/US4 — no hay una tabla ni una ruta de redención por mecanismo.
    """

    __tablename__ = "redencion_promocion"

    id_redencion_promocion: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo_origen: Mapped[str] = mapped_column(String, nullable=False)
    id_cupon: Mapped[int | None] = mapped_column(
        ForeignKey("cupon.id_cupon"), nullable=True
    )
    id_oferta_recompra: Mapped[int | None] = mapped_column(
        ForeignKey("oferta_recompra.id_oferta_recompra"), nullable=True
    )
    id_asignacion_experimento: Mapped[int | None] = mapped_column(
        ForeignKey("asignacion_experimento.id_asignacion_experimento"), nullable=True
    )
    id_venta: Mapped[int] = mapped_column(ForeignKey("venta.id_venta"), nullable=False)
    id_producto: Mapped[int | None] = mapped_column(
        ForeignKey("producto.id_producto"), nullable=True
    )
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    periodo: Mapped[date] = mapped_column(Date, nullable=False)
    descuento_aplicado: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    instante_redencion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "tipo_origen IN ('cupon','oferta_recompra','reactivacion')",
            name="ck_redencion_promocion_tipo_origen",
        ),
        CheckConstraint(
            "( (id_cupon IS NOT NULL)::int + (id_oferta_recompra IS NOT NULL)::int"
            " + (id_asignacion_experimento IS NOT NULL)::int ) = 1"
            " AND (tipo_origen = 'cupon') = (id_cupon IS NOT NULL)"
            " AND (tipo_origen = 'oferta_recompra') = (id_oferta_recompra IS NOT NULL)"
            " AND (tipo_origen = 'reactivacion') = (id_asignacion_experimento IS NOT NULL)",
            name="ck_redencion_promocion_origen_unico",
        ),
    )


# --------------------------------------------------------------------------
# 006-caja-mermas-fraude — arqueo, merma, anomalia_caja (data-model.md,
# constitución v2.2.5). Tres fenómenos con lógica distinta (FR-037): NO una
# entidad genérica de "descuadre". Append + máquina de estados, nunca se
# recomputan al leer (research.md #13). Los indicadores por operador son
# cálculo derivado sobre 001, NO tabla (research.md #2, #7).
# --------------------------------------------------------------------------


class Arqueo(Base):
    """Fenómeno 2: cuadre de efectivo al cierre de un `turno` de 001 (FR-001 a FR-008).

    `monto_esperado` = SUM(venta.total) del turno, **congelado** al cerrar el arqueo: anular una
    venta después no lo cambia (research.md #4). `id_operador`/`id_sucursal`/`dia_local` se
    denormalizan de `turno` (inmutables). Idempotencia por `UNIQUE (id_turno)` (FR-005). Una
    diferencia sin `motivo_conocido` fuera de la tolerancia genera una `AnomaliaCaja` de origen
    efectivo. El arqueo, por sí solo, NUNCA es señal del fraude de sub-registro (FR-008).
    """

    __tablename__ = "arqueo"

    id_arqueo: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_turno: Mapped[int] = mapped_column(
        ForeignKey("turno.id_turno"), unique=True, nullable=False
    )
    id_operador: Mapped[int] = mapped_column(
        ForeignKey("operador.id_operador"), nullable=False
    )
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    dia_local: Mapped[date] = mapped_column(Date, nullable=False)
    monto_esperado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monto_contado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    diferencia: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    motivo_conocido: Mapped[str | None] = mapped_column(String, nullable=True)
    ajustes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    instante_cierre_arqueo: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    marca_tiempo_origen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")


class Merma(Base):
    """Fenómeno 1: pérdida de producto SIN venta asociada, clasificada por causa (FR-009 a FR-017).

    `id_conteo_renglon` NULL = merma declarada fuera de conteo (FR-012); no nula = clasifica la
    `diferencia` que 001 ya expone (rama **bloqueada** hasta 001 User Story 5 — research.md #10).
    `cantidad_faltante` tiene la escala de `conteo_renglon.diferencia` de 001 (entero, gramos para
    granel). `valoracion` = cantidad × costo del lote FEFO; NULL = "no calculable", NUNCA 0.00
    (FR-010). Atribuida a sucursal y período entre conteos, **nunca a un operador** (FR-011).
    """

    __tablename__ = "merma"

    id_merma: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_conteo_renglon: Mapped[int | None] = mapped_column(
        ForeignKey("conteo_renglon.id_conteo_renglon"), nullable=True
    )
    id_producto: Mapped[int] = mapped_column(
        ForeignKey("producto.id_producto"), nullable=False
    )
    id_lote: Mapped[int | None] = mapped_column(ForeignKey("lote.id_lote"), nullable=True)
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    cantidad_faltante: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False)
    causa: Mapped[str] = mapped_column(String, nullable=False)
    valoracion: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    periodo_desde: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(
        String, nullable=False, default="pendiente_clasificar"
    )
    conciliar_con_conteo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    id_operador_registro: Mapped[int] = mapped_column(
        ForeignKey("operador.id_operador"), nullable=False
    )
    instante_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    nota: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "causa IN ('vencimiento','dano','robo_externo','error_conteo','merma_granel',"
            "'pendiente_clasificar')",
            name="ck_merma_causa",
        ),
        CheckConstraint(
            "estado IN ('pendiente_clasificar','clasificada')", name="ck_merma_estado"
        ),
        CheckConstraint("cantidad_faltante > 0", name="ck_merma_cantidad_positiva"),
        CheckConstraint("periodo_hasta >= periodo_desde", name="ck_merma_periodo"),
        CheckConstraint(
            "valoracion IS NULL OR valoracion >= 0", name="ck_merma_valoracion_no_negativa"
        ),
    )


class AnomaliaCaja(Base):
    """Fenómeno 3 + residuo: una diferencia (de efectivo o de inventario) que ninguna causa
    conocida explica (FR-018 a FR-031). UNA entidad con campo `origen` — no un cajón que fusione
    los tres fenómenos: ambos orígenes comparten la misma máquina de estados y el mismo flujo de
    revisión humana.

    `sin_explicacion -> resuelta`, **sólo** por acción de una persona (FR-030). NO hay transición
    automática por el paso del tiempo (FR-029). `indicador_snapshot` (JSONB) congela los
    indicadores por operador cuando se genera una anomalía de inventario (research.md #2, #6).
    `historial` (JSONB) guarda cada cambio de estado. `resolucion` es texto libre, no un ENUM
    cerrado (research.md #18).
    """

    __tablename__ = "anomalia_caja"

    id_anomalia_caja: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    origen: Mapped[str] = mapped_column(String, nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="sin_explicacion")
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    id_arqueo: Mapped[int | None] = mapped_column(ForeignKey("arqueo.id_arqueo"), nullable=True)
    id_turno: Mapped[int | None] = mapped_column(ForeignKey("turno.id_turno"), nullable=True)
    id_operador: Mapped[int | None] = mapped_column(
        ForeignKey("operador.id_operador"), nullable=True
    )
    id_producto: Mapped[int | None] = mapped_column(
        ForeignKey("producto.id_producto"), nullable=True
    )
    id_conteo_fisico: Mapped[int | None] = mapped_column(
        ForeignKey("conteo_fisico.id_conteo_fisico"), nullable=True
    )
    monto: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    magnitud: Mapped[Decimal | None] = mapped_column(Numeric(14, 0), nullable=True)
    valor_estimado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    periodo_desde: Mapped[date | None] = mapped_column(Date, nullable=True)
    periodo_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    dia_local: Mapped[date] = mapped_column(Date, nullable=False)
    indicador_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    historial: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    resolucion: Mapped[str | None] = mapped_column(String, nullable=True)
    id_operador_resolucion: Mapped[int | None] = mapped_column(
        ForeignKey("operador.id_operador"), nullable=True
    )
    instante_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    instante_deteccion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    __table_args__ = (
        CheckConstraint("origen IN ('efectivo','inventario')", name="ck_anomalia_caja_origen"),
        CheckConstraint(
            "estado IN ('sin_explicacion','resuelta')", name="ck_anomalia_caja_estado"
        ),
        CheckConstraint(
            "(id_operador_resolucion IS NOT NULL) = (estado = 'resuelta')"
            " AND (instante_resolucion IS NOT NULL) = (estado = 'resuelta')",
            name="ck_anomalia_caja_resolucion_coherente",
        ),
    )


# --------------------------------------------------------------------------
# 007-pagos-seguridad — medio_pago, terminal_pago, cobertura_pago,
# bitacora_auditoria, token_pago (data-model.md, constitución v2.2.6).
# `token_pago` añadida por la enmienda v2.2.6 (research.md #1): registro
# autoritativo de un cobro con tarjeta tokenizado, UNIQUE por cobro e
# idempotencia. SIN ningún campo de PAN/CVV/banda; `ultimos_digitos CHAR(4)`
# con CHECK de 4 dígitos (barrera de esquema, FR-018). 007 SÓLO LEE de 001.
# Los indicadores de firmware y la cuota de intención no atendida NO son
# entidad: cálculo derivado (research.md #3, #5).
# --------------------------------------------------------------------------


class MedioPago(Base):
    """Catálogo global de medios de pago (FR-001). Una fila por medio, extensible sin migración."""

    __tablename__ = "medio_pago"

    id_medio_pago: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    requiere_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    admite_tokenizacion: Mapped[bool] = mapped_column(Boolean, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TerminalPago(Base):
    """Terminal de pago (datáfono) física (FR-008 a FR-015). NUEVA en este módulo: 001 sólo guarda
    una `referencia_terminal_pago` opaca. Los indicadores "desactualizada"/"expuesta a clonación"
    NO son columnas: cálculo derivado al leer (research.md #3). El sistema NUNCA marca `activa =
    False` por una señal de firmware (FR-012).
    """

    __tablename__ = "terminal_pago"

    id_terminal_pago: Mapped[int] = mapped_column(Integer, primary_key=True)
    identificador: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    modelo: Mapped[str] = mapped_column(String, nullable=False)
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    version_firmware: Mapped[str] = mapped_column(String, nullable=False)
    fecha_ultima_actualizacion_firmware: Mapped[date | None] = mapped_column(Date, nullable=True)
    historial_ubicacion: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    historial_firmware: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    id_operador_registro: Mapped[int] = mapped_column(
        ForeignKey("operador.id_operador"), nullable=False
    )
    instante_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint(
            "version_firmware ~ '^[0-9]+\\.[0-9]+\\.[0-9]+$'", name="ck_terminal_pago_version"
        ),
    )


class CoberturaPago(Base):
    """Aceptación de un `medio_pago` en una `sucursal`, con vigencia histórica por tramos
    `[fecha_desde, fecha_hasta]` sin solape (FR-002). La cuota de intención de compra no atendida
    se DERIVA de `bitacora_auditoria` (research.md #5), no se persiste aquí.
    """

    __tablename__ = "cobertura_pago"

    id_cobertura_pago: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_medio_pago: Mapped[int] = mapped_column(
        ForeignKey("medio_pago.id_medio_pago"), nullable=False
    )
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    fecha_desde: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    id_operador: Mapped[int] = mapped_column(
        ForeignKey("operador.id_operador"), nullable=False
    )
    instante_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "fecha_hasta IS NULL OR fecha_hasta >= fecha_desde", name="ck_cobertura_pago_periodo"
        ),
    )


class BitacoraAuditoria(Base):
    """Rastro de SOLO ANEXADO de los hechos de pago (Principio IV, FR-023 a FR-028). Un TRIGGER
    `BEFORE UPDATE OR DELETE` (migración 0007) rechaza cualquier modificación o borrado a nivel de
    motor (FR-025). NUNCA contiene PAN, CVV ni datos de banda/chip (FR-026); `resultado` se redacta
    desde plantillas por `tipo_evento`, nunca desde texto libre del cliente (research.md #6).
    """

    __tablename__ = "bitacora_auditoria"

    id_bitacora_auditoria: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo_evento: Mapped[str] = mapped_column(String, nullable=False)
    instante: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dia_local: Mapped[date] = mapped_column(Date, nullable=False)
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    id_terminal_pago: Mapped[int | None] = mapped_column(
        ForeignKey("terminal_pago.id_terminal_pago"), nullable=True
    )
    id_medio_pago: Mapped[int | None] = mapped_column(
        ForeignKey("medio_pago.id_medio_pago"), nullable=True
    )
    iniciador_tipo: Mapped[str] = mapped_column(String, nullable=False)
    id_operador: Mapped[int | None] = mapped_column(
        ForeignKey("operador.id_operador"), nullable=True
    )
    proceso: Mapped[str | None] = mapped_column(String, nullable=True)
    resultado: Mapped[str] = mapped_column(String, nullable=False)
    referencia_recurso_tipo: Mapped[str | None] = mapped_column(String, nullable=True)
    referencia_recurso_id: Mapped[str | None] = mapped_column(String, nullable=True)
    clave_idempotencia: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "tipo_evento IN ('token_emitido','token_idempotencia_divergente','token_purgado',"
            "'pan_rechazado','firmware_actualizado','firmware_desactualizado_detectado',"
            "'terminal_expuesta_detectada','terminal_registrada','terminal_movida','medio_pago_alta',"
            "'medio_pago_baja','cobertura_declarada','intencion_no_atendida','config_firmware_cambiada')",
            name="ck_bitacora_auditoria_tipo_evento",
        ),
        CheckConstraint(
            "iniciador_tipo IN ('operador','proceso')", name="ck_bitacora_auditoria_iniciador"
        ),
        CheckConstraint(
            "referencia_recurso_tipo IS NULL OR referencia_recurso_tipo IN "
            "('token_pago','venta','terminal_pago','medio_pago','cobertura_pago')",
            name="ck_bitacora_auditoria_referencia",
        ),
    )


class TokenPago(Base):
    """Registro AUTORITATIVO de un cobro con tarjeta tokenizado (research.md #1, #4). Guarda
    ÚNICAMENTE el identificador sustituto opaco y el metadato mínimo que la constitución permite
    conservar ("Datos de pago": identificadores y últimos dígitos). SIN ningún campo de PAN, CVV o
    banda/chip. `ultimos_digitos` es `CHAR(4)` con CHECK de 4 dígitos: barrera de esquema (FR-018).

    Idempotencia (research.md #15): PRIMARIA por `UNIQUE (id_venta)` (un token por cobro, como
    `arqueo` usa `UNIQUE (id_turno)`); `clave_idempotencia UNIQUE` es la segunda barrera, la genera
    el cliente. FK `id_venta` de SOLO LECTURA: 007 consulta `venta` de 001, nunca la escribe.
    """

    __tablename__ = "token_pago"

    id_token_pago: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    id_venta: Mapped[int] = mapped_column(
        ForeignKey("venta.id_venta"), unique=True, nullable=False
    )
    clave_idempotencia: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    ultimos_digitos: Mapped[str] = mapped_column(String(4), nullable=False)
    marca: Mapped[str] = mapped_column(String, nullable=False)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    id_terminal_pago: Mapped[int] = mapped_column(
        ForeignKey("terminal_pago.id_terminal_pago"), nullable=False
    )
    id_sucursal: Mapped[int] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=False
    )
    instante: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dia_local: Mapped[date] = mapped_column(Date, nullable=False)
    marca_tiempo_origen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "ultimos_digitos ~ '^[0-9]{4}$'", name="ck_token_pago_ultimos_digitos"
        ),
        CheckConstraint(
            "marca IN ('visa','mastercard','amex','diners','otra')", name="ck_token_pago_marca"
        ),
        CheckConstraint(
            "tipo IN ('debito','credito','desconocido')", name="ck_token_pago_tipo"
        ),
    )


# --------------------------------------------------------------------------
# 008-reportes-inteligencia — entidades DERIVADAS y regenerables (constitución v2.6.0).
# Ninguna es fuente de verdad: se reconstruyen ejecutando los cálculos de 008 sobre 001–006.
# --------------------------------------------------------------------------


class AgregadoReporte(Base):
    """Caché del resultado ya calculado de una vista (comparativo / tendencia / tablero) para un
    ámbito y período. Se puebla a demanda; el encargado la invalida con "Actualizar".
    """

    __tablename__ = "agregado_reporte"

    id_agregado_reporte: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    ambito_sucursal: Mapped[int | None] = mapped_column(
        ForeignKey("sucursal.id_sucursal"), nullable=True
    )
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fin: Mapped[date] = mapped_column(Date, nullable=False)
    granularidad: Mapped[str] = mapped_column(String, nullable=False)
    contenido: Mapped[dict] = mapped_column(JSONB, nullable=False)
    instante_calculo: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('comparativo','tendencia','tablero')", name="ck_agregado_reporte_tipo"
        ),
        CheckConstraint(
            "granularidad IN ('total','semana','mes')", name="ck_agregado_reporte_gran"
        ),
        UniqueConstraint(
            "tipo",
            "ambito_sucursal",
            "periodo_inicio",
            "periodo_fin",
            "granularidad",
            name="uq_agregado_reporte_clave",
        ),
    )


class SegmentoCliente(Base):
    """Definición de un grupo del ÚLTIMO recálculo de clustering (FR-018, FR-022). Se reemplaza
    entera en cada recálculo; sólo se conserva la última corrida.
    """

    __tablename__ = "segmento_cliente"

    id_segmento_cliente: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    corrida: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    etiqueta_grupo: Mapped[str] = mapped_column(String, nullable=False)
    centroide_frecuencia: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    centroide_margen: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    centroide_recencia_dias: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    n_clientes: Mapped[int] = mapped_column(Integer, nullable=False)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    semilla: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("corrida", "etiqueta_grupo", name="uq_segmento_cliente_corrida_grupo"),
    )


class AsignacionSegmento(Base):
    """Relación cliente ↔ grupo del último recálculo. Una fila por cliente (FR-023). 008 NO
    escribe en `cliente`; el detalle de 002 que muestra la etiqueta la lee de aquí.
    """

    __tablename__ = "asignacion_segmento"

    id_cliente: Mapped[int] = mapped_column(
        ForeignKey("cliente.id_cliente", ondelete="CASCADE"), primary_key=True
    )
    corrida: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    etiqueta_grupo: Mapped[str] = mapped_column(String, nullable=False)
    distancia_al_centroide: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["corrida", "etiqueta_grupo"],
            ["segmento_cliente.corrida", "segmento_cliente.etiqueta_grupo"],
            name="fk_asignacion_segmento_grupo",
        ),
    )


# --------------------------------------------------------------------------
# 009-facturacion-electronica — SIMULADA (constitución v2.7.0). Entidad propia de 009, derivada
# de una `venta` confirmada de 001. 009 CONSULTA venta/renglon_venta/cliente sin poseerlos.
# --------------------------------------------------------------------------


class FacturaSimulada(Base):
    """Documento con la FORMA de una factura electrónica ecuatoriana, SIMULADO (sin SRI, sin
    firma, sin XML regulatorio). Todo el contenido es un SNAPSHOT: una factura emitida no cambia
    aunque cambie la venta, el cliente o la configuración (FR-013). Idempotente por `id_venta`
    para `tipo='factura'`.
    """

    __tablename__ = "factura_simulada"

    id_factura_simulada: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_venta: Mapped[int] = mapped_column(ForeignKey("venta.id_venta"), nullable=False)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    id_factura_referida: Mapped[int | None] = mapped_column(
        ForeignKey("factura_simulada.id_factura_simulada"), nullable=True
    )
    establecimiento: Mapped[str] = mapped_column(String, nullable=False)
    punto_emision: Mapped[str] = mapped_column(String, nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    secuencial: Mapped[str] = mapped_column(String, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    emisor: Mapped[dict] = mapped_column(JSONB, nullable=False)
    comprador: Mapped[dict] = mapped_column(JSONB, nullable=False)
    renglones: Mapped[list] = mapped_column(JSONB, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tarifa_iva: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    monto_iva: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    medio_pago: Mapped[str | None] = mapped_column(String, nullable=True)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="emitida")
    instante_generacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint("tipo IN ('factura','nota_credito')", name="ck_factura_simulada_tipo"),
        CheckConstraint("estado IN ('emitida','anulada')", name="ck_factura_simulada_estado"),
        CheckConstraint("numero >= 1", name="ck_factura_simulada_numero"),
        UniqueConstraint(
            "establecimiento", "punto_emision", "tipo", "numero",
            name="uq_factura_simulada_secuencial",
        ),
    )
