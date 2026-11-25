"""Router conversacional.

Un mensaje del usuario se clasifica en una intención y se despacha a la
herramienta correspondiente. La clasificación usa el modelo rápido y tiene
red de seguridad: si no reconoce la intención, cae en consulta médica
general en vez de ejecutar una acción equivocada.

Nada sale del sistema por su cuenta: enviar por WhatsApp devuelve un enlace
que el profesional debe pulsar. La receta sólo se **propone** aquí; este
módulo no genera el PDF ni la escribe en la historia, y emitirla exige la
confirmación nombrada de `routes/recetas.py`.

`agendar`, `crear_paciente` y `cristalizar` sí escriben sin esa
confirmación. Es deuda declarada.
"""

import logging
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends

from ...core.entrada_no_confiable import detectar_instrucciones
from ...core.receta import ExtraccionInvalida, validar_extraccion
from ...llm import LLMUnavailable
from ...models import ChatRequest, HolonPaciente, OrigenTic, PropuestaReceta
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
- receta: generar una receta o documento
- buscar_paciente: localizar un paciente (extrae "consulta")
- crear_paciente: dar de alta un paciente (extrae "nombre")
- cristalizar: procesar una narrativa clínica y extraer hallazgos
- medica: consulta médica general (opción por defecto)

MENSAJE: "{mensaje}"

Responde en JSON: {{"intencion": "...", ...campos extraídos...}}"""


@router.post("/chat")
async def chat(
    req: ChatRequest, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
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
        return await _proponer_receta(ctx, holon, req.mensaje)

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
        tic = await ctx.pipeline.ejecutar(req.mensaje, holon)
        tic.origen = OrigenTic.CONSULTA
        tic.tic_id = ctx.tics.guardar(tic)
        return {"tipo": "tic", "datos": tic}

    return await _consulta_medica(ctx, holon, req.mensaje)


async def _proponer_receta(
    ctx: AppContext, holon: HolonPaciente, mensaje: str
) -> dict[str, Any]:
    """Redacta una propuesta de receta. No escribe nada en ningún sitio.

    Recibe el mensaje tal como lo envió la persona. Una `peticion` devuelta
    por el router sería una reescritura de un modelo: podría añadir un
    fármaco que nadie pidió, o quitar la frase que delata una inyección.
    """
    # El chat le habla al sistema, así que el imperativo es normal («haz la
    # receta», «prescribe…») y no da señal. Lo que sí la da retiene la
    # petición entera antes de extraer nada. Un «registra que…» legítimo cae
    # aquí y cuesta reformular; no se filtra por categoría porque la
    # inyección observada era justamente una orden de escritura.
    senales = detectar_instrucciones(mensaje)
    if senales:
        encontrado = "; ".join(f"«{s.fragmento}»" for s in senales)
        return {
            "tipo": "error",
            "mensaje": (
                "No se prepara la receta: el mensaje contiene texto dirigido al "
                f"sistema ({encontrado}). No se ha extraído ni registrado nada. "
                "Revisa lo que hayas pegado y pide la receta indicando sólo "
                "fármaco, concentración e indicaciones."
            ),
        }

    skill = ctx.skills.cargar("receta")
    instrucciones = (
        skill.contenido
        if skill
        else 'Extrae los medicamentos como JSON: {"items": [{"farmaco": "", "concentracion": "", "indicaciones": ""}]}'
    )

    try:
        datos = await ctx.llm.generar_json(
            f"{instrucciones}\n\nPACIENTE: {holon.nombre}\nPETICIÓN: {mensaje}\n\nJSON:",
            model=ctx.settings.model_clinical,
            timeout=ctx.settings.llm_timeout_slow,
        )
    except LLMUnavailable as exc:
        return {"tipo": "error", "mensaje": str(exc)}

    try:
        items, generales = validar_extraccion(datos)
    except ExtraccionInvalida as exc:
        return {"tipo": "error", "mensaje": str(exc)}

    propuesta = PropuestaReceta(
        paciente_id=holon.paciente_id,
        paciente_nombre=holon.nombre,
        texto_original=mensaje,
        items=items,
        indicaciones_generales=generales,
    )
    ctx.propuestas_receta.guardar(propuesta)
    return {"tipo": "receta_propuesta", "datos": propuesta}


async def _consulta_medica(ctx: AppContext, holon, mensaje: str) -> dict[str, Any]:
    """Consulta general, apoyada en el historial validado del paciente."""
    infones = ctx.tics.linea_tiempo(holon.paciente_id, limite=15)
    contexto = (
        "HALLAZGOS VALIDADOS PREVIOS: " + "; ".join(i.termino for i in infones)
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
