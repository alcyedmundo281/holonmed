"""Descarga de documentos generados (recetas, informes)."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..deps import AppContext, get_context

router = APIRouter(prefix="/api", tags=["documentos"])


@router.get("/documentos/{nombre}")
async def descargar(nombre: str, ctx: AppContext = Depends(get_context)):
    ruta = ctx.recetas.ruta_documento(nombre)
    if not ruta:
        raise HTTPException(404, "Documento no encontrado")
    return FileResponse(ruta, media_type="application/pdf", filename=ruta.name)
