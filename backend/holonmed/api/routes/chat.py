"""Router conversacional.

Un mensaje del usuario se clasifica en una intención y se despacha a la
herramienta correspondiente. La clasificación usa el modelo rápido y tiene
red de seguridad: si no reconoce la intención, cae en consulta médica
general en vez de ejecutar una acción equivocada.

Este módulo **no escribe nada**. Receta, cita, alta de paciente y tic sólo
se **proponen**: escribirlos exige la confirmación nombrada de
`routes/recetas.py` o `routes/confirmaciones.py`. Enviar por WhatsApp
devuelve un enlace que el profesional debe pulsar.

La intención y los campos salen de un modelo, así que ninguno basta para
escribir: la intención sólo elige qué proponer, y un campo de la cita o del
alta que no esté en el mensaje no se usa ni se completa.
"""

import logging
import urllib.parse
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends

from ...core.cita import PeticionInvalida, citado_del_mensaje, interpretar_fecha
from ...core.entrada_no_confiable import detectar_instrucciones
from ...core.receta import ExtraccionInvalida, validar_extraccion
from ...llm import LLMUnavailable
from ...models import (
    ChatRequest,
    HolonPaciente,
    Infon,
    OrigenTic,
    Polaridad,
    PropuestaCita,
    PropuestaPaciente,
    PropuestaReceta,
    PropuestaTic,
)
from ..deps import AppContext, get_context
from ..historia import cargar_holon, huella

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
- agendar: pedir una cita (extrae "motivo" y "fecha"; "fecha" es el día y la
  hora juntos)
- whatsapp: mandar un mensaje al paciente (extrae "mensaje")
- receta: generar una receta o documento
- buscar_paciente: localizar un paciente (extrae "consulta")
- crear_paciente: dar de alta un paciente (extrae "nombre")
- cristalizar: procesar una narrativa clínica y extraer hallazgos
- medica: consulta médica general (opción por defecto)

"fecha", "motivo" y "nombre" se copian letra por letra del mensaje. Si el
mensaje no dice uno, no incluyas ese campo.

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
        return _proponer_cita(ctx, req, clasificacion)

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
        return _proponer_alta(ctx, req, clasificacion)

    if intencion == "cristalizar":
        return await _proponer_tic(ctx, req)

    return await _consulta_medica(ctx, holon, req.mensaje)


def _error(mensaje: str) -> dict[str, Any]:
    return {"tipo": "error", "mensaje": mensaje}


def _retenido(mensaje: str, negativa: str, consejo: str) -> dict[str, Any] | None:
    """El rechazo, si el mensaje contiene texto dirigido al sistema.

    El chat le habla al sistema, así que el imperativo es normal («haz la
    receta», «agenda…») y no da señal. Lo que sí la da retiene la petición
    entera antes de extraer nada. Un «registra que…» legítimo cae aquí y
    cuesta reformular; no se filtra por categoría porque la inyección
    observada era justamente una orden de escritura.
    """
    senales = detectar_instrucciones(mensaje)
    if not senales:
        return None
    encontrado = "; ".join(f"«{s.fragmento}»" for s in senales)
    return _error(
        f"{negativa}: el mensaje contiene texto dirigido al sistema "
        f"({encontrado}). No se ha extraído ni registrado nada. {consejo}"
    )


def _sin_alta() -> dict[str, Any]:
    return _error(
        "El paciente no está dado de alta. No se propone nada: dalo de alta "
        "o selecciona otro."
    )


def _proponer_cita(
    ctx: AppContext, req: ChatRequest, clasificacion: dict[str, Any]
) -> dict[str, Any]:
    retenido = _retenido(
        req.mensaje,
        "No se prepara la cita",
        "Pídela indicando sólo día, hora y motivo.",
    )
    if retenido:
        return retenido
    # Una cita sobre un identificador sin ficha crearía un paciente cuyo
    # nombre sería el propio identificador.
    holon = ctx.pacientes.obtener(req.paciente_id)
    if holon is None:
        return _sin_alta()
    try:
        fecha_texto = citado_del_mensaje(
            clasificacion.get("fecha"), req.mensaje, "la fecha"
        )
        motivo = citado_del_mensaje(clasificacion.get("motivo"), req.mensaje, "el motivo")
        fecha = interpretar_fecha(fecha_texto, datetime.now())
    except PeticionInvalida as exc:
        return _error(str(exc))

    propuesta = PropuestaCita(
        paciente_id=holon.paciente_id,
        paciente_nombre=holon.nombre,
        texto_original=req.mensaje,
        fecha_texto=fecha_texto,
        fecha=fecha.isoformat(),
        motivo=motivo,
    )
    ctx.propuestas_cita.guardar(propuesta)
    return {"tipo": "cita_propuesta", "datos": propuesta}


