"""Emisión de recetas: el único sitio donde una receta se escribe.

El chat redacta una propuesta y ahí termina. Aquí no entra ningún modelo ni
contenido nuevo: llega el identificador de una propuesta pendiente y el
nombre de quien la aprueba, y se escribe exactamente lo que se enseñó.

El nombre es **declarado, no autenticado**: sin identidad en el sistema, deja
constancia de quién dice haber aprobado, y no lo demuestra.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ...models import ConfirmarReceta, OrigenTic, ResultadoTic
from ..deps import AppContext, get_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["recetas"])


@router.post("/recetas/confirmar", status_code=201)
async def confirmar_receta(
    confirmacion: ConfirmarReceta, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    propuesta = ctx.propuestas_receta.ver(confirmacion.propuesta_id)
    if propuesta is None:
        raise HTTPException(
            404,
            "Esa propuesta no está pendiente: no existe, ya se confirmó o el "
            "servidor se reinició. Revisa el historial antes de pedirla otra vez.",
        )
    if propuesta.paciente_id != confirmacion.paciente_id:
        raise HTTPException(409, "La propuesta es de otro paciente.")

    # Se retira antes de escribir: una segunda confirmación no puede emitir
    # la misma receta dos veces. Entre esto y el final no hay ningún `await`.
    ctx.propuestas_receta.retirar(propuesta.propuesta_id)
    items = [item.model_dump() for item in propuesta.items]

    try:
        ruta = ctx.recetas.generar(items, propuesta.paciente_nombre)
    except Exception as exc:  # noqa: BLE001 — todavía no hay nada registrado
        # Sólo la clase: el mensaje de un OSError lleva la ruta, y la ruta
        # lleva el nombre del paciente.
        logger.error("Falló la generación del PDF: %s", type(exc).__name__)
        ruta = None
    if not ruta:
        ctx.propuestas_receta.guardar(propuesta)
        raise HTTPException(500, "No se pudo generar el PDF. No se registró nada.")

    # La receta entra en la historia como un tic de origen `farmacia`: un
    # fármaco prescrito es parte del registro clínico, y su ausencia rompe la
    # conciliación de la medicación en la visita siguiente.
    resumen = ", ".join(f"{i.farmaco} {i.concentracion}".strip() for i in propuesta.items)
    tic_id = ctx.tics.guardar(
        ResultadoTic(
            paciente_id=propuesta.paciente_id,
            texto_original=propuesta.texto_original,
            origen=OrigenTic.FARMACIA,
            actor=confirmacion.confirmado_por,
            skill_activa="receta",
            resumen=f"Receta: {resumen}",
        )
    )
    if not tic_id:
        ruta.unlink(missing_ok=True)
        ctx.propuestas_receta.guardar(propuesta)
        raise HTTPException(
            500, "No se pudo registrar la receta en la historia. No se emitió."
        )

    documento_id = ctx.documentos.registrar(
        propuesta.paciente_id,
        tipo="receta",
        archivo=ruta.name,
        datos={
            "items": items,
            "indicaciones": propuesta.indicaciones_generales,
            "confirmado_por": confirmacion.confirmado_por,
        },
        tic_id=tic_id,
    )
    if not documento_id:
        raise HTTPException(
            500,
            f"La receta quedó en la historia (tic {tic_id}) pero no se registró "
            "el documento. No la emitas otra vez.",
        )

    return {
        "url": f"/api/documentos/{ruta.name}",
        "items": items,
        "tic_id": tic_id,
        "confirmado_por": confirmacion.confirmado_por,
        "aviso": "Borrador sin validez hasta que lo firmes.",
    }
