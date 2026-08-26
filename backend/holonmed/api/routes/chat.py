"""Router conversacional.

Un mensaje del usuario se clasifica en una intención y se despacha a la
herramienta correspondiente. La clasificación usa el modelo rápido y tiene
red de seguridad: si no reconoce la intención, cae en consulta médica
general en vez de ejecutar una acción equivocada.

Nota de diseño: ninguna intención ejecuta algo irreversible sin que el
resultado vuelva al clínico. Enviar por WhatsApp devuelve un enlace que el
profesional debe pulsar; el sistema no envía nada por su cuenta.
"""

import logging
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends

from ...llm import LLMUnavailable
from ...models import ChatRequest, OrigenTic, ResultadoTic
from ..deps import AppContext, get_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

INTENCIONES = [
    "agendar",
    "whatsapp",
    "receta",
    "buscar_paciente",
    "crear_paciente",
    "cristalizar",
    "medica",
]

PROMPT_ROUTER = """Clasifica la intención del mensaje del usuario.

INTENCIONES:
- agendar: pedir una cita (extrae "fecha" y "motivo")
- whatsapp: mandar un mensaje al paciente (extrae "mensaje")
- receta: generar una receta o documento (extrae "peticion")
- buscar_paciente: localizar un paciente (extrae "consulta")
- crear_paciente: dar de alta un paciente (extrae "nombre")
- cristalizar: procesar una narrativa clínica y extraer hallazgos
- medica: consulta médica general (opción por defecto)

MENSAJE: "{mensaje}"

Responde en JSON: {{"intencion": "...", ...campos extraídos...}}"""


@router.post("/chat")
async def chat(req: ChatRequest, ctx: AppContext = Depends(get_context)) -> dict[str, Any]:
    holon = ctx.pacientes.obtener_o_efimero(req.paciente_id)

    try:
        clasificacion = await ctx.llm.generar_json(
            PROMPT_ROUTER.format(mensaje=req.mensaje),
            model=ctx.settings.model_router,
            timeout=ctx.settings.llm_timeout_fast,
        )
    except LLMUnavailable as exc:
        return {"tipo": "error", "mensaje": f"Modelo no disponible: {exc}"}

    intencion = str(clasificacion.get("intencion", "medica")).lower().strip()
    if intencion not in INTENCIONES:
        intencion = "medica"
    logger.info("Intención: %s", intencion)

    if intencion == "agendar":
        resultado = ctx.agenda.agendar(
            req.paciente_id,
            str(clasificacion.get("fecha", "la próxima semana")),
            str(clasificacion.get("motivo", "Control")),
        )
        return {"tipo": "agenda", "datos": resultado}

    if intencion == "whatsapp":
        mensaje = str(clasificacion.get("mensaje", req.mensaje))
        telefono = holon.telefono
        if not telefono:
            return {
                "tipo": "error",
                "mensaje": "El paciente no tiene teléfono registrado.",
            }
        # Se devuelve el enlace: el envío lo confirma una persona.
        return {
            "tipo": "whatsapp",
            "datos": {
                "url": f"https://wa.me/{telefono}?text={urllib.parse.quote(mensaje)}",
                "telefono": telefono,
                "mensaje": mensaje,
                "aviso": "Revisa el mensaje antes de enviarlo.",
            },
        }

    if intencion == "receta":
        return await _generar_receta(
            ctx, holon, str(clasificacion.get("peticion", req.mensaje))
        )

    if intencion == "buscar_paciente":
        encontrado = ctx.pacientes.buscar(str(clasificacion.get("consulta", req.mensaje)))
        return {
            "tipo": "paciente",
            "datos": encontrado,
            "encontrado": bool(encontrado),
        }

    if intencion == "crear_paciente":
        nombre = str(clasificacion.get("nombre", "")).strip()
        if not nombre:
            return {"tipo": "error", "mensaje": "No se identificó un nombre."}
        creado = ctx.pacientes.crear({"nombre": nombre, "antecedentes": ""})
        return {"tipo": "paciente", "datos": creado, "creado": bool(creado)}

    if intencion == "cristalizar":
        holon.linea_tiempo = ctx.tics.linea_tiempo(req.paciente_id)
        holon.phi_previo = ctx.tics.phi_por_hipotesis(req.paciente_id)
        resultado = await ctx.pipeline.ejecutar(req.mensaje, holon)
        resultado.origen = OrigenTic.CONSULTA
        resultado.tic_id = ctx.tics.guardar(resultado)
        return {"tipo": "tic", "datos": resultado}

    return await _consulta_medica(ctx, holon, req.mensaje)


