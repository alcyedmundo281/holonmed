"""Lo que el laboratorio trae: qué responde una pregunta y qué abre otra.

LA REGLA
--------
    resultado CON orden  ──►  evidencia de la hipótesis que lo pidió
    resultado SIN orden  ──►  infón igual, pero PROBLEMA NUEVO en la lista

**Nada se descarta.** Lo que cambia no es si entra, sino de qué es
evidencia.

POR QUÉ NO ES LO MISMO
----------------------
Un resultado que alguien pidió **responde** a una pregunta: existe porque
una hipótesis lo necesitaba, y por eso cuenta como evidencia de ella. Uno
que nadie pidió **abre** una: nadie lo estaba buscando, así que no confirma
ni refuta la hipótesis activa —no fue elegido para ponerla a prueba— y lo
que hace es señalar algo que no estaba en la lista.

Meter el segundo en el numerador de Bayes sería contar como prueba de una
hipótesis un dato recogido para otra cosa. Y descartarlo sería peor: es
exactamente el problema que Weed encontraba disperso por la historia sin
que nadie lo hubiera listado.

LA SERENDIPIA VA A LA LISTA DE PROBLEMAS
-----------------------------------------
Es Weed literal: cuando aparece un problema nuevo, va a la lista. Su queja
en el Grand Rounds era encontrar rastros de problemas que nadie había
anotado —electrolitos pedidos a diario en una paciente ingresada por un
ictus— y no poder saber qué se estaba tratando.

POR QUÉ NO HACE FALTA SABER SI EL VALOR ES ANORMAL
---------------------------------------------------
Podría parecer que la serendipia exige un rango de referencia: reconocer
que el potasio está alto. No hace falta, y por una razón que ya está en el
sistema: el extractor **se niega a interpretar un número que ningún corte
declarado respalde**. Si un resultado llegó a producir un infón, es porque
algún protocolo sabía leerlo. Encaminar por orden es entonces completo.

Lo que sí falta —y es el ciclo 11— es que ese corte deje de ser binario.

LO QUE ESTE MÓDULO NO HACE
--------------------------
No crea órdenes ni decide si una orden estaba justificada. Recibe las que
hay y dice a dónde va cada resultado. Es puro: sin red y sin base.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class Destino(str, Enum):
    """Qué papel juega un resultado en el razonamiento."""

    EVIDENCIA = "evidencia"
    PROBLEMA_NUEVO = "problema_nuevo"


@dataclass(frozen=True)
class OrdenPendiente:
    """Lo mínimo de una orden para poder emparejarla con un resultado.

    Se pasa esto y no la `Orden` entera porque el núcleo no habla con la
    base, y porque emparejar no necesita la dosis ni el prescriptor.
    """

    orden_id: str
    termino: str
    codigo: str | None = None
    sistema: str | None = None
    concepto_id: int | None = None


@dataclass(frozen=True)
class Encaminamiento:
    """A dónde va un resultado, y por qué.

    La razón viaja siempre, también cuando encaja: quien audite mañana
    necesita saber por qué este potasio contó como prueba y aquél abrió un
    problema, y «porque sí» no es auditable.
    """

    destino: Destino
    razon: str
    orden_id: str | None = None

    @property
    def cuenta_como_evidencia(self) -> bool:
        return self.destino is Destino.EVIDENCIA


def _normalizar(texto: str) -> str:
    """Sin tildes, sin mayúsculas, sin espacios de más.

    El emparejamiento por término es el último recurso y tiene que ser
    generoso con la ortografía: un resultado que dice «Potasio serico» y una
    orden que dice «Potasio sérico» son la misma petición.
    """
    plano = unicodedata.normalize("NFKD", texto.lower())
    sin_tildes = "".join(c for c in plano if not unicodedata.combining(c))
    return " ".join(sin_tildes.split())


def encaminar(
    termino: str,
    ordenes: Sequence[OrdenPendiente],
    codigo: str | None = None,
    sistema: str | None = None,
    concepto_id: int | None = None,
) -> Encaminamiento:
    """¿Este resultado responde a una orden, o abre un problema?

    Se empareja en tres pasos, del más fuerte al más débil: por concepto,
    por código dentro de su sistema, y por término normalizado. El orden
    importa —el concepto es identidad y el término es una cadena— y bajar
    directamente al término emparejaría cosas que sólo se parecen.
    """
    if concepto_id is not None:
        for orden in ordenes:
            if orden.concepto_id == concepto_id:
                return Encaminamiento(
                    Destino.EVIDENCIA,
                    f"Responde a la orden {orden.orden_id}: mismo concepto.",
                    orden.orden_id,
                )

    if codigo:
        for orden in ordenes:
            if orden.codigo == codigo and orden.sistema == sistema:
                return Encaminamiento(
                    Destino.EVIDENCIA,
                    f"Responde a la orden {orden.orden_id}: mismo código {codigo}.",
                    orden.orden_id,
                )

    objetivo = _normalizar(termino)
    for orden in ordenes:
        if _normalizar(orden.termino) == objetivo:
            return Encaminamiento(
                Destino.EVIDENCIA,
                f"Responde a la orden {orden.orden_id}: mismo término.",
                orden.orden_id,
            )

    return Encaminamiento(
        Destino.PROBLEMA_NUEVO,
        (
            f"«{termino}» no responde a ninguna orden de este paciente. No "
            "cuenta como prueba de la hipótesis activa —nadie lo pidió para "
            "ponerla a prueba— y entra en la lista de problemas, que es donde "
            "va lo que aparece sin que nadie lo buscara."
        ),
    )


@dataclass(frozen=True)
class Reparto:
    """Cómo quedó una tanda de resultados.

    Se devuelven las dos listas y no sólo la de evidencia porque la de
    problemas nuevos es la que hay que enseñar: es la que dice que apareció
    algo que nadie estaba mirando.
    """

    evidencia: tuple[str, ...] = ()
    problemas_nuevos: tuple[str, ...] = ()

    @property
    def hubo_serendipia(self) -> bool:
        return bool(self.problemas_nuevos)


def repartir(terminos: Sequence[str], ordenes: Sequence[OrdenPendiente]) -> Reparto:
    """Encamina una tanda entera. Atajo para el caso común."""
    evidencia: list[str] = []
    nuevos: list[str] = []
    for termino in terminos:
        if encaminar(termino, ordenes).cuenta_como_evidencia:
            evidencia.append(termino)
        else:
            nuevos.append(termino)
    return Reparto(tuple(evidencia), tuple(nuevos))
