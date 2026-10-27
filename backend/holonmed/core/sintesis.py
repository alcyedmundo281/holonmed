"""El holon de fondo, y cuándo se imprime.

Esto era dos ciclos —«`resumen_vivo` vivo» y «la nota clínica firmada»— y
son dos estados de un mismo mecanismo.

EL FONDO
--------
Tras la validación de cada infón, HolonMed genera **en cada tic** un holon
secundario que incorpora los nuevos. Corre por debajo y por eso puede estar
siempre al día sin molestar a nadie.

**No lleva fecha ni firma.** No afirma el estado del paciente en un
instante: afirma el estado *ahora*, y se reescribe. Weed es implacable con
la nota escrita el domingo por la mañana —una nota cuyo sello de tiempo no
corresponde a un evento es ficción— y el fondo no tiene sello, así que no
puede mentir.

LA IMPRESIÓN
------------
Cuando las cosas cambian, el fondo se imprime en el presente real para que
el médico actualice su conocimiento del paciente. Eso sí es un documento:
`clínica-N`, con ordinal, fecha y firma.

Y el disparo importa tanto como la nota. Weed pide que la lista de problemas
se mantenga al día y es lo único en lo que exige ser despiadado; el volumen
es válvula secundaria y, cuando dispara él, **la nota lo dice**. Que se note
la diferencia es la mitad del valor: una síntesis que nació porque se llenó
un buffer no fecha nada que le pasara al paciente.

VA POR PROBLEMA
---------------
Es la queja central de Weed. «Doing well» no significa nada en un paciente
con artritis, insuficiencia cardíaca, azotemia, cadera rota e infección de
oído: quien lo escribió quería decir que le mejoró lo suyo. Cada problema
lleva su punto de vista del paciente, su dato objetivo y su siguiente paso,
en ese orden —«sintomáticamente y objetivamente», empezando siempre por el
punto de vista del paciente—.

Y el orden lo da la procedencia del ciclo 18, que ya sabe cuál es cuál. Sin
ella habría que adivinarlo del texto, que es justo lo que el sistema no
hace.

LO QUE ESTE MÓDULO NO HACE
--------------------------
No redacta prosa ni llama al modelo: organiza infones ya validados en
bloques y decide si toca imprimir. La redacción es otra pieza; ésta es la
que garantiza que ningún problema se quede fuera del documento.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

from ..models import Infon


class Motivo(str, Enum):
    """Por qué se imprimió una nota clínica.

    Se guarda con la nota y no sólo en un log: quien la lea mañana necesita
    saber si la pidió el paciente o el tamaño. Una síntesis disparada por
    volumen no fecha ningún evento clínico, y presentarla como si lo hiciera
    sería la ficción que Weed denuncia.
    """

    PROBLEMA_NUEVO = "problema_nuevo"
    PROBLEMA_RESUELTO = "problema_resuelto"
    PROMOCION = "promocion"
    DUDA = "duda"
    VOLUMEN = "volumen"


# Los motivos que nacen de que al paciente le pasó algo. El volumen no está,
# y ésa es toda la distinción.
CLINICOS = frozenset(
    {Motivo.PROBLEMA_NUEVO, Motivo.PROBLEMA_RESUELTO, Motivo.PROMOCION, Motivo.DUDA}
)


@dataclass(frozen=True)
class Bloque:
    """Un problema, con lo que se sabe de él y hacia dónde va.

    El orden de los campos es el de Weed y no es estético: primero lo que el
    paciente cuenta, después lo que alguien comprobó, y sólo entonces qué
    sigue. Invertirlo hace que el dato objetivo tiña el relato.
    """

    problema: str
    subjetivo: tuple[str, ...] = ()
    objetivo: tuple[str, ...] = ()
    derivado: tuple[str, ...] = ()
    siguiente: str = ""

    @property
    def vacio(self) -> bool:
        return not (self.subjetivo or self.objetivo or self.derivado)


@dataclass(frozen=True)
class HolonDeFondo:
    """La síntesis viva. Sin fecha y sin firma, a propósito.

    `hasta_tic` dice hasta dónde incorporó, que es lo único temporal que
    lleva: no es un sello sobre el paciente sino sobre sí mismo, y sirve
    para saber si está al día.
    """

    bloques: tuple[Bloque, ...] = ()
    hasta_tic: str | None = None
    sin_sintetizar: tuple[str, ...] = ()

    @property
    def problemas(self) -> tuple[str, ...]:
        return tuple(bloque.problema for bloque in self.bloques)

    @property
    def al_dia(self) -> bool:
        """Nada quedó fuera. Es la condición de hecho del ciclo."""
        return not self.sin_sintetizar


def sintetizar(
    infones: Sequence[Infon],
    problemas: Sequence[str],
    hasta_tic: str | None = None,
) -> HolonDeFondo:
    """Organiza los infones por problema, en el orden de Weed.

    Un infón que no cae bajo ningún problema **no se descarta**: sale en
    `sin_sintetizar`. Perderlo en silencio sería la peor forma del error
    aquí, porque el fondo es lo que alimenta la nota impresa y lo que no
    esté en el fondo no llegará nunca al médico.
    """
    por_problema: dict[str, list[Infon]] = {problema: [] for problema in problemas}
    sueltos: list[str] = []

    for infon in infones:
        destino = _problema_de(infon, problemas)
        if destino is None:
            sueltos.append(infon.termino)
            continue
        por_problema[destino].append(infon)

    bloques = tuple(
        Bloque(
            problema=problema,
            subjetivo=tuple(
                i.texto_origen for i in suyos if i.procedencia == "subjetivo"
            ),
            objetivo=tuple(i.texto_origen for i in suyos if i.procedencia == "objetivo"),
            derivado=tuple(i.termino for i in suyos if i.procedencia == "derivado"),
        )
        for problema, suyos in por_problema.items()
    )

    return HolonDeFondo(
        bloques=bloques,
        hasta_tic=hasta_tic,
        sin_sintetizar=tuple(sueltos),
    )


def _problema_de(infon: Infon, problemas: Sequence[str]) -> str | None:
    """A qué problema pertenece un infón.

    Se empareja por término y por linaje: un hallazgo cuelga del problema
    que lo nombra o del que es su padre en el grafo. No se adivina del
    texto, que es lo que el sistema entero existe para no hacer.
    """
    candidatos = {infon.termino, infon.linaje_clinico}
    for problema in problemas:
        if problema in candidatos:
            return problema
    return None


@dataclass(frozen=True)
class Impresion:
    """Si toca imprimir, y por qué.

    `motivos` en plural porque pueden coincidir varios en el mismo tic, y
    quedarse con uno perdería información que el clínico usa: no es lo mismo
    «apareció un problema» que «apareció un problema Y otro se promovió».
    """

    imprime: bool
    motivos: tuple[Motivo, ...] = ()
    razon: str = ""

    @property
    def la_pidio_el_paciente(self) -> bool:
        """Si algún motivo es clínico. Si no, la pidió el tamaño."""
        return any(motivo in CLINICOS for motivo in self.motivos)


def decidir(
    problemas_antes: Iterable[str],
    problemas_ahora: Iterable[str],
    promovidos: Iterable[str] = (),
    dudas: Iterable[str] = (),
    infones_sin_imprimir: int = 0,
    umbral_volumen: int = 0,
) -> Impresion:
    """¿Toca imprimir el fondo?

    El disparo primario es el cambio en la lista de problemas, que es lo
    único en lo que Weed exige ser despiadado. El volumen es la válvula
    secundaria, y sólo dispara si nadie más lo hizo: cuando hay motivo
    clínico, decir además «y el buffer estaba lleno» sería ruido.

    `umbral_volumen = 0` desactiva la válvula. Es el defecto porque un
    umbral inventado imprimiría notas que no fechan nada, y elegir el número
    es una decisión clínica que este módulo no puede tomar.
    """
    antes, ahora = set(problemas_antes), set(problemas_ahora)
    motivos: list[Motivo] = []
    detalles: list[str] = []

    if nuevos := sorted(ahora - antes):
        motivos.append(Motivo.PROBLEMA_NUEVO)
        detalles.append(f"apareció {_lista(nuevos)}")
    if idos := sorted(antes - ahora):
        motivos.append(Motivo.PROBLEMA_RESUELTO)
        detalles.append(f"se resolvió {_lista(idos)}")
    if promovidas := sorted(promovidos):
        motivos.append(Motivo.PROMOCION)
        detalles.append(f"pasó a diagnóstico {_lista(promovidas)}")
    if abiertas := sorted(dudas):
        motivos.append(Motivo.DUDA)
        detalles.append(f"la creencia dejó de sostenerse en {_lista(abiertas)}")

    if motivos:
        return Impresion(
            imprime=True,
            motivos=tuple(motivos),
            razon="La lista de problemas cambió: " + "; ".join(detalles) + ".",
        )

    if umbral_volumen and infones_sin_imprimir >= umbral_volumen:
        return Impresion(
            imprime=True,
            motivos=(Motivo.VOLUMEN,),
            razon=(
                f"Esta síntesis la pidió el tamaño y no el paciente: "
                f"{infones_sin_imprimir} hallazgos sin sintetizar. La lista de "
                "problemas no cambió."
            ),
        )

    return Impresion(
        imprime=False,
        razon="Nada cambió en la lista de problemas. El fondo sigue al día.",
    )


def _lista(nombres: Sequence[str]) -> str:
    if len(nombres) == 1:
        return f"«{nombres[0]}»"
    return ", ".join(f"«{n}»" for n in nombres[:-1]) + f" y «{nombres[-1]}»"
