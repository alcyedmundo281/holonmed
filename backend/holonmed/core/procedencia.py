"""De dónde sale un infón: quién lo asevera, no de qué instrumento salió.

LA REGLA
--------
    subjetivo   lo expresó el paciente
    objetivo    lo observó la experiencia del clínico, o es evidencia
                objetiva recogida por quien la produce
    derivado    no lo aseveró nadie: se sigue de otros infones

Weed pide la nota de evolución escrita «sintomáticamente y objetivamente»,
en ese orden, empezando siempre por el punto de vista del paciente. Esa
separación no es de estilo: es de procedencia, y sin registrarla la nota
mezcla lo que alguien contó con lo que alguien comprobó.

LO QUE CLASIFICA ES QUIÉN LO ASEVERA, NO EL INSTRUMENTO
--------------------------------------------------------
Una glucemia que el paciente refiere es **subjetiva**, aunque salga de un
glucómetro. Nadie vio el aparato, ni la lectura, ni si estaba calibrado:
es testimonio sobre un número. La misma cifra, medida en la consulta o
informada por el laboratorio, es objetiva.

Confundirlos tiene consecuencia directa: un valor referido no puede
comparase contra un punto de corte como si se hubiera medido, y un sistema
que los mezcle acabará auditando lógicamente una cifra que nadie vio.

EL EJE ES DEL INFÓN, NO DEL TIC
--------------------------------
Una nota de consulta contiene las dos clases en el mismo párrafo: «refiere
dolor epigástrico desde ayer» es subjetivo aunque lo teclee el médico, y
«abdomen blando, sin defensa» es objetivo. El tic tiene un origen; cada
infón dentro de él tiene su propia procedencia. Es el mismo error que ya se
deshizo con `tipo`, `origen` y `solicitante`.

HOLONMED NO ASEVERA
-------------------
El sistema no observa ni refiere: deduce. Lo que introduce es `derivado`, y
por eso `derivado_de` ya existía en el modelo. Un infón que HolonMed
presentara como objetivo estaría afirmando haber visto algo.
"""

from __future__ import annotations

from enum import Enum

from ..models import OrigenTic


class Procedencia(str, Enum):
    """Quién asevera un infón."""

    SUBJETIVO = "subjetivo"
    OBJETIVO = "objetivo"
    DERIVADO = "derivado"


# Qué puede aseverar cada actor. La tabla es la regla: está aquí, en el
# código, y no en una instrucción de prompt, porque el contrato dice que
# las condiciones de rechazo se implementan y se prueban.
#
# `consulta` y `enfermeria` son los únicos que pueden las dos, y no por
# privilegio: son los únicos que a la vez escuchan al paciente y exploran.
PERMITIDAS: dict[OrigenTic, frozenset[Procedencia]] = {
    # El paciente sólo puede aseverar su propio relato. Una cifra que trae
    # es su relato de una cifra.
    OrigenTic.PACIENTE: frozenset({Procedencia.SUBJETIVO}),
    # Un analizador no tiene síntomas.
    OrigenTic.LABORATORIO: frozenset({Procedencia.OBJETIVO}),
    OrigenTic.IMAGEN: frozenset({Procedencia.OBJETIVO}),
    OrigenTic.FARMACIA: frozenset({Procedencia.OBJETIVO}),
    OrigenTic.CONSULTA: frozenset({Procedencia.SUBJETIVO, Procedencia.OBJETIVO}),
    OrigenTic.ENFERMERIA: frozenset({Procedencia.SUBJETIVO, Procedencia.OBJETIVO}),
    # HolonMed no observa ni refiere: deduce.
    OrigenTic.HOLONMED: frozenset({Procedencia.DERIVADO}),
    # `otro` no declara nada de sí mismo, así que no se le concede nada:
    # ante un origen que no sabemos leer, el sistema se detiene en vez de
    # suponer el caso más permisivo.
    OrigenTic.OTRO: frozenset(),
}


def admite(origen: OrigenTic, procedencia: Procedencia) -> bool:
    return procedencia in PERMITIDAS.get(origen, frozenset())


def motivo_del_rechazo(origen: OrigenTic, procedencia: Procedencia) -> str:
    """Por qué este actor no puede aseverar así.

    Se explica en términos de la regla y no del código: quien lea esto está
    intentando registrar algo, y «no permitido» le manda a reintentar.
    """
    if origen is OrigenTic.PACIENTE and procedencia is Procedencia.OBJETIVO:
        return (
            "Lo que el paciente refiere es subjetivo aunque sea una cifra: una "
            "glucemia que trae de casa es su relato de una lectura que nadie "
            "verificó. Regístrela como subjetiva, o mídala."
        )
    if origen in (OrigenTic.LABORATORIO, OrigenTic.IMAGEN, OrigenTic.FARMACIA):
        return (
            f"«{origen.value}» no puede aseverar un hallazgo {procedencia.value}: "
            "informa lo que midió. Un analizador no tiene síntomas."
        )
    if origen is OrigenTic.HOLONMED:
        return (
            "HolonMed no observa ni refiere: deduce. Lo que introduzca es "
            "derivado, y tiene que decir de qué se sigue. Presentarlo como "
            "observado sería afirmar haber visto algo."
        )
    if origen is OrigenTic.OTRO:
        return (
            "El origen «otro» no declara qué clase de aseveración produce, así "
            "que no se le concede ninguna. Declare el actor real."
        )
    return f"«{origen.value}» no puede aseverar un hallazgo {procedencia.value}."


def clasificar_por_defecto(origen: OrigenTic) -> Procedencia | None:
    """La procedencia de un actor que sólo puede una, y `None` si puede varias.

    Existe para no obligar a declarar lo que no tiene alternativa: un
    resultado de laboratorio es objetivo y no hay nada que decidir. Devuelve
    `None` para consulta y enfermería **a propósito**: ahí sí hay que
    decidir, y elegir por ellos sería exactamente mezclar lo que alguien
    contó con lo que alguien comprobó.
    """
    posibles = PERMITIDAS.get(origen, frozenset())
    return next(iter(posibles)) if len(posibles) == 1 else None
