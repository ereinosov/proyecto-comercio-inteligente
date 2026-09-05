"""Esqueleto FastAPI. Enrutador base y manejo de errores sin trazas técnicas (T011).

El operador nunca ve una traza; ve un mensaje con la acción correctiva (constitución,
Principio IV). Cualquier excepción no anticipada se registra en el log del servidor y se
devuelve como error genérico 500 sin detalle interno.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from rasero.errores import ErrorDominio

logger = logging.getLogger("rasero")

app = FastAPI(title="Rasero — Core de Ventas e Inventario", version="0.1.0")

# Desarrollo únicamente: el frontend de Vite corre en un origen distinto (puerto propio) y
# el navegador bloquea la petición sin CORS. Sin cookies ni credenciales de sesión en este
# módulo, un origen abierto es seguro para desarrollo local; se acota antes de empaquetar
# para producción (fase final del proyecto, ver plan.md).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ErrorDominio)
async def manejar_error_dominio(request: Request, exc: ErrorDominio) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"codigo": exc.codigo, "mensaje": exc.mensaje},
    )


@app.exception_handler(Exception)
async def manejar_error_inesperado(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error inesperado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "codigo": "error_interno",
            "mensaje": "Ocurrió un error. Intenta de nuevo; si persiste, avisa al encargado.",
        },
    )


def registrar_rutas() -> None:
    from rasero.api.turnos import router as router_turnos
    from rasero.api.ventas import router as router_ventas
    from rasero.api.productos import router as router_productos
    from rasero.api.operadores import router as router_operadores
    from rasero.api.clientes import router as router_clientes
    from rasero.api.precios import router as router_precios
    from rasero.api.pronostico import router as router_pronostico
    from rasero.api.promociones import router as router_promociones

    app.include_router(router_turnos)
    app.include_router(router_ventas)
    app.include_router(router_productos)
    app.include_router(router_operadores)
    app.include_router(router_clientes)
    app.include_router(router_precios)
    app.include_router(router_pronostico)
    app.include_router(router_promociones)


registrar_rutas()
