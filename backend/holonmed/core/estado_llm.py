"""¿Se puede decir que el modelo local está conectado?

Función pura: recibe lo que se observó en el servidor de modelos y devuelve
uno de cuatro estados. La regla que importa es que `conectado` exige haber
leído la lista de modelos y haber encontrado en ella todos los configurados.
Cualquier otra cosa —no responder, responder algo ilegible— cae en un estado
distinto, nunca en el verde.

`conectado` significa que el servidor responde y ofrece los modelos. No
certifica que estén cargados en memoria ni que vayan a generar bien: LM
Studio, por ejemplo, puede listar modelos que cargará al primer uso.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

EstadoModelo = Literal["conectado", "falta_modelo", "sin_conexion", "sin_comprobar"]


@dataclass(frozen=True)
class DiagnosticoModelo:
    estado: EstadoModelo
    #: Modelos configurados que el servidor no ofrece. Vacío cuando no se
    #: pudo leer la lista: no saber qué hay no es saber que falta.
    faltantes: list[str]


def _nombre_completo(modelo: str, backend: str) -> str:
    """En Ollama, un nombre sin etiqueta significa `:latest` y nada más.

    Comparar sólo lo anterior a los dos puntos daría por instalado
    `gemma2:9b` teniendo `gemma2:2b`. En un servidor compatible con OpenAI
    el identificador es opaco y se compara tal cual.
    """
    if backend == "ollama" and ":" not in modelo.rsplit("/", 1)[-1]:
        return f"{modelo}:latest"
    return modelo


def diagnosticar_modelo(
    *,
    responde: bool,
    modelos: list[str] | None,
    requeridos: Iterable[str],
    backend: str,
) -> DiagnosticoModelo:
    """`modelos` es `None` si no se pudo leer la lista."""
    if not responde:
        return DiagnosticoModelo("sin_conexion", [])
    if modelos is None:
        return DiagnosticoModelo("sin_comprobar", [])

    ofrecidos = {_nombre_completo(m, backend) for m in modelos}
    faltantes = sorted(
        {m for m in requeridos if _nombre_completo(m, backend) not in ofrecidos}
    )
    return DiagnosticoModelo("falta_modelo" if faltantes else "conectado", faltantes)
