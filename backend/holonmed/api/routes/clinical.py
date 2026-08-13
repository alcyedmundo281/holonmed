"""Rutas clínicas: cristalización, historial y línea de tiempo del holón."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ...models import CrystallizeRequest, OrigenTic, ResultadoTic
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
    resultado.origen = req.origen
    resultado.actor = req.actor
    resultado.tic_id = ctx.tics.guardar(resultado)
    return resultado


@router.post("/labs/upload")
async def subir_laboratorio(
    paciente_id: str,
    archivo: UploadFile = File(...),
    actor: str | None = None,
    ctx: AppContext = Depends(get_context),
):
    """Extrae el texto de un informe PDF y lo pasa por el pipeline.

    El tic queda marcado con origen `laboratorio`: un informe de
    laboratorio y una nota dictada alimentan la misma historia, pero no
    son la misma clase de evidencia y deben poder distinguirse después.
    """
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
    resultado.origen = OrigenTic.LABORATORIO
    resultado.actor = actor
    resultado.tic_id = ctx.tics.guardar(resultado)
    ctx.documentos.registrar(
        paciente_id,
        tipo="informe_laboratorio",
        archivo=archivo.filename,
        tic_id=resultado.tic_id,
    )

    return {
        "archivo": archivo.filename,
        "caracteres_extraidos": len(texto),
        "resultado": resultado,
    }


@router.get("/pacientes/{paciente_id}/historial")
async def historial(
    paciente_id: str,
    origen: OrigenTic | None = None,
    ctx: AppContext = Depends(get_context),
):
    """Registro de auditoría: cada tic procesado para este paciente.

    Se puede filtrar por origen para ver sólo lo que aportó un actor
    concreto del entorno clínico.
    """
    return ctx.tics.historial(paciente_id, origen=origen.value if origen else None)


@router.get("/pacientes/{paciente_id}/origenes")
async def origenes(paciente_id: str, ctx: AppContext = Depends(get_context)):
    """Qué actores han aportado información sobre este paciente."""
    return ctx.tics.por_origen(paciente_id)


@router.get("/pacientes/{paciente_id}/documentos")
async def documentos(
    paciente_id: str,
    tipo: str | None = None,
    ctx: AppContext = Depends(get_context),
):
    """Recetas e informes emitidos, con su contenido estructurado."""
    return ctx.documentos.listar(paciente_id, tipo)


@router.get("/pacientes/{paciente_id}/holon")
async def holon_completo(paciente_id: str, ctx: AppContext = Depends(get_context)):
    """El holón: datos del paciente más su línea de tiempo de infones."""
    holon = ctx.pacientes.obtener_o_efimero(paciente_id)
    holon.linea_tiempo = ctx.tics.linea_tiempo(paciente_id)
    return holon


@router.get("/skills")
async def listar_skills(ctx: AppContext = Depends(get_context)):
    """Protocolos clínicos disponibles y el conocimiento que aportan.

    Los protocolos operativos —enfermería, farmacia— quedan fuera: no
    interpretan una narrativa clínica, estructuran el registro de un actor.
    Ofrecerlos donde se elige con qué leer una nota sólo confunde; viven en
    `/api/facturacion/roles`.
    """
    salida = []
    for nombre in ctx.skills.listar():
        skill = ctx.skills.cargar(nombre)
        if not skill or skill.tipo == "operativo":
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
