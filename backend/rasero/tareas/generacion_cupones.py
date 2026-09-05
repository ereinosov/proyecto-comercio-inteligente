"""Tarea programada (005-promociones-inteligentes, T015): genera los cupones por fecha fija de un
rango de fechas. Fuera del camino crítico de cualquier petición HTTP (Principio II) — nunca se
dispara como efecto secundario de un endpoint. Se invoca aparte, por ejemplo desde el
planificador del sistema operativo (cron, Programador de tareas de Windows):

    python -m rasero.tareas.generacion_cupones <desde> <hasta>

`<desde>` y `<hasta>` en formato ISO (`AAAA-MM-DD`). Sin argumentos, usa la ventana de generación
por defecto: de hoy a hoy + ANTELACION_GENERACION_CUPON_DIAS + VALIDEZ_CUPON_DIAS.
"""

import sys
from datetime import date, timedelta

from rasero.config import promociones as cfg
from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.promociones import generar_cupones


def ejecutar(desde: date | None = None, hasta: date | None = None) -> None:
    if desde is None:
        desde = date.today()
    if hasta is None:
        hasta = desde + timedelta(
            days=cfg.ANTELACION_GENERACION_CUPON_DIAS + cfg.VALIDEZ_CUPON_DIAS
        )
    sesion = SesionLocal()
    try:
        resultado = generar_cupones(sesion, desde=desde, hasta=hasta)
        sesion.commit()
        print(
            f"Campaña {resultado['id_campania']}: "
            f"{resultado['cupones_generados']} cupones generados, "
            f"{resultado['cupones_ya_existentes']} ya existían "
            f"(rango {desde.isoformat()} a {hasta.isoformat()})"
        )
    finally:
        sesion.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    d = date.fromisoformat(args[0]) if len(args) >= 1 else None
    h = date.fromisoformat(args[1]) if len(args) >= 2 else None
    ejecutar(d, h)
