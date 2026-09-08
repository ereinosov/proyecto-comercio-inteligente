"""Calibración de 008-reportes-inteligencia. Valores presentacionales y de cálculo, nunca
reglas de negocio de 001–007 (008 las hereda, no las redefine).
"""

# ── Segmentación de clientes (User Story 4) ──────────────────────────────────────────────────
# k del clustering. Se evaluó 3 y 4 (research.md §2): con 4 la base de un minimarket de dos
# tiendas se separa en los grupos que un encargado reconoce —frecuentes de buen margen,
# frecuentes de bajo margen, esporádicos, y dormidos/en fuga— sin fragmentar de más; con 3
# "esporádicos" y "dormidos" se colapsan en un grupo poco accionable. Con menos de K clientes
# clasificables, `dominio/kmeans.agrupar` reduce k a esa cantidad (FR-024). No es parámetro de
# interfaz en esta versión.
K_SEGMENTOS = 4

# Historial mínimo para entrar al clustering: 3 visitas, el mismo mínimo que 002 exige para
# calcular `intervalo_compra` (FR-021). Menos que eso → grupo "sin_clasificar".
MIN_VISITAS_CLASIFICABLE = 3

# Semilla fija del RNG del k-means (FR-019, mismo criterio que el experimento de 005).
SEMILLA_SEGMENTOS = 20260907

# ── Tendencias (User Story 2) ───────────────────────────────────────────────────────────────
PERIODOS_TENDENCIA_DEFECTO = {"semana": 12, "mes": 6}

# ── Tablero de KPIs (User Story 3): umbrales de "atención" ───────────────────────────────────
# Un margen de producto por debajo de esto cuenta como "margen bajo" en la tarjeta de Márgenes
# (mismo valor que el umbral saludable de Precios.tsx en el frontend de 003).
MARGEN_SALUDABLE = 0.15
# Cuota de intención de compra no atendida por encima de esto → atención en la tarjeta de Pagos.
CUOTA_NO_ATENDIDA_ATENCION = 0.10
