"""US6 de 002-clientes-fidelizacion (FR-018..FR-020): `GET /clientes/fuga/resumen` devuelve la
distribución instantánea de clientes por segmento de fuga. Snapshot, no serie temporal.

El test limpia lo que crea: deja `senal_fuga` 'activa' committed rompería
`test_semilla_reactivacion` (su pool de elegibles = clientes con señal activa).
"""

import datetime as dt

from sqlalchemy import delete
from fastapi.testclient import TestClient

from rasero.api.aplicacion import app
from rasero.persistencia.modelos import Cliente, IntervaloCompra, SenalFuga
from rasero.persistencia.sesion import SesionLocal

cliente_http = TestClient(app)

_AHORA = dt.datetime(2026, 9, 7, tzinfo=dt.timezone.utc)


def _resumen() -> dict:
    r = cliente_http.get("/clientes/fuga/resumen")
    assert r.status_code == 200
    cuerpo = r.json()
    assert set(cuerpo) == {"sin_senal", "datos_insuficientes", "activa", "confirmada", "resuelta"}
    return cuerpo


def test_resumen_cuenta_cada_segmento_y_excluye_anonimizados():
    sesion = SesionLocal()
    ids: list[int] = []
    try:
        base = _resumen()

        def nuevo(nombre: str, intervalo_estado: str, senal_estado: str | None) -> int:
            c = Cliente(nombre=nombre, fecha_alta=_AHORA)
            sesion.add(c)
            sesion.flush()
            ids.append(c.id_cliente)
            sesion.add(
                IntervaloCompra(
                    id_cliente=c.id_cliente,
                    intervalo_esperado_dias=None if intervalo_estado == "datos_insuficientes" else 10,
                    visitas_consideradas=1 if intervalo_estado == "datos_insuficientes" else 4,
                    estado=intervalo_estado,
                    instante_calculo=_AHORA,
                )
            )
            if senal_estado is not None:
                sesion.add(
                    SenalFuga(
                        id_cliente=c.id_cliente,
                        estado=senal_estado,
                        instante_deteccion=_AHORA,
                        instante_confirmacion=_AHORA if senal_estado == "confirmada" else None,
                        instante_resolucion=_AHORA if senal_estado == "resuelta" else None,
                        instante_purga_programada=(
                            _AHORA + dt.timedelta(days=90) if senal_estado == "confirmada" else None
                        ),
                    )
                )
            return c.id_cliente

        nuevo("Fuga sin señal", "calculado", None)
        nuevo("Fuga datos insuf", "datos_insuficientes", None)
        nuevo("Fuga activa", "calculado", "activa")
        nuevo("Fuga confirmada", "calculado", "confirmada")
        nuevo("Fuga resuelta", "calculado", "resuelta")

        c_anon = nuevo("no-cuenta", "calculado", "confirmada")
        anon = sesion.get(Cliente, c_anon)
        anon.nombre = None
        anon.anonimizado = True

        sesion.commit()

        despues = _resumen()
        assert despues["sin_senal"] == base["sin_senal"] + 1
        assert despues["datos_insuficientes"] == base["datos_insuficientes"] + 1
        assert despues["activa"] == base["activa"] + 1
        assert despues["confirmada"] == base["confirmada"] + 1
        assert despues["resuelta"] == base["resuelta"] + 1
    finally:
        if ids:
            sesion.execute(delete(SenalFuga).where(SenalFuga.id_cliente.in_(ids)))
            sesion.execute(delete(IntervaloCompra).where(IntervaloCompra.id_cliente.in_(ids)))
            sesion.execute(delete(Cliente).where(Cliente.id_cliente.in_(ids)))
            sesion.commit()
        sesion.close()
