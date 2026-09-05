"""Las reglas del episodio: qué documento puede escribirse y cuándo.

La secuencia canónica de un episodio es ésta, y no es una convención de
presentación sino la forma que Weed le dio a la acción médica:

    historia clínica
      evolución … evolución …
    clínica-1
      evolución … evolución …
    clínica-2
      …
    epicrisis

DE LA FORMA SE SIGUEN CUATRO REGLAS
-----------------------------------
1. **La historia abre, y abre una sola vez.** Es la base definida: si se
   pudiera escribir dos veces, la segunda cambiaría la lista de problemas
   sin que nadie lo hubiera advertido.
2. **La epicrisis cierra, y cierra una sola vez.** Un episodio cerrado no
   admite más documentos: si se pudiera seguir escribiendo, la epicrisis
   dejaría de ser una síntesis y pasaría a ser un documento más.
3. **Nada precede a la historia.** Una evolución antes de la base sería un
   hallazgo sin nadie a quien atribuírselo.
4. **Las notas clínicas van numeradas dentro del episodio.** Weed pide
   notas tituladas y numeradas, y `clínica-2` sólo significa algo respecto
   de `clínica-1`.

POR QUÉ ESTO ES CÓDIGO
----------------------
Son condiciones de rechazo, y el contrato dice dónde viven: implementadas y
probadas, no confiadas a una instrucción en un prompt. Una regla que un
modelo puede decidir saltarse no es una regla.

LO QUE ESTE MÓDULO NO HACE
--------------------------
No decide cuándo nace una nota clínica —eso es el ciclo 14— ni redacta
ninguna. Sólo dice si un documento **puede** escribirse aquí, y cuando no,
por qué. Es puro: no toca la base ni la red.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import TipoNota


@dataclass(frozen=True)
class EstadoEpisodio:
    """Lo que hay que saber de un episodio para decidir si admite un documento.

    Se pasa explícito en vez de leerse de la base porque el núcleo no habla
    con SQLite: es la misma frontera que respeta el resto de `core/`.
    """

    cerrado: bool = False
    tiene_historia: bool = False
    notas_clinicas: int = 0


@dataclass(frozen=True)
class Admision:
    """Si el documento entra, y si no, por qué no.

    `motivo` no es un mensaje de error para un log: es lo que se le enseña a
    quien intentó escribirlo. Un rechazo sin razón se lee como un fallo del
    sistema y se reintenta.
    """

    admitido: bool
    motivo: str = ""
    ordinal: int | None = None


def admite(estado: EstadoEpisodio, tipo: TipoNota) -> Admision:
    """¿Puede escribirse este documento en este episodio?

    Devuelve además el ordinal que le tocaría a una nota clínica, porque
    quien pregunta si puede escribirla es quien va a necesitarlo, y
    calcularlo aparte abriría la puerta a que los dos números difieran.
    """
    if estado.cerrado:
        return Admision(
            False,
            "El episodio está cerrado por su epicrisis. Un episodio cerrado no "
            "admite más documentos: si se pudiera seguir escribiendo, la "
            "epicrisis dejaría de ser una síntesis. Abra un episodio nuevo.",
        )

    if tipo is TipoNota.BASE:
        if estado.tiene_historia:
            return Admision(
                False,
                "Este episodio ya tiene su historia clínica. Una segunda "
                "cambiaría la lista de problemas sin que nadie lo advirtiera; "
                "lo que cambia después de la base se escribe como evolución.",
            )
        return Admision(True)

    if not estado.tiene_historia:
        return Admision(
            False,
            f"Este episodio no tiene todavía su historia clínica, y «{tipo.value}» "
            "no puede precederla: sería un hallazgo sin nadie a quien "
            "atribuírselo. La base define qué problemas puede haber.",
        )

    if tipo is TipoNota.CLINICA:
        return Admision(True, ordinal=estado.notas_clinicas + 1)

    if tipo is TipoNota.EPICRISIS:
        if estado.notas_clinicas == 0:
            return Admision(
                False,
                "No hay ninguna nota clínica que sintetizar. Una epicrisis que "
                "sólo resume evoluciones sueltas es el documento que Weed "
                "llamaba ficción: cierra sin que nadie haya cerrado nada.",
            )
        return Admision(True)

    return Admision(True)


def etiqueta(tipo: TipoNota, ordinal: int | None) -> str:
    """Cómo se nombra un documento en la historia.

    Sólo la nota clínica lleva número, y lo lleva siempre: una «clínica» sin
    ordinal no se puede citar, y citarla es para lo que Weed la numeraba.
    """
    if tipo is TipoNota.CLINICA:
        return f"clínica-{ordinal}" if ordinal else "clínica-(sin numerar)"
    return tipo.value
