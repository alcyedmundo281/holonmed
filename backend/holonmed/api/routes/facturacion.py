"""Rutas de facturación: órdenes, conciliación y cuenta.

El orden de las rutas refleja el de la cadena. No hay ningún punto de
entrada que cree un cargo directamente: un cargo sólo nace de conciliar
una orden con su ejecución.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ...facturacion import (
    FORMATOS,
    Cuenta,
    Ejecucion,
    EstadoOrden,
    Orden,
    OrdenPropuesta,
    exportar,
)
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


class RegistroCrudo(BaseModel):
    """Un registro asistencial en texto libre, tal como lo escribe el actor."""

    paciente_id: str
    rol: str = Field(description="enfermeria, farmacia… según los protocolos")
    texto: str = Field(min_length=1)
    termino: str | None = Field(default=None, description="Qué se ejecutó, si ya se sabe")
    actor: str | None = None
    referencias: dict[str, str] = Field(default_factory=dict)


@router.post("/registros", status_code=201)
async def registrar_operativo(
    registro: RegistroCrudo, ctx: AppContext = Depends(get_context)
):
    """Estructura un registro según el protocolo del rol que lo firma.

    Cada rol declara en su propio protocolo qué campos exige. Lo valioso
    no es lo que extrae sino **lo que señala que falta**: un registro a
    medias es una causa real de que un procedimiento no se facture, y aquí
    se detecta cuando todavía se puede corregir.
    """
    extraido = await ctx.registros.extraer(registro.texto, registro.rol)

    ejecucion = Ejecucion(
        paciente_id=registro.paciente_id,
        termino=registro.termino
        or extraido.campos.get("medicamento")
        or extraido.campos.get("preparacion")
        or "",
        origen=registro.rol,
        actor=registro.actor or extraido.campos.get("responsable"),
        texto_origen=registro.texto,
        detalle=extraido.campos,
        referencias=registro.referencias,
        campos_faltantes=extraido.faltantes,
    )

    if not ejecucion.termino:
        raise HTTPException(
            422, "No se pudo determinar qué se ejecutó; indícalo en `termino`"
        )

    concepto = ctx.terminologia.buscar_exacto(ejecucion.termino)
    if concepto:
        ejecucion.codigo, ejecucion.sistema = concepto.codigo, concepto.sistema

    ejecucion.id = ctx.ejecuciones.registrar(ejecucion)
    return {
        "ejecucion": ejecucion,
        "completo": extraido.completo,
        "faltantes": extraido.faltantes,
        "resumen": extraido.resumen(),
    }


@router.get("/roles")
async def roles(ctx: AppContext = Depends(get_context)):
    """Protocolos operativos disponibles y qué exige cada uno."""
    salida = []
    for nombre in ctx.skills.listar():
        skill = ctx.skills.cargar(nombre)
        if not skill or skill.tipo != "operativo":
            continue
        salida.append(
            {
                "rol": skill.rol,
                "protocolo": nombre,
                "titulo": skill.titulo,
                "campos": [
                    {"nombre": c.nombre, "titulo": c.titulo, "requerido": c.requerido}
                    for c in skill.campos
                ],
            }
        )
    return salida


@router.get("/cuenta/{paciente_id}/exportar", response_class=PlainTextResponse)
async def exportar_cuenta(
    paciente_id: str,
    formato: str = "xml",
    incluir_propuestos: bool = False,
    emisor: str | None = None,
    ctx: AppContext = Depends(get_context),
):
    """Exporta la cuenta al formato que consuma el sistema de destino.

    XML por defecto porque es lo que suelen exigir los sistemas de
    facturación y de intercambio sanitario: validan contra un esquema y a
    veces requieren firma. HolonMed no conoce el esquema de ningún
    organismo concreto y no debería: entrega la estructura completa y
    trazable, y el mapeo al esquema de cada sitio es una capa de
    integración propia de ese despliegue.

    Por defecto sólo salen los cargos confirmados: exportar algo que nadie
    ha revisado sería mandar a facturar lo que el sistema apenas propuso.
    """
    if formato not in FORMATOS:
        raise HTTPException(400, f"Formato no soportado. Usa uno de: {list(FORMATOS)}")

    cuenta = ctx.conciliador.cuenta(paciente_id)
    contenido = (
        exportar(cuenta, formato, emisor=emisor, incluir_propuestos=incluir_propuestos)
        if formato == "xml"
        else exportar(cuenta, formato)
    )

    tipos = {"xml": "application/xml", "json": "application/json", "csv": "text/csv"}
    return PlainTextResponse(contenido, media_type=tipos[formato])


class PlanCrudo(BaseModel):
    """El texto del plan, tal como lo escribe el médico."""

    paciente_id: str
    texto: str = Field(min_length=1)


class Autorizacion(BaseModel):
    """La firma que convierte un borrador en una orden real."""

    paciente_id: str
    propuestas: list[OrdenPropuesta]
    prescriptor: str | None = None


@router.post("/ordenes/proponer")
async def proponer_ordenes(plan: PlanCrudo, ctx: AppContext = Depends(get_context)):
    """Lee el plan y propone las órdenes que ve. **No crea ninguna.**

    Es el borrador que acompaña al plan, con su botón. Nada queda
    autorizado hasta que alguien lo firma en `/ordenes/autorizar`, y esa
    separación es la condición para que el resto se sostenga: toda la
    cadena de facturación se apoya en que la orden es un acto de una
    persona.
    """
    propuestas = await ctx.proponedor.proponer(plan.texto)
    return {
        "paciente_id": plan.paciente_id,
        "propuestas": propuestas,
        "aviso": (
            "Ninguna de estas órdenes existe todavía. Revisa y autoriza las "
            "que correspondan."
        ),
    }


@router.post("/ordenes/autorizar", status_code=201)
async def autorizar_ordenes(
    autorizacion: Autorizacion, ctx: AppContext = Depends(get_context)
):
    """Convierte en órdenes reales las propuestas que el médico firma.

    Recibe sólo las que autoriza, ya editadas si hizo falta. Las que no
    envíe simplemente no existen: descartar un borrador no requiere
    ninguna acción.
    """
    creadas = []
    for propuesta in autorizacion.propuestas:
        orden = propuesta.a_orden(
            autorizacion.paciente_id, prescriptor=autorizacion.prescriptor
        )
        # El médico pudo corregir el término al revisar, y entonces el
        # borrador llega sin código. Se resuelve aquí contra el término
        # final: es el que se ordena y el que habrá que tarifar.
        if not orden.concepto_id:
            concepto = ctx.terminologia.buscar_exacto(orden.termino)
            if concepto:
                orden.concepto_id = concepto.concepto_id
                orden.codigo, orden.sistema = concepto.codigo, concepto.sistema

        orden.id = ctx.ordenes.crear(orden)
        if orden.id:
            creadas.append(orden)

    if not creadas:
        raise HTTPException(500, "No se pudo registrar ninguna orden")
    return {"creadas": len(creadas), "ordenes": creadas}
