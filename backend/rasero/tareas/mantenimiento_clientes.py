"""Tarea programada (T034): `evaluar_fugas_pendientes()` y, después, `anonimizar_clientes_vencidos()`.
Fuera del camino crítico de cualquier petición HTTP (research.md #6 de 002-clientes-fidelizacion,
Principio II) — nunca se dispara como efecto secundario de un endpoint. Se invoca aparte, por
ejemplo desde el planificador del sistema operativo (cron, Programador de tareas de Windows):

    python -m rasero.tareas.mantenimiento_clientes

El orden importa: primero se evalúan y confirman las fugas del día, y solo después se anonimiza
— así una fuga que se confirma justo en esta corrida nunca se anonimiza en la misma pasada (su
`instante_purga_programada` queda siempre en el futuro, a 90 días).
"""

from rasero.persistencia.sesion import SesionLocal
from rasero.servicios.anonimizacion import anonimizar_clientes_vencidos
from rasero.servicios.clientes import evaluar_fugas_pendientes


def ejecutar() -> None:
    sesion = SesionLocal()
    try:
        tocados = evaluar_fugas_pendientes(sesion)
        anonimizados = anonimizar_clientes_vencidos(sesion)
        print(f"Señales de fuga creadas o confirmadas: {tocados}")
        print(f"Clientes anonimizados: {anonimizados}")
    finally:
        sesion.close()


if __name__ == "__main__":
    ejecutar()
