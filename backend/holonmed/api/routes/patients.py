"""Gestión de pacientes y agenda."""

from fastapi import APIRouter, Depends, HTTPException

from ...models import CitaCreate, PacienteCreate
from ..deps import AppContext, get_context

router = APIRouter(prefix="/api", tags=["pacientes"])


@router.get("/pacientes")
async def listar(ctx: AppContext = Depends(get_context)):
    return ctx.pacientes.listar()


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
    return ctx.agenda.agendar(datos.paciente_id, datos.fecha, datos.motivo)
