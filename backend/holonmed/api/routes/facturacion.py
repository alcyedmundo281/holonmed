"""Rutas de facturación: órdenes, conciliación y cuenta.

El orden de las rutas refleja el de la cadena. No hay ningún punto de
entrada que cree un cargo directamente: un cargo sólo nace de conciliar
una orden con su ejecución.
"""

from fastapi import APIRouter, Depends, HTTPException

from ...facturacion import Cuenta, Ejecucion, EstadoOrden, Orden
from ..deps import AppContext, get_context

router = APIRouter(prefix="/api/facturacion", tags=["facturación"])


@router.post("/ordenes", status_code=201)
async def crear_orden(orden: Orden, ctx: AppContext = Depends(get_context)):
    """Registra lo que el profesional autorizó.

    Es el primer eslabón: sin orden no puede haber cargo. Se intenta
    resolver el término contra el vocabulario para que después encuentre
    su código tarifario.
    """
    if not orden.concepto_id:
        concepto = ctx.terminologia.buscar_exacto(orden.termino)
        if concepto:
            orden.concepto_id = concepto.concepto_id
            orden.codigo = orden.codigo or concepto.codigo
            orden.sistema = orden.sistema or concepto.sistema

    orden.id = ctx.ordenes.crear(orden)
    if not orden.id:
        raise HTTPException(500, "No se pudo registrar la orden")
    return orden


@router.get("/ordenes/{paciente_id}")
async def listar_ordenes(
    paciente_id: str,
    estado: EstadoOrden | None = None,
    ctx: AppContext = Depends(get_context),
):
    return ctx.ordenes.listar(paciente_id, estado)


@router.post("/ejecuciones", status_code=201)
async def registrar_ejecucion(
    ejecucion: Ejecucion, ctx: AppContext = Depends(get_context)
):
    """Registra que un actor cumplió algo.

    No exige que exista la orden: si no existe, la conciliación lo
    detectará como administración no autorizada, que es un incidente de
    seguridad y no algo que deba ocultarse rechazando el registro.
    """
    if not ejecucion.codigo:
        concepto = ctx.terminologia.buscar_exacto(ejecucion.termino)
        if concepto:
            ejecucion.codigo = concepto.codigo
            ejecucion.sistema = concepto.sistema

    ejecucion.id = ctx.ejecuciones.registrar(ejecucion)
    if not ejecucion.id:
        raise HTTPException(500, "No se pudo registrar la ejecución")
    return ejecucion


@router.get("/conciliacion/{paciente_id}")
async def conciliar(paciente_id: str, ctx: AppContext = Depends(get_context)):
    """Compara lo ordenado con lo ejecutado.

    De los tres resultados sólo uno es de facturación. Los otros dos son
    incidentes clínicos: algo prescrito que no se cumplió, o algo
    administrado que nadie autorizó.
    """
    resultado = ctx.conciliador.conciliar(paciente_id)
    return {
        "cuadra": resultado.cuadra,
        "parejas": [
            {"orden": p.orden, "ejecucion": p.ejecucion} for p in resultado.parejas
        ],
        "descuadres": resultado.descuadres,
    }


@router.post("/cuenta/{paciente_id}/calcular", response_model=Cuenta)
async def calcular(paciente_id: str, ctx: AppContext = Depends(get_context)) -> Cuenta:
    """Deriva los cargos de las parejas conciliadas.

    Todo cargo nace **propuesto**: facturar exige que una persona lo
    confirme. En condiciones normales esto se ejecuta al cerrar cada tic,
    no al alta.
    """
    return ctx.conciliador.facturar(paciente_id)


@router.get("/cuenta/{paciente_id}", response_model=Cuenta)
async def cuenta(paciente_id: str, ctx: AppContext = Depends(get_context)) -> Cuenta:
    """La cuenta al día, sin recalcular nada.

    Las seis horas de espera al alta no son un problema de velocidad de
    proceso sino de arquitectura: la cuenta se calculaba en bloque al
    final. Aquí los cargos se acumulan según se concilian y esto sólo los
    proyecta.
    """
    return ctx.conciliador.cuenta(paciente_id)


@router.post("/cargos/{cargo_id}/confirmar")
async def confirmar_cargo(cargo_id: str, ctx: AppContext = Depends(get_context)):
    """Autoriza un cargo propuesto. Es el paso que lo hace facturable."""
    if not ctx.cargos.confirmar(cargo_id):
        raise HTTPException(400, "No se pudo confirmar el cargo")
    return {"estado": "confirmado", "cargo_id": cargo_id}


@router.post("/cargos/{cargo_id}/anular")
async def anular_cargo(cargo_id: str, ctx: AppContext = Depends(get_context)):
    if not ctx.cargos.anular(cargo_id):
        raise HTTPException(400, "No se pudo anular el cargo")
    return {"estado": "anulado", "cargo_id": cargo_id}


@router.get("/tarifarios")
async def tarifarios(ctx: AppContext = Depends(get_context)):
    """Catálogos de precios cargados.

    Un tarifario es un vocabulario más: cada hospital carga el suyo con
    `scripts/importar_tarifario.py` sin tocar código.
    """
    return {
        "activo": ctx.settings.sistema_tarifario,
        "cargados": ctx.tarifas.sistemas(),
    }