def _proponer_alta(
    ctx: AppContext, req: ChatRequest, clasificacion: dict[str, Any]
) -> dict[str, Any]:
    retenido = _retenido(
        req.mensaje, "No se prepara el alta", "Pídela indicando sólo el nombre."
    )
    if retenido:
        return retenido
    try:
        nombre = citado_del_mensaje(clasificacion.get("nombre"), req.mensaje, "el nombre")
    except PeticionInvalida as exc:
        return _error(str(exc))
    if not any(c.isalpha() for c in nombre):
        return _error("El nombre no contiene ninguna letra.")

    propuesta = PropuestaPaciente(texto_original=req.mensaje, nombre=nombre)
    ctx.propuestas_paciente.guardar(propuesta)
    return {"tipo": "paciente_propuesto", "datos": propuesta}


async def _proponer_tic(ctx: AppContext, req: ChatRequest) -> dict[str, Any]:
    """Procesa la narrativa y enseña el tic. No lo guarda."""
    retenido = _retenido(
        req.mensaje,
        "No se procesa la narrativa desde el chat",
        "Si es el texto de un expediente, usa el panel de cristalización, que "
        "lo conserva marcado y sin validar nada.",
    )
    if retenido:
        return retenido
    holon = ctx.pacientes.obtener(req.paciente_id)
    if holon is None:
        return _sin_alta()
    cargar_holon(ctx, holon)
    # Antes del pipeline: lo que cambie mientras corre también invalida.
    historia = huella(holon)
    try:
        tic = await ctx.pipeline.ejecutar(req.mensaje, holon)
    except LLMUnavailable as exc:
        return _error(str(exc))
    tic.origen = OrigenTic.CONSULTA

    propuesta = PropuestaTic(
        paciente_id=holon.paciente_id,
        paciente_nombre=holon.nombre,
        huella_historia=historia,
        tic=tic,
    )
    ctx.propuestas_tic.guardar(propuesta)
    return {"tipo": "tic_propuesto", "datos": propuesta}


async def _proponer_receta(
    ctx: AppContext, holon: HolonPaciente, mensaje: str
) -> dict[str, Any]:
    """Redacta una propuesta de receta. No escribe nada en ningún sitio.

    Recibe el mensaje tal como lo envió la persona. Una `peticion` devuelta
    por el router sería una reescritura de un modelo: podría añadir un
    fármaco que nadie pidió, o quitar la frase que delata una inyección.
    """
    retenido = _retenido(
        mensaje,
        "No se prepara la receta",
        "Revisa lo que hayas pegado y pide la receta indicando sólo fármaco, "
        "concentración e indicaciones.",
    )
    if retenido:
        return retenido

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


def _contexto_de_hallazgos(infones: list[Infon]) -> str:
    """Los hallazgos previos para el modelo, sin perder la polaridad.

    El término de un infón no lleva la negación: en una sola lista,
    «Sin ictericia» le llegaría como «Ictericia».
    """
    if not infones:
        return "Sin hallazgos previos registrados."
    lineas = []
    for rotulo, polaridad in (
        ("HALLAZGOS VALIDADOS PREVIOS", Polaridad.PRESENTE),
        ("AUSENCIAS DOCUMENTADAS (constan como NO presentes)", Polaridad.AUSENTE),
    ):
        terminos = [i.termino for i in infones if i.polaridad is polaridad]
        if terminos:
            lineas.append(f"{rotulo}: " + "; ".join(terminos))
    return "\n".join(lineas)


async def _consulta_medica(ctx: AppContext, holon, mensaje: str) -> dict[str, Any]:
    """Consulta general, apoyada en el historial validado del paciente."""
    infones = ctx.tics.linea_tiempo(holon.paciente_id, limite=15)
    contexto = _contexto_de_hallazgos(infones)

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
