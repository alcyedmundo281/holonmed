"""Citas, altas y tics pedidos por chat: aquí es donde se escriben.

El chat redacta una propuesta y ahí termina. Aquí no entra ningún modelo ni
contenido nuevo: llega el identificador de una propuesta pendiente y el
nombre de quien la aprueba, y se escribe lo que se enseñó.

El nombre es **declarado, no autenticado**: sin identidad en el sistema, deja
constancia de quién dice haber aprobado, y no lo demuestra.

En cada ruta la propuesta se retira antes de escribir, para que una segunda
confirmación no escriba dos veces, y vuelve a quedar pendiente si no se
escribió nada. Entre una cosa y otra no hay ningún `await`.
"""

from datetime import datetime
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException

from ...models import (
    ConfirmarAlta,
    ConfirmarEnPaciente,
    HolonPaciente,
    PropuestaCita,
    PropuestaTic,
)
from ...services.propuestas import Identificable, Propuestas
from ..deps import AppContext, get_context
from ..historia import cargar_holon, huella

router = APIRouter(prefix="/api", tags=["confirmaciones"])

P = TypeVar("P", bound=Identificable)


def _pendiente(propuestas: Propuestas[P], propuesta_id: str) -> P:
    propuesta = propuestas.ver(propuesta_id)
    if propuesta is None:
        raise HTTPException(
            404,
            "Esa propuesta no está pendiente: no existe, ya se confirmó o el "
            "servidor se reinició. Revisa el registro antes de pedirla otra vez.",
        )
    return propuesta


def _mismo_paciente(
    ctx: AppContext, propuesta: PropuestaCita | PropuestaTic, paciente_id: str
) -> HolonPaciente:
    if propuesta.paciente_id != paciente_id:
        raise HTTPException(409, "La propuesta es de otro paciente.")
    holon = ctx.pacientes.obtener(paciente_id)
    if holon is None:
        raise HTTPException(409, "El paciente ya no está dado de alta.")
    return holon


@router.post("/citas/confirmar", status_code=201)
async def confirmar_cita(
    confirmacion: ConfirmarEnPaciente, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    propuesta = _pendiente(ctx.propuestas_cita, confirmacion.propuesta_id)
    _mismo_paciente(ctx, propuesta, confirmacion.paciente_id)
    fecha = datetime.fromisoformat(propuesta.fecha)
    if fecha <= datetime.now():
        ctx.propuestas_cita.retirar(propuesta.propuesta_id)
        raise HTTPException(409, "La fecha propuesta ya pasó. Pide la cita otra vez.")

    ctx.propuestas_cita.retirar(propuesta.propuesta_id)
    cita_id = ctx.agenda.registrar(
        propuesta.paciente_id, fecha, propuesta.motivo, confirmacion.confirmado_por
    )
    if not cita_id:
        ctx.propuestas_cita.guardar(propuesta)
        raise HTTPException(500, "No se pudo agendar. No se registró nada.")
    return {
        "id": cita_id,
        "fecha": propuesta.fecha,
        "motivo": propuesta.motivo,
        "confirmado_por": confirmacion.confirmado_por,
    }


@router.post("/pacientes/confirmar", status_code=201)
async def confirmar_alta(
    confirmacion: ConfirmarAlta, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    propuesta = _pendiente(ctx.propuestas_paciente, confirmacion.propuesta_id)

    ctx.propuestas_paciente.retirar(propuesta.propuesta_id)
    creado = ctx.pacientes.crear(
        {
            "nombre": propuesta.nombre,
            "alta_confirmada_por": confirmacion.confirmado_por,
        }
    )
    if not creado:
        ctx.propuestas_paciente.guardar(propuesta)
        raise HTTPException(500, "No se pudo dar de alta. No se registró nada.")
    return {
        "id": creado["id"],
        "nombre": creado["nombre"],
        "confirmado_por": confirmacion.confirmado_por,
    }


@router.post("/tics/confirmar", status_code=201)
async def confirmar_tic(
    confirmacion: ConfirmarEnPaciente, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    """Guarda el tic propuesto. **No ratifica sus infones**: siguen en potencia."""
    propuesta = _pendiente(ctx.propuestas_tic, confirmacion.propuesta_id)
    holon = _mismo_paciente(ctx, propuesta, confirmacion.paciente_id)
    # La inferencia, Φ y la duda se calcularon contra la historia de entonces.
    # Si cambió, escribirlos ahora afirmaría algo que ya nadie ha calculado.
    if huella(cargar_holon(ctx, holon)) != propuesta.huella_historia:
        ctx.propuestas_tic.retirar(propuesta.propuesta_id)
        raise HTTPException(
            409,
            "La historia del paciente cambió desde la propuesta. No se registró "
            "nada: pide el procesamiento otra vez.",
        )

    ctx.propuestas_tic.retirar(propuesta.propuesta_id)
    tic = propuesta.tic.model_copy(
        deep=True, update={"actor": confirmacion.confirmado_por}
    )
    tic_id = ctx.tics.guardar(tic)
    if not tic_id:
        ctx.propuestas_tic.guardar(propuesta)
        raise HTTPException(500, "No se pudo guardar. No se registró nada.")
    return {"tic_id": tic_id, "confirmado_por": confirmacion.confirmado_por}
