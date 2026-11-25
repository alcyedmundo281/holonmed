"""La página del tutorial para demostraciones públicas.

Sólo se registra en modo demo (`HOLONMED_MODO_DEMO=true`). La página escribe
tics, así que no debe quedar servida sobre la base donde se trabaja de verdad:
`scripts/demo.py` enciende el modo con una base temporal.

No añade ninguna operación: la página usa las rutas que ya existen, y el modelo
sigue detrás de la única puerta (`llm/client.py`).
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

PAGINA = Path(__file__).resolve().parents[1] / "static" / "tutorial.html"

router = APIRouter(tags=["demo"])


@router.get("/", include_in_schema=False)
async def raiz() -> RedirectResponse:
    return RedirectResponse("/tutorial")


@router.get("/tutorial", include_in_schema=False)
async def tutorial() -> FileResponse:
    # Sin caché: tras actualizar el repo, el navegador no debe presentar delante
    # del público la copia anterior de la página.
    return FileResponse(
        PAGINA,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
