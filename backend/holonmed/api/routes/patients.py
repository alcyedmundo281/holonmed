"""Gestión de pacientes y agenda."""

from typing import Any
from urllib.parse import quote

import yaml
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from ...core.cita import PeticionInvalida
from ...models import (
    Acoplamiento,
    AgrupacionDiagnostica,
    CandidataAbductiva,
    CitaCreate,
    InferenciaBayesiana,
    Infon,
    NotaEvolucion,
    OrigenTic,
    PacienteCreate,
    ReaperturaDeIndagacion,
    SenalInstruccion,
    VeredictoDeclarado,
)
from ..deps import AppContext, get_context

router = APIRouter(prefix="/api", tags=["pacientes"])


class DetalleConsulta(BaseModel):
    evolucion: NotaEvolucion | None
    instrucciones_detectadas: list[SenalInstruccion]
    todas_vetadas: str | None
    clasificacion: Any
    agrupaciones_triage: list[AgrupacionDiagnostica]


class ConsultaGuardada(BaseModel):
    tic_id: str
    paciente_id: str
    timestamp: str
    origen: OrigenTic
    skill_activa: str
    texto_original: str
    resumen: str
    infones: list[Infon]
    inferencia: InferenciaBayesiana | None
    acoplamiento: Acoplamiento | None
    veredicto_declarado: VeredictoDeclarado | None
    reapertura: ReaperturaDeIndagacion | None
    competencia: list[CandidataAbductiva]
    ganadora_abductiva: str | None
    triaje_coincide: bool | None
    aviso_triaje: str | None
    aviso_protocolo: str | None
    aviso_competencia: str | None
    detalle: DetalleConsulta | None


class ExpedientePaciente(BaseModel):
    paciente_id: str
    consulta: ConsultaGuardada | None
    problemas: list[dict[str, Any]]
    historia: list[dict[str, Any]]
    grafo: dict[str, list[dict[str, Any]]]


@router.get("/pacientes")
async def listar(ctx: AppContext = Depends(get_context)):
    return ctx.pacientes.listar()


@router.get("/pacientes/indice.yaml", response_class=Response)
async def indice_pacientes(ctx: AppContext = Depends(get_context)) -> Response:
    indice = {
        "pacientes": [
            {
                "id": paciente_id,
                "ruta": f"./expediente.json?id={quote(paciente_id, safe='')}",
            }
            for paciente_id in ctx.pacientes.listar_ids()
        ]
    }
    return Response(
        yaml.safe_dump(indice, allow_unicode=True, sort_keys=False),
        media_type="application/yaml",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/pacientes/expediente.json", response_model=ExpedientePaciente)
async def expediente_paciente(
    id: str, response: Response, ctx: AppContext = Depends(get_context)
) -> ExpedientePaciente:
    """Proyecciones del expediente guardado para Consulta, Problemas, Historia y Grafo."""
    response.headers["Cache-Control"] = "no-store"
    with ctx.database.conexion() as conexion:
        # Las cuatro vistas se leen del mismo estado, incluso con otra escritura en curso.
        conexion.execute("BEGIN")
        if ctx.pacientes.obtener(id) is None:
            raise HTTPException(404, "Paciente no encontrado")
        consulta = ctx.tics.ultima_consulta(id)
        return ExpedientePaciente(
            paciente_id=id,
            consulta=ConsultaGuardada.model_validate(consulta) if consulta else None,
            problemas=ctx.tics.lista_problemas(id),
            historia=ctx.tics.historial(id),
            grafo=ctx.grafo.vecindad(id),
        )


@router.post("/pacientes", status_code=201)
async def crear(datos: PacienteCreate, ctx: AppContext = Depends(get_context)):
    creado = ctx.pacientes.crear(datos.model_dump())
    if not creado:
        raise HTTPException(503, "Base de datos no disponible")
    return creado


@router.get("/pacientes/buscar")
async def buscar(q: str, ctx: AppContext = Depends(get_context)):
    encontrado = ctx.pacientes.buscar(q)
    if not encontrado:
        raise HTTPException(404, f"Sin coincidencias para '{q}'")
    return encontrado


@router.patch("/pacientes/{paciente_id}")
async def actualizar(
    paciente_id: str,
    campo: str,
    valor: str,
    ctx: AppContext = Depends(get_context),
):
    if not ctx.pacientes.actualizar(paciente_id, campo, valor):
        raise HTTPException(400, f"No se pudo actualizar el campo '{campo}'")
    return {"estado": "actualizado", "campo": campo, "valor": valor}


@router.get("/citas")
async def listar_citas(
    paciente_id: str | None = None,
    ctx: AppContext = Depends(get_context),
):
    return ctx.agenda.listar(paciente_id)


@router.post("/citas", status_code=201)
async def crear_cita(datos: CitaCreate, ctx: AppContext = Depends(get_context)):
    # La agenda daría de alta la ficha que falte, con el identificador por nombre.
    if ctx.pacientes.obtener(datos.paciente_id) is None:
        raise HTTPException(404, "El paciente no está dado de alta. No se agendó nada.")
    try:
        cita = ctx.agenda.agendar(datos.paciente_id, datos.fecha, datos.motivo)
    except PeticionInvalida as exc:
        raise HTTPException(422, str(exc)) from exc
    if not cita["id"]:
        raise HTTPException(500, "No se pudo agendar. No se registró nada.")
    return cita
