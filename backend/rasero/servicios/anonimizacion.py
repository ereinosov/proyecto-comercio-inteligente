"""Anonimización de clientes con fuga confirmada y vencida (FR-015, FR-016 de
002-clientes-fidelizacion). Job de fondo (research.md #6): nunca se invoca desde un endpoint
HTTP, solo desde `tareas/mantenimiento_clientes.py` (T034) o pruebas.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from rasero.persistencia.modelos import Cliente, SenalFuga


def anonimizar_clientes_vencidos(sesion: Session) -> int:
    """Para cada `senal_fuga` `confirmada` cuyo `instante_purga_programada` ya venció, vacía
    los datos personales del cliente y lo marca `anonimizado` — conservando `id_cliente` y sus
    métricas agregadas (`intervalo_compra`, `senal_fuga`) intactas (FR-016). La señal misma
    permanece `confirmada`: no existe un cuarto estado para "ya purgada".

    Si el cliente registró una nueva visita antes de esta ejecución, `registrar_visita` ya
    marcó la señal `resuelta` y limpió `instante_purga_programada` (FR-009, FR-015): esa fila
    ya no aparece en la consulta de abajo, así que la anonimización queda cancelada por
    construcción, sin ninguna comprobación adicional aquí.
    """
    ahora = datetime.now(timezone.utc)

    vencidas = sesion.execute(
        select(SenalFuga).where(
            SenalFuga.estado == "confirmada",
            SenalFuga.instante_purga_programada.is_not(None),
            SenalFuga.instante_purga_programada <= ahora,
        )
    ).scalars().all()

    anonimizados = 0
    for senal in vencidas:
        cliente = sesion.get(Cliente, senal.id_cliente)
        if cliente is None or cliente.anonimizado:
            continue
        cliente.nombre = None
        cliente.fecha_nacimiento = None
        cliente.contacto = None
        cliente.anonimizado = True
        cliente.instante_anonimizacion = ahora
        anonimizados += 1

    sesion.commit()
    return anonimizados
