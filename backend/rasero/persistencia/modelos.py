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
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    BigInteger,
    Boolean,
    JSON,
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


class Categoria(Base):
    __tablename__ = "categoria"

    id_categoria: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    dias_umbral_inmovilizado: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Producto(Base):
    __tablename__ = "producto"

    id_producto: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_categoria: Mapped[int | None] = mapped_column(ForeignKey("categoria.id_categoria"))
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    es_granel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    precio_vigente: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    lleva_caducidad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")


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


# --------------------------------------------------------------------------
# Personas y turnos
# --------------------------------------------------------------------------


class Operador(Base):
    __tablename__ = "operador"

    id_operador: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    pin_hash: Mapped[str] = mapped_column(String, nullable=False)
    es_encargado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


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
