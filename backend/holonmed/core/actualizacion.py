"""Potencia y acto: lo que el sistema propone y lo que un humano ratifica.

EL PRINCIPIO
------------
En cada tic, lo potencial es validado por el médico y **se vuelve presente
real**. Lo que el sistema propone es potencia; el acto es humano.

POR QUÉ HACE FALTA UN EJE NUEVO
--------------------------------
`EstadoInfon.VALIDADO` significa hoy «el validador de tres capas lo
confirmó»: ontología y lógica coinciden. Eso es juicio de la máquina, y es
un juicio bueno —tiene su traza, su score y su razón—, pero **no es una
ratificación**. Bajo el principio de potencia y acto sigue siendo potencial
hasta que alguien lo actualiza.

Meterlo en `EstadoInfon` habría fundido dos cosas que se leen distinto:
«el validador lo confirmó» y «un médico lo hizo suyo». Es la misma forma
que ya tienen `solicitante` y `prescriptor` en la orden, y `origen` frente a
`procedencia` en el infón: el juicio del sistema y la ratificación humana
nunca comparten campo.

EL BUCLE
--------
    tic real ──genera──► tic potencial ──acto──► nuevo tic real ──►

Y el potencial se genera **sobre lo que el médico aprobó**, no sobre lo que
el sistema cree. Un sistema que propusiera sobre sus propias conjeturas sin
ratificar acumularía error sin que nadie lo viera.

«CORREGIR» NO ES UN TERCER BOTÓN, ES EL PRODUCTO
-------------------------------------------------
Aceptar o rechazar mide poco: un contador de aciertos no dice en qué falla
el sistema. La corrección sí —dice qué término era el bueno, qué polaridad,
qué procedencia— y es la única fuente de esa medida.

Se registra aunque no decida nada, por el mismo argumento por el que
`triaje_coincide` se persiste aunque la competencia abductiva no vote: sin
registrar la discrepancia, la cifra que justificaría hacerle caso al sistema
no existe. Es además la partida doble del ciclo 16 en su forma más pequeña.

LO QUE ESTE MÓDULO NO HACE
--------------------------
No decide qué se ratifica ni redacta nada. Dice si un infón es real, quién
lo hizo real, y qué cambió al hacerlo. Es puro: sin red y sin base.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Acto(str, Enum):
    """Qué hizo el humano con lo que el sistema propuso.

    `RECHAZADO` no borra: el infón queda con su motivo, igual que el RUIDO
    del validador se muestra en vez de esconderse. Un sistema que oculta lo
    que se le rechazó no se puede auditar, y esta vez lo rechazado dice algo
    sobre el sistema y no sobre el paciente.
    """

    ACEPTADO = "aceptado"
    CORREGIDO = "corregido"
    RECHAZADO = "rechazado"


@dataclass(frozen=True)
class Actualizacion:
    """El acto que convirtió una potencia en presente real.

    `por` es un nombre, no un booleano: el contrato exige aprobación humana
    **nombrada**, y «alguien lo validó» no es auditable. Si algún día hay
    autenticación, sale del rol de quien firma; mientras tanto lo declara
    quien escribe, igual que `actor`.
    """

    acto: Acto
    por: str
    cuando: str
    # Qué cambió, cuando el acto fue corregir: {campo: [antes, después]}.
    # No es un registro de auditoría genérico —eso es otra pieza pendiente—
    # sino la materia prima de la tasa de corrección.
    cambios: dict[str, tuple[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.por.strip():
            raise ValueError(
                "Una actualización sin nombre no es una ratificación: el "
                "contrato exige aprobación humana nombrada, y «alguien lo "
                "validó» no se puede auditar."
            )
        if self.acto is Acto.CORREGIDO and not self.cambios:
            raise ValueError(
                "Una corrección sin decir qué cambió no mide nada, y medir es "
                "para lo que existe. Registre los campos corregidos."
            )
        if self.acto is not Acto.CORREGIDO and self.cambios:
            raise ValueError(
                f"Un acto «{self.acto.value}» no cambia nada, así que no puede "
                "traer cambios. Si hubo corrección, el acto es «corregido»."
            )

    @property
    def hace_real(self) -> bool:
        """Sólo aceptar y corregir actualizan. Rechazar deja la potencia sin acto."""
        return self.acto in (Acto.ACEPTADO, Acto.CORREGIDO)


def es_real(actualizacion: Actualizacion | None) -> bool:
    """Un infón que ningún humano actualizó nunca es real, sólo potencial.

    `None` es el caso de todo lo escrito hasta hoy y de todo lo que el
    sistema acaba de proponer. No es un defecto que rellenar: es el estado
    inicial correcto.
    """
    return actualizacion is not None and actualizacion.hace_real


def describir(actualizacion: Actualizacion | None) -> str:
    """Cómo se presenta el estado de un infón, sin sobreafirmar nunca.

    Es la condición del ciclo: **un infón que ningún humano actualizó no se
    presenta como real**. Decir «validado» a secas sería exactamente la
    confusión que este eje existe para deshacer.
    """
    if actualizacion is None:
        return "potencial: propuesto por el sistema, sin ratificar"
    if actualizacion.acto is Acto.RECHAZADO:
        return f"rechazado por {actualizacion.por}"
    if actualizacion.acto is Acto.CORREGIDO:
        campos = ", ".join(sorted(actualizacion.cambios))
        return f"real, corregido por {actualizacion.por} en {campos}"
    return f"real, aceptado por {actualizacion.por}"


@dataclass(frozen=True)
class TasaDeCorreccion:
    """Cuánto se equivoca el sistema, y en qué.

    `sin_actuar` se cuenta aparte y no como acierto: un infón que nadie miró
    no dice nada sobre el sistema. Meterlo en el denominador inventaría una
    tasa, que es el mismo error que `acuerdo_del_triaje()` evita con los tics
    sin competencia.
    """

    aceptados: int = 0
    corregidos: int = 0
    rechazados: int = 0
    sin_actuar: int = 0
    por_campo: dict[str, int] = field(default_factory=dict)

    @property
    def actuados(self) -> int:
        return self.aceptados + self.corregidos + self.rechazados

    @property
    def tasa(self) -> float | None:
        """Fracción de lo actuado que el humano no aceptó tal cual.

        `None` cuando nadie ha actuado todavía. No es cero: cero diría que
        el sistema no se equivocó nunca, y lo que pasa es que nadie ha
        mirado. Es la misma distinción que `triaje_coincide` guarda como
        NULL en vez de como 0.
        """
        if not self.actuados:
            return None
        return (self.corregidos + self.rechazados) / self.actuados


def medir(actualizaciones: list[Actualizacion | None]) -> TasaDeCorreccion:
    """Agrega los actos de una tanda de infones."""
    aceptados = corregidos = rechazados = sin_actuar = 0
    por_campo: dict[str, int] = {}

    for actualizacion in actualizaciones:
        if actualizacion is None:
            sin_actuar += 1
        elif actualizacion.acto is Acto.ACEPTADO:
            aceptados += 1
        elif actualizacion.acto is Acto.CORREGIDO:
            corregidos += 1
            for campo in actualizacion.cambios:
                por_campo[campo] = por_campo.get(campo, 0) + 1
        else:
            rechazados += 1

    return TasaDeCorreccion(
        aceptados=aceptados,
        corregidos=corregidos,
        rechazados=rechazados,
        sin_actuar=sin_actuar,
        por_campo=por_campo,
    )
