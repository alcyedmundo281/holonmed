"""El holon anidado: un todo que es parte de un todo mayor.

Koestler acuñó «holon» para lo que es a la vez entero y parte. El sistema
llevaba el nombre desde el principio y sólo tenía un nivel: `HolonPaciente`
era la historia entera creciendo por absorción de infones, sin jerarquía.

LA ESCALERA
-----------
    infones             componen ──►  historia clínica   PRIMARIO
    + la historia       componen ──►  notas clínicas     SECUNDARIOS
    + todo lo anterior  componen ──►  epicrisis          FINAL

LA EVOLUCIÓN NO ES UN HOLON
----------------------------
Es donde entran infones nuevos, y por eso importa, pero no es un todo: no
sintetiza nada. Un holon secundario nace justamente para recoger las
evoluciones que se acumularon desde el anterior. Contarlas como holones
haría de cada nota suelta una síntesis, que es lo contrario de lo que Weed
pide cuando exige notas tituladas y numeradas.

LA COMPOSICIÓN SE DERIVA, NO SE ALMACENA
-----------------------------------------
Qué compone cada holon es función de la secuencia del episodio, y la
secuencia es inmutable: se añade, no se reescribe. Guardarla en una tabla
de enlace crearía una segunda fuente de verdad que un día diverge de la
primera, y el compromiso del sistema es que el estado en el tic *n* sea
recomputable desde los tics 1..*n*.

Es la decisión contraria a la del ordinal —`clínica-2` sí se almacena—, y
la diferencia tiene razón: el ordinal es **identidad** y se cita, así que no
puede recalcularse nunca; la composición es **estructura** y se recalcula
sin que nadie lo note.

LA CONSERVACIÓN
---------------
Reconstruir el holon final desde sus holones tiene que dar lo mismo que
reconstruirlo desde los infones de todo el episodio. Si no da lo mismo, algo
se perdió por el camino, y el sistema **lo dice en vez de elegir una de las
dos rutas**. Callarlo dejaría una epicrisis que omite hallazgos sin avisar,
que es la peor forma del error en este dominio.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from ..models import TipoNota


class Nivel(str, Enum):
    """Dónde está un holon en la escalera."""

    PRIMARIO = "primario"
    SECUNDARIO = "secundario"
    FINAL = "final"


# Qué tipo de documento produce qué nivel. La evolución no aparece a
# propósito: aporta infones, no síntesis.
NIVELES: dict[TipoNota, Nivel] = {
    TipoNota.BASE: Nivel.PRIMARIO,
    TipoNota.CLINICA: Nivel.SECUNDARIO,
    TipoNota.EPICRISIS: Nivel.FINAL,
}


def nivel_de(tipo: TipoNota) -> Nivel | None:
    """El nivel de un documento, o `None` si no es un holon.

    `None` para la evolución no es un hueco: es la respuesta correcta, y
    devolver un nivel por defecto la convertiría en una síntesis que no es.
    """
    return NIVELES.get(tipo)


@dataclass(frozen=True)
class Documento:
    """Un tic del episodio, reducido a lo que la composición necesita.

    Se pasa esto y no el `ResultadoTic` entero porque el núcleo no habla con
    la base: quien construya la lista decide de dónde la saca.
    """

    tic_id: str
    tipo: TipoNota
    infones: tuple[str, ...] = ()
    ordinal: int | None = None


@dataclass(frozen=True)
class HolonCompuesto:
    """Un holon con lo que lo compone: holones debajo, e infones propios.

    `infones_propios` son los que entraron desde el holon anterior —las
    evoluciones acumuladas más los del propio documento—. `compone` son los
    holones que quedan dentro de él.
    """

    tic_id: str
    nivel: Nivel
    ordinal: int | None = None
    compone: tuple[str, ...] = ()
    infones_propios: tuple[str, ...] = ()

    @property
    def etiqueta(self) -> str:
        if self.nivel is Nivel.SECUNDARIO:
            return f"clínica-{self.ordinal}" if self.ordinal else "clínica-(sin numerar)"
        return self.nivel.value


def componer(documentos: Sequence[Documento]) -> list[HolonCompuesto]:
    """La escalera de holones de un episodio, en orden.

    Cada holon recoge los infones acumulados desde el holon anterior —que es
    para lo que nace— y referencia a todos los holones que lo preceden. La
    epicrisis los contiene a todos, y por eso es el final y no uno más.
    """
    holones: list[HolonCompuesto] = []
    pendientes: list[str] = []
    previos: list[str] = []

    for documento in documentos:
        nivel = nivel_de(documento.tipo)
        if nivel is None:
            # Una evolución no cierra nada: deja sus infones esperando al
            # siguiente holon, que es quien los sintetiza.
            pendientes.extend(documento.infones)
            continue

        propios = tuple(pendientes) + tuple(documento.infones)
        holones.append(
            HolonCompuesto(
                tic_id=documento.tic_id,
                nivel=nivel,
                ordinal=documento.ordinal,
                compone=tuple(previos),
                infones_propios=propios,
            )
        )
        pendientes = []
        previos = [*previos, documento.tic_id]

    return holones


@dataclass(frozen=True)
class Conservacion:
    """Si las dos rutas de reconstrucción coinciden, y qué falta si no.

    `huerfanos` son infones que existen en el episodio y no llegaron a
    ningún holon: entraron en evoluciones posteriores al último holon y
    nadie los ha sintetizado todavía. **No es un error** —es el estado
    normal entre dos notas clínicas— y por eso se cuentan aparte de la
    divergencia.
    """

    coincide: bool
    razon: str
    huerfanos: tuple[str, ...] = ()
    perdidos: tuple[str, ...] = ()

    @property
    def hay_pendientes(self) -> bool:
        return bool(self.huerfanos)


def conciliar(
    documentos: Sequence[Documento], holones: Sequence[HolonCompuesto]
) -> Conservacion:
    """¿Da lo mismo bajar por los holones que recorrer todos los infones?

    Si no da lo mismo, se dice cuáles se perdieron. Elegir una de las dos
    rutas en silencio dejaría una epicrisis que omite hallazgos sin avisar.
    """
    todos = [infon for documento in documentos for infon in documento.infones]
    en_holones = [infon for holon in holones for infon in holon.infones_propios]

    perdidos = tuple(i for i in todos if i not in set(en_holones))

    # Lo que quedó tras el último holon está pendiente de síntesis, no
    # perdido. Se separa mirando dónde cae el último holon en la secuencia.
    ultimo = -1
    for indice, documento in enumerate(documentos):
        if nivel_de(documento.tipo) is not None:
            ultimo = indice
    posteriores = {
        infon for documento in documentos[ultimo + 1 :] for infon in documento.infones
    }
    huerfanos = tuple(i for i in perdidos if i in posteriores)
    perdidos = tuple(i for i in perdidos if i not in posteriores)

    if perdidos:
        return Conservacion(
            coincide=False,
            razon=(
                f"{len(perdidos)} infones del episodio no están en ningún holon "
                "y no son posteriores al último. Reconstruir por holones daría "
                "menos que recorrer los infones, y la diferencia se perdería "
                "en silencio."
            ),
            huerfanos=huerfanos,
            perdidos=perdidos,
        )

    if huerfanos:
        return Conservacion(
            coincide=True,
            razon=(
                f"{len(huerfanos)} infones esperan al próximo holon. Es el "
                "estado normal entre dos notas clínicas, no una pérdida."
            ),
            huerfanos=huerfanos,
        )

    return Conservacion(coincide=True, razon="Las dos rutas dan lo mismo.")