async def _generar_receta(ctx: AppContext, holon, peticion: str) -> dict[str, Any]:
    skill = ctx.skills.cargar("receta")
    instrucciones = (
        skill.contenido
        if skill
        else 'Extrae los medicamentos como JSON: {"items": [{"farmaco": "", "concentracion": "", "indicaciones": ""}]}'
    )

    try:
        datos = await ctx.llm.generar_json(
            f"{instrucciones}\n\nPACIENTE: {holon.nombre}\nPETICIÓN: {peticion}\n\nJSON:",
            model=ctx.settings.model_clinical,
            timeout=ctx.settings.llm_timeout_slow,
        )
    except LLMUnavailable as exc:
        return {"tipo": "error", "mensaje": str(exc)}

    items = datos.get("items") or datos.get("rx_items") or []
    if not items:
        return {
            "tipo": "error",
            "mensaje": "No se identificaron medicamentos en la petición.",
        }

    ruta = ctx.recetas.generar(items, holon.nombre)
    if not ruta:
        return {"tipo": "error", "mensaje": "No se pudo generar el PDF."}

    # La receta entra en la historia como un tic de origen `farmacia`.
    # Antes sólo se generaba el PDF: el fármaco prescrito no dejaba rastro
    # y desaparecía en cuanto se cerraba la ventana. Un fármaco prescrito
    # es parte del registro clínico, y su ausencia rompe la conciliación
    # de la medicación en la visita siguiente.
    resumen = ", ".join(
        f"{i.get('farmaco') or i.get('drug', '?')} {i.get('concentracion', '')}".strip()
        for i in items
    )
    tic = ResultadoTic(
        paciente_id=holon.paciente_id,
        texto_original=peticion,
        origen=OrigenTic.FARMACIA,
        skill_activa="receta",
        resumen=f"Receta: {resumen}",
    )
    tic.tic_id = ctx.tics.guardar(tic)
    ctx.documentos.registrar(
        holon.paciente_id,
        tipo="receta",
        archivo=ruta.name,
        datos={"items": items, "indicaciones": datos.get("indicaciones_generales", "")},
        tic_id=tic.tic_id,
    )

    return {
        "tipo": "receta",
        "datos": {
            "url": f"/api/documentos/{ruta.name}",
            "items": items,
            "tic_id": tic.tic_id,
            "aviso": "Borrador sin validez hasta que lo revises y lo firmes.",
        },
    }


async def _consulta_medica(ctx: AppContext, holon, mensaje: str) -> dict[str, Any]:
    """Consulta general, apoyada en el historial validado del paciente."""
    infones = ctx.tics.linea_tiempo(holon.paciente_id, limite=15)
    contexto = (
        "HALLAZGOS VALIDADOS PREVIOS: "
        + "; ".join(i.termino for i in infones)
        if infones
        else "Sin hallazgos previos registrados."
    )

    prompt = f"""Eres un asistente clínico. Respondes a un profesional sanitario.

PACIENTE: {holon.nombre}
{contexto}

Responde con precisión y en español. Si la pregunta requiere datos que no
tienes, dilo en lugar de suponerlos. No inventes valores ni antecedentes.

CONSULTA: {mensaje}"""

    try:
        respuesta = await ctx.llm.generar(
            prompt,
            model=ctx.settings.model_clinical,
            timeout=ctx.settings.llm_timeout_slow,
        )
    except LLMUnavailable as exc:
        return {"tipo": "error", "mensaje": str(exc)}

    return {"tipo": "texto", "datos": {"respuesta": respuesta}}
