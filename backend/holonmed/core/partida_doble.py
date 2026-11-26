"""Dos libros, y la discrepancia entre ellos, que es el producto.

Weed sostiene que la medicina es un negocio de billones **sin sistema
contable**, y que sin poder auditar la calidad no hay medio de producirla.
La partida doble es lo que hace que una discrepancia sea estructuralmente
visible: no se puede maquillar un libro sin que el otro lo delate.

LOS DOS LIBROS
--------------
    LIBRO DE HOLONMED   lo que el validador de tres capas dio por bueno
    LIBRO DEL CLÍNICO   lo que una persona ratificó

No hubo que inventarlos: son los dos ejes que el ciclo 19 separó. `estado`
es juicio de la máquina; `acto` es la ratificación humana. Que estuvieran ya
en campos distintos es lo que permite conciliarlos.

LAS TRES SITUACIONES
--------------------
    ambos                    concuerda
    sólo HolonMed            problema pasado por alto
    sólo el clínico          fallo de cobertura del índice

La primera clase es la que Weed midió: en una sala de urgencias, con un
cuestionario de 32 preguntas y personal paramédico, los médicos se dejaban
**5.2 problemas por paciente**. Esa cifra hoy no la produce nadie.

UNA AUSENCIA NO ES UN PROBLEMA
------------------------------
La cifra de Weed cuenta problemas. Un «sin ictericia» validado que el
clínico no ratificó no es un problema que se le haya escapado, así que las
ausencias no entran en esa tasa: ni arriba ni abajo, porque dejar las
ratificadas en el denominador la diluiría. Siguen en los libros —se
revisaron, y en `tasa_sin_cobertura` miden al índice igual que lo
presente—, y la que no se recogió tiene su propia situación.

PENDIENTE NO ES PASADO POR ALTO
--------------------------------
Y ésta es la distinción que hace honesta la medida. Un hallazgo que nadie ha
mirado todavía no está pasado por alto: está pendiente. Sólo se puede decir
que se pasó por alto cuando **el clínico revisó ese tic y a ése no lo tocó**
—hay hermanos suyos con acto y él no—.

Contar los pendientes como pasados por alto inflaría la cifra con el trabajo
que aún no se ha hecho, y una tasa inflada se ignora a la semana.

POR QUÉ LOS LIBROS NO SE FUNDEN
--------------------------------
HolonMed no escribe en el expediente: propone. No es una concesión al
contrato —es lo que hace que esto funcione—. Si el sistema fundiera en
silencio sus hallazgos con el registro del clínico habría otra vez un solo
libro, y la discrepancia, que es el producto entero, dejaría de existir.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum

from ..models import EstadoInfon, Infon, Polaridad


class Situacion(str, Enum):
    """Dónde aparece un hallazgo."""

    CONCUERDA = "concuerda"
    SOLO_HOLONMED = "solo_holonmed"
    SOLO_CLINICO = "solo_clinico"
    PENDIENTE = "pendiente"
    AUSENCIA_SIN_RECOGER = "ausencia_sin_recoger"


@dataclass(frozen=True)
class Asiento:
    """Un hallazgo, y en qué libro está.

    `motivo` viaja siempre: una discrepancia sin razón no se puede llevar a
    una reunión, y la cifra sólo sirve si alguien puede discutir los casos.
    """

    termino: str
    situacion: Situacion
    motivo: str
    # El término no lleva la negación: sin esto una ausencia se lee afirmada.
    polaridad: Polaridad = Polaridad.PRESENTE

    @property
    def es_discrepancia(self) -> bool:
        return self.situacion in (Situacion.SOLO_HOLONMED, Situacion.SOLO_CLINICO)


@dataclass(frozen=True)
class Balance:
    """El cierre de la conciliación.

    `pendientes` se cuentan aparte de todo lo demás y no entran en ninguna
    tasa: son trabajo sin hacer, no desacuerdo.
    """

    asientos: tuple[Asiento, ...] = ()
    concuerdan: int = 0
    solo_holonmed: int = 0
    solo_clinico: int = 0
    pendientes: int = 0
    ausencias_sin_recoger: int = 0
    # Todas las ausencias revisadas, en cualquier situación.
    ausencias_conciliadas: int = 0
    por_termino: dict[str, int] = field(default_factory=dict)

    @property
    def conciliados(self) -> int:
        """Lo que el clínico ya revisó. El denominador de todas las tasas."""
        return (
            self.concuerdan
            + self.solo_holonmed
            + self.solo_clinico
            + self.ausencias_sin_recoger
        )

    @property
    def tasa_pasados_por_alto(self) -> float | None:
        """La cifra de Weed: qué fracción de lo revisado el clínico no anotó.

        Sólo sobre hallazgos presentes: una ausencia no es un problema.

        `None` cuando nadie ha revisado nada. No es cero: cero diría que no
        se pasó nada por alto, y lo que pasa es que no hay con qué compararlo.
        Es la misma distinción que `acuerdo_del_triaje()` y que la tasa de
        corrección del ciclo 19.
        """
        presentes = self.conciliados - self.ausencias_conciliadas
        if not presentes:
            return None
        return self.solo_holonmed / presentes

    @property
    def tasa_sin_cobertura(self) -> float | None:
        """Qué fracción escribió el clínico y el índice no supo ver.

        Mide al sistema, no al médico. Es la mitad que suele faltar en las
        evaluaciones de este tipo de herramientas.
        """
        if not self.conciliados:
            return None
        return self.solo_clinico / self.conciliados


def conciliar(tics: Mapping[str, Sequence[Infon]]) -> Balance:
    """Cierra los dos libros, agrupando por tic.

    Se recibe agrupado por tic y no una lista plana porque la señal que
    distingue pendiente de pasado por alto vive en el tic: **está revisado
    si alguno de sus infones tiene acto**. Un clínico que ratificó tres
    hallazgos de una nota y dejó el cuarto sin tocar lo dejó sin tocar; uno
    que no ha abierto la nota todavía no ha dejado nada.

    Calcularlo aquí y no pedirlo como parámetro evita el error de suponer:
    dar todo por revisado inflaría la cifra, y dar nada la dejaría siempre
    en cero.
    """
    asientos: list[Asiento] = []
    concuerdan = solo_holonmed = solo_clinico = pendientes = 0
    ausencias_sin_recoger = ausencias_conciliadas = 0
    por_termino: dict[str, int] = {}

    for suyos in tics.values():
        revisado = any(infon.acto for infon in suyos)

        for infon in suyos:
            lo_vio_holonmed = infon.estado is EstadoInfon.VALIDADO
            lo_hizo_suyo_el_clinico = infon.es_real
            ausente = infon.polaridad is Polaridad.AUSENTE
            previos = len(asientos)

            if lo_vio_holonmed and lo_hizo_suyo_el_clinico:
                concuerdan += 1
                asientos.append(
                    Asiento(
                        infon.termino,
                        Situacion.CONCUERDA,
                        "Lo vio el sistema y lo ratificó una persona.",
                    )
                )
            elif lo_vio_holonmed and revisado and ausente:
                ausencias_sin_recoger += 1
                asientos.append(
                    Asiento(
                        infon.termino,
                        Situacion.AUSENCIA_SIN_RECOGER,
                        (
                            "El sistema validó que consta ausente y el clínico "
                            "revisó esta nota sin recogerlo. No es un problema, "
                            "así que no cuenta como pasado por alto."
                        ),
                    )
                )
            elif lo_vio_holonmed and revisado:
                solo_holonmed += 1
                por_termino[infon.termino] = por_termino.get(infon.termino, 0) + 1
                asientos.append(
                    Asiento(
                        infon.termino,
                        Situacion.SOLO_HOLONMED,
                        (
                            "El sistema lo validó y el clínico revisó esta nota "
                            "sin recogerlo. Es un problema pasado por alto, y se "
                            "PROPONE: HolonMed no escribe en el expediente."
                        ),
                    )
                )
            elif lo_vio_holonmed:
                pendientes += 1
                asientos.append(
                    Asiento(
                        infon.termino,
                        Situacion.PENDIENTE,
                        (
                            "Nadie ha abierto esta nota todavía. Pendiente no es "
                            "pasado por alto, y contarlo como tal inflaría la "
                            "cifra con trabajo que aún no se ha hecho."
                        ),
                    )
                )
            elif lo_hizo_suyo_el_clinico:
                solo_clinico += 1
                asientos.append(
                    Asiento(
                        infon.termino,
                        Situacion.SOLO_CLINICO,
                        (
                            "Lo ratificó una persona y el validador no lo dio por "
                            "bueno. Mide al índice, no al médico: es cobertura "
                            "que falta."
                        ),
                    )
                )

            if len(asientos) > previos and ausente:
                asientos[-1] = replace(asientos[-1], polaridad=Polaridad.AUSENTE)
                if asientos[-1].situacion is not Situacion.PENDIENTE:
                    ausencias_conciliadas += 1

    return Balance(
        asientos=tuple(asientos),
        concuerdan=concuerdan,
        solo_holonmed=solo_holonmed,
        solo_clinico=solo_clinico,
        pendientes=pendientes,
        ausencias_sin_recoger=ausencias_sin_recoger,
        ausencias_conciliadas=ausencias_conciliadas,
        por_termino=por_termino,
    )
