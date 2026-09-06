"""La interfaz por la que entra todo: episodios y sus documentos.

Hasta aquí, la narrativa clínica entraba como texto suelto por un chat y lo
único que la clasificaba era quién la producía. Estas rutas son el contrato
por el que entra la secuencia de Weed con su forma:

    historia clínica
      evolución … evolución …
    clínica-1
      …
    epicrisis

QUÉ NO HACEN ESTAS RUTAS
------------------------
No reimplementan ninguna regla. Las cuatro de la secuencia viven en
`core.episodio` y las aplica el almacén, que es el único punto por el que se
puede pasar; aquí sólo se traduce un rechazo del almacén a un 409 con su
motivo. Una regla que viviera también en la ruta se saltaría desde la CLI.

LA HISTORIA CLÍNICA NO LA TECLEA EL MÉDICO
-------------------------------------------
Por eso `GET /base` no devuelve un formulario: devuelve **qué falta y a
quién pedírselo**. La solución de Weed para la fase 1 es cuestionario con
ramificación, enfermería entrenada y el propio paciente, y una lista de
huecos que nadie sabe quién llena se queda sin llenar.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core.base import cargar_todas, evaluar
from ...core.sintesis import decidir, sintetizar
from ...models import OrigenTic, TipoNota
from ..deps import AppContext, get_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["episodios"])


class AbrirEpisodio(BaseModel):
    paciente_id: str
    motivo: str = ""
    # Qué base se va a exigir. Se declara al abrir y no al cerrar: un
    # episodio atendido con la mínima no puede presentarse después como si
    # se hubiera hecho la comprehensiva.
    alcance_base: str = "comprehensiva"


class EscribirDocumento(BaseModel):
    texto: str = Field(min_length=1)
    tipo: TipoNota = TipoNota.EVOLUCION
    origen: OrigenTic = OrigenTic.CONSULTA
    actor: str | None = None


@router.post("/episodios", status_code=201)
async def abrir_episodio(
    peticion: AbrirEpisodio, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    """Abre un episodio. Todo lo demás cuelga de él."""
    episodio_id = ctx.episodios.abrir(
        peticion.paciente_id, peticion.motivo, peticion.alcance_base
    )
    if not episodio_id:
        raise HTTPException(500, "No se pudo abrir el episodio")
    return {"episodio_id": episodio_id, "paciente_id": peticion.paciente_id}


@router.get("/episodios/{paciente_id}")
async def listar_episodios(
    paciente_id: str, ctx: AppContext = Depends(get_context)
) -> list[dict[str, Any]]:
    return ctx.episodios.listar(paciente_id)


@router.get("/episodios/{episodio_id}/holones")
async def escalera(
    episodio_id: str, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    """La escalera de holones del episodio, con su conciliación.

    La conciliación viaja junto y no aparte: quien lee los holones es quien
    necesita saber si están completos.
    """
    return ctx.episodios.holones(episodio_id)


@router.get("/episodios/{episodio_id}/base")
async def estado_de_la_base(
    episodio_id: str,
    edad: int | None = None,
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    """Qué falta de la base definida, y **a quién pedírselo**.

    Devuelve el reparto por actor y no una lista plana porque «la base está
    incompleta» sin destinatario no es accionable: una lista de huecos que
    nadie sabe quién llena se queda sin llenar.

    Si la base condiciona ítems por edad y la edad no consta, no se elige:
    se dice que no se puede saber cuáles aplican.
    """
    episodios = ctx.episodios.listar_uno(episodio_id)
    if episodios is None:
        raise HTTPException(404, "No existe ese episodio")

    bases = cargar_todas(ctx.settings.base_dir)
    alcance = episodios.get("alcance_base") or "comprehensiva"
    base = next((b for b in bases.values() if b.alcance.value == alcance), None)
    if base is None:
        raise HTTPException(500, f"No hay ninguna base declarada con alcance «{alcance}»")

    cubiertos = ctx.episodios.terminos_del_episodio(episodio_id)
    estado = evaluar(base, cubiertos, edad)
    return {
        "base": base.titulo,
        "alcance": base.alcance.value,
        "completa": estado.completa,
        "razon": estado.razon,
        "faltan_por_quien": estado.faltan_por_quien,
    }


@router.get("/episodios/{episodio_id}/fondo")
async def holon_de_fondo(
    episodio_id: str, ctx: AppContext = Depends(get_context)
) -> dict[str, Any]:
    """El holon de fondo del episodio, y si toca imprimirlo.

    El fondo corre por debajo en cada tic y **no lleva fecha ni firma**: no
    afirma el estado del paciente en un instante, afirma el estado ahora.
    Leerlo no lo imprime.

    La decisión viaja con él porque quien lo consulta es quien va a
    imprimirlo, y separarlas dejaría que se imprimiera sin motivo.
    """
    if ctx.episodios.listar_uno(episodio_id) is None:
        raise HTTPException(404, "No existe ese episodio")

    paciente_id = ctx.episodios.paciente_de(episodio_id) or ""
    problemas = [p["termino"] for p in ctx.tics.lista_problemas(paciente_id)]
    infones = ctx.episodios.infones_del_episodio(episodio_id)

    fondo = sintetizar(infones, problemas)
    # Sin problemas previos con qué comparar, el primer fondo de un episodio
    # imprime por cada problema que aparece, que es lo correcto: todos son
    # nuevos.
    decision = decidir(problemas_antes=[], problemas_ahora=problemas)

    return {
        "bloques": [
            {
                "problema": b.problema,
                "subjetivo": list(b.subjetivo),
                "objetivo": list(b.objetivo),
                "derivado": list(b.derivado),
            }
            for b in fondo.bloques
        ],
        # Lo que no cayó bajo ningún problema. No se descarta: lo que no
        # esté en el fondo no llegará nunca al médico.
        "sin_sintetizar": list(fondo.sin_sintetizar),
        "al_dia": fondo.al_dia,
        "impresion": {
            "imprime": decision.imprime,
            "motivos": [m.value for m in decision.motivos],
            "razon": decision.razon,
            "la_pidio_el_paciente": decision.la_pidio_el_paciente,
        },
    }


@router.post("/episodios/{episodio_id}/documentos", status_code=201)
async def escribir_documento(
    episodio_id: str,
    peticion: EscribirDocumento,
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    """Escribe un documento en el episodio, con su tipo declarado.

    **Ningún documento se emite sin tipo**: el defecto es `evolucion` porque
    es el grueso del tráfico, pero es una declaración y no una suposición.

    Si la secuencia no lo admite —una evolución antes de la historia, una
    segunda historia, cualquier cosa en un episodio cerrado— el almacén lo
    rechaza y aquí sale un 409 con el motivo. El motivo importa: un rechazo
    sin razón se lee como un fallo del sistema y se reintenta.
    """
    estado = ctx.episodios.estado(episodio_id)
    if estado is None:
        raise HTTPException(404, "No existe ese episodio")

    from ...core.episodio import admite

    veredicto = admite(estado, peticion.tipo)
    if not veredicto.admitido:
        raise HTTPException(409, veredicto.motivo)

    holon = ctx.pacientes.obtener_o_efimero(ctx.episodios.paciente_de(episodio_id) or "")
    holon.linea_tiempo = ctx.tics.linea_tiempo(holon.paciente_id)
    resultado = await ctx.pipeline.ejecutar(peticion.texto, holon)
    resultado.episodio_id = episodio_id
    resultado.tipo = peticion.tipo
    resultado.origen = peticion.origen
    resultado.actor = peticion.actor

    tic_id = ctx.tics.guardar(resultado)
    if not tic_id:
        raise HTTPException(409, "El episodio no admitió el documento")

    resultado.tic_id = tic_id
    return {
        "tic_id": tic_id,
        "tipo": resultado.tipo.value,
        "ordinal_clinica": resultado.ordinal_clinica,
        "infones": len(resultado.infones),
    }


@router.post("/episodios/{episodio_id}/cerrar")
async def cerrar_episodio(
    episodio_id: str,
    firmante: str,
    ctx: AppContext = Depends(get_context),
) -> dict[str, Any]:
    """Cierra el episodio. Sólo la epicrisis lo cierra, y exige firma.

    La epicrisis es el único de los cuatro documentos que **sale de la
    institución**, y por eso es el único bajo aprobación humana nombrada
    obligatoria. Un episodio no se cierra por dejar de escribir.
    """
    if not firmante.strip():
        raise HTTPException(
            422,
            "La epicrisis sale de la institución y exige una firma con "
            "nombre. «Alguien la cerró» no se puede auditar.",
        )

    estado = ctx.episodios.estado(episodio_id)
    if estado is None:
        raise HTTPException(404, "No existe ese episodio")
    if estado.cerrado:
        raise HTTPException(409, "El episodio ya está cerrado")

    if not ctx.episodios.cerrar(episodio_id):
        raise HTTPException(500, "No se pudo cerrar el episodio")
    return {"episodio_id": episodio_id, "cerrado_por": firmante}
