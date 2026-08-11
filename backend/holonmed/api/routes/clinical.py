"""Rutas clínicas: cristalización, historial y línea de tiempo del holón."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ...models import CrystallizeRequest, ResultadoTic
from ...services import LabExtractionError, extraer_texto_pdf
from ..deps import AppContext, get_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["clínica"])


@router.post("/crystallize", response_model=ResultadoTic)
async def cristalizar(
    req: CrystallizeRequest,
    ctx: AppContext = Depends(get_context),
) -> ResultadoTic:
    """Convierte narrativa clínica libre en infones validados.

    Es el corazón del sistema: triaje del protocolo, extracción, validación
    ontológica y lógica, e inferencia bayesiana. Devuelve también los
    hallazgos descartados, con su motivo — descartar en silencio impediría
    auditar al sistema.
    """
    holon = ctx.pacientes.obtener_o_efimero(req.paciente_id)
    holon.linea_tiempo = ctx.tics.linea_tiempo(req.paciente_id)

    resultado = await ctx.pipeline.ejecutar(req.texto, holon, skill_forzada=req.skill)
    resultado.tic_id = ctx.tics.guardar(resultado)
    return resultado


@router.post("/labs/upload")
async def subir_laboratorio(
    paciente_id: str,
    archivo: UploadFile = File(...),
    ctx: AppContext = Depends(get_context),
):
    """Extrae el texto de un informe PDF y lo pasa por el pipeline."""
    if archivo.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(415, "Sólo se aceptan archivos PDF")

    contenido = await archivo.read()
    try:
        texto = extraer_texto_pdf(contenido)
    except LabExtractionError as exc:
        raise HTTPException(422, str(exc)) from exc

    holon = ctx.pacientes.obtener_o_efimero(paciente_id)
    holon.linea_tiempo = ctx.tics.linea_tiempo(paciente_id)

    resultado = await ctx.pipeline.ejecutar(texto, holon)
    resultado.tic_id = ctx.tics.guardar(resultado)

    return {
        "archivo": archivo.filename,
        "caracteres_extraidos": len(texto),
        "resultado": resultado,
    }


@router.get("/pacientes/{paciente_id}/historial")
async def historial(paciente_id: str, ctx: AppContext = Depends(get_context)):
    """Registro de auditoría: cada tic procesado para este paciente."""
    return ctx.tics.historial(paciente_id)


@router.get("/pacientes/{paciente_id}/holon")
async def holon_completo(paciente_id: str, ctx: AppContext = Depends(get_context)):
    """El holón: datos del paciente más su línea de tiempo de infones."""
    holon = ctx.pacientes.obtener_o_efimero(paciente_id)
    holon.linea_tiempo = ctx.tics.linea_tiempo(paciente_id)
    return holon


@router.get("/skills")
async def listar_skills(ctx: AppContext = Depends(get_context)):
    """Protocolos disponibles y el conocimiento estructurado que aportan."""
    salida = []
    for nombre in ctx.skills.listar():
        skill = ctx.skills.cargar(nombre)
        if not skill:
            continue
        salida.append(
            {
                "nombre": nombre,
                "descripcion": skill.descripcion,
                "hints_snomed": len(skill.hints_snomed()),
                "vocabulario": skill.vocabulario_preferido()[:20],
                "tiene_modelo_bayesiano": bool(
                    skill.json_principal.get("modelo_bayesiano")
                ),
            }
        )
    return salida


@router.get("/pacientes/{paciente_id}/problemas")
async def lista_problemas(paciente_id: str, ctx: AppContext = Depends(get_context)):
    """Lista de problemas: conceptos validados, deduplicados y fechados.

    Es la primera vista que mira un clínico. La primera y la última
    aparición son lo que distingue un problema agudo de uno arrastrado.
    """
    return ctx.tics.lista_problemas(paciente_id)


@router.get("/tics/{tic_id}")
async def tic_completo(tic_id: str, ctx: AppContext = Depends(get_context)):
    """Un tic con su texto original y todos sus infones, incluidos los descartados."""
    tic = ctx.tics.tic_completo(tic_id)
    if not tic:
        raise HTTPException(404, "Tic no encontrado")
    return tic
