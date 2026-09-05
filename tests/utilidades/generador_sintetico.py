"""Generador de series de demanda sintéticas con demanda latente CONOCIDA (T023 de
004-pronostico-demanda, User Story 2).

NO es un archivo de pruebas y NO pertenece al paquete de producción `rasero`: vive en `tests/`
porque su único propósito es alimentar la validación de la descensura (research.md #9). Los datos
que produce no pertenecen al juego de datos "Despensa Los Ríos" y nunca se cargan en un entorno
real (constitución: separación herramienta/datos; FR-017).

La serie es **determinista** (fechas fijas, sin azar): el mismo llamado produce siempre la misma
serie, para que el número del reporte de error sea reproducible y defendible.

Modelo de la demanda "verdadera" de un día: un nivel base plano de lunes a viernes, con un
recargo de fin de semana. Durante un intervalo de quiebre la demanda OBSERVADA es 0 pero la
demanda LATENTE VERDADERA sigue el mismo modelo — ese es el valor contra el que se mide si el
método base de FR-009 acierta.
"""

from datetime import date, timedelta

INICIO = date(2026, 1, 5)  # lunes
DIAS_TOTALES = 56

NIVEL_BASE = 10
RECARGO_SABADO = 5
RECARGO_DOMINGO = 2

# Dos intervalos de quiebre (índices de día, ambos inclusive):
#  - A: 33..38 — incluye sábado y domingo, y TIENE consultas no atendidas sintéticas (camino FR-007).
#  - B: 45..47 — sólo entre semana + un sábado, y NO tiene consultas (camino FR-008 / método base).
_QUIEBRE_A = range(33, 39)
_QUIEBRE_B = range(45, 48)


def _demanda_verdadera(dia: date) -> int:
    diasem = dia.weekday()  # lunes=0 ... domingo=6
    if diasem == 5:
        return NIVEL_BASE + RECARGO_SABADO
    if diasem == 6:
        return NIVEL_BASE + RECARGO_DOMINGO
    return NIVEL_BASE


def generar_serie(id_producto: int, id_sucursal: int) -> dict:
    """Devuelve un cuerpo con la forma `CargaSintetica` de contracts/openapi.yaml, listo para
    `POST /demanda-sintetica`.
    """
    periodos: list[dict] = []
    consultas: list[dict] = []

    for i in range(DIAS_TOTALES):
        dia = INICIO + timedelta(days=i)
        verdadera = _demanda_verdadera(dia)
        en_quiebre = i in _QUIEBRE_A or i in _QUIEBRE_B

        if en_quiebre:
            periodos.append(
                {
                    "periodo": dia.isoformat(),
                    "demanda_observada": "0",
                    "dias_en_quiebre": "1",
                    "demanda_latente_verdadera": str(verdadera),
                }
            )
            if i in _QUIEBRE_A:
                # Escenario de conocimiento perfecto: el conteo de consultas coincide con la
                # demanda latente. Cuando 001 implemente FR-007 / T014, la magnitud por evidencia
                # real debería quedar aún más cerca de la verdad que el método base.
                consultas.append({"periodo": dia.isoformat(), "conteo": verdadera})
        else:
            periodos.append(
                {
                    "periodo": dia.isoformat(),
                    "demanda_observada": str(verdadera),
                    "dias_en_quiebre": "0",
                }
            )

    return {
        "id_producto": id_producto,
        "id_sucursal": id_sucursal,
        "periodos": periodos,
        "consultas_no_atendidas_sinteticas": consultas,
    }
