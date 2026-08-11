"""Rutas del grafo clínico.

Lo que distingue estas consultas de una búsqueda normal es que aprovechan
la jerarquía: preguntar por «enfermedad pancreática» encuentra hallazgos
codificados como hiperlipasemia sin que nadie haya escrito esa relación en
la consulta.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import AppContext, get_context

router = APIRouter(prefix="/api/grafo", tags=["grafo"])


@router.get("/paciente/{paciente_id}")
async def subgrafo_paciente(
    paciente_id: str,
    limite: int = Query(60, ge=1, le=300),
    ctx: AppContext = Depends(get_context),
):
    """Conceptos validados del paciente y los ancestros que los agrupan.

    No devuelve el grafo entero del vocabulario, sino la porción que este
    paciente ocupa. Los nodos de agrupación son los que explican por qué
    varios hallazgos sueltos pertenecen al mismo problema.
    """
    return ctx.grafo.vecindad(paciente_id, limite)


@router.get("/cohorte")
async def cohorte(
    codigo: str,
    sistema: str = "holonmed",
    ctx: AppContext = Depends(get_context),
):
    """Pacientes con algún hallazgo bajo una rama del grafo.

    Usa el cierre transitivo materializado: es un join indexado, no un
    recorrido recursivo por paciente.
    """
    filas = ctx.grafo.cohorte(codigo, sistema)
    return {
        "concepto": {"codigo": codigo, "sistema": sistema},
        "pacientes": [dict(f) for f in filas],
        "total": len(filas),
    }


@router.get("/concepto/{concepto_id}/ancestros")
async def ancestros(concepto_id: int, ctx: AppContext = Depends(get_context)):
    """Linaje completo de un concepto, de lo específico a lo general."""
    filas = ctx.grafo.ancestros(concepto_id)
    if not filas:
        raise HTTPException(404, "Concepto sin ancestros o inexistente")
    return [dict(f) for f in filas]


@router.get("/buscar")
async def buscar_concepto(
    q: str = Query(min_length=2),
    limite: int = Query(15, ge=1, le=50),
    ctx: AppContext = Depends(get_context),
):
    """Búsqueda de conceptos en el vocabulario cargado.

    Es la misma recuperación que usa el validador, expuesta para que se
    pueda inspeccionar qué encuentra el sistema y con qué puntuación.
    """
    candidatos = ctx.terminologia.buscar_candidatos(q, limite)
    return [
        {
            "concepto_id": c.concepto_id,
            "codigo": c.codigo,
            "sistema": c.sistema,
            "termino": c.termino,
            "score": round(c.score, 1),
        }
        for c in candidatos
    ]
