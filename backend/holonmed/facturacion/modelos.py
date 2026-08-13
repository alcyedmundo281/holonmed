"""Modelos de la cadena de facturación.

La secuencia es deliberada y no se puede saltar ningún eslabón:

    nota médica (P) → ORDEN → ejecución por un actor → cargo

Una orden no describe: **autoriza**. Es un acto de habla que crea una
obligación, y por eso es la fuente de la verdad para facturar. La ejecución
es la confirmación de que alguien la cumplió. El cargo sólo existe donde
ambas cosas coinciden.

Eso convierte la propiedad antifraude en algo **estructural** en vez de una
instrucción amable en un prompt: sin orden no hay cargo, no porque se lo
pidamos al modelo sino porque no existe la fila.

Y el descuadre vale más como seguridad que como dinero:

    orden sin ejecución   el paciente no recibió lo prescrito
    ejecución sin orden   administración no autorizada
    orden + ejecución     facturable

Los dos primeros son incidentes clínicos que hoy se detectan tarde o nunca.
El mismo mecanismo que cuadra la cuenta cuadra la medicación.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EstadoOrden(str, Enum):
    PENDIENTE = "pendiente"  # autorizada, nadie la ha cumplido todavía
    CUMPLIDA = "cumplida"  # hay ejecución que la satisface
    ANULADA = "anulada"  # el prescriptor la retiró


class EstadoCargo(str, Enum):
    """Un cargo nace propuesto. Facturar exige que alguien lo confirme.

    Es la misma lógica que el estado ALERTA de los infones: el sistema
    propone, una persona autoriza. Cobrarle a un paciente por algo que
    dedujo un modelo de lenguaje sin que nadie lo mirara sería
    indefendible.
    """

    PROPUESTO = "propuesto"
    CONFIRMADO = "confirmado"
    ANULADO = "anulado"


class TipoDescuadre(str, Enum):
    ORDEN_SIN_EJECUTAR = "orden_sin_ejecutar"
    EJECUCION_SIN_ORDEN = "ejecucion_sin_orden"


class Orden(BaseModel):
    """Lo que el profesional autorizó. La fuente de verdad de la cadena."""

    id: str | None = None
    paciente_id: str
    tic_id: str | None = None
    timestamp: str = Field(default_factory=_now)

    termino: str = Field(description="Qué se ordenó, normalizado")
    codigo: str | None = None
    sistema: str | None = None
    concepto_id: int | None = None

    # Trazabilidad hasta la nota. Sin esto un cargo no se puede defender
    # ante una auditoría ni ante el propio paciente.
    texto_origen: str = ""
    prescriptor: str | None = None

    detalle: dict = Field(
        default_factory=dict,
        description="Dosis, frecuencia, duración, vía… según el tipo de orden",
    )
    estado: EstadoOrden = EstadoOrden.PENDIENTE


class Ejecucion(BaseModel):
    """Lo que un actor hizo. Farmacia dispensa, enfermería administra."""

    id: str | None = None
    paciente_id: str
    orden_id: str | None = Field(
        default=None,
        description="Nulo mientras no se concilie, o si nunca hubo orden",
    )
    tic_id: str | None = None
    timestamp: str = Field(default_factory=_now)

    termino: str
    codigo: str | None = None
    sistema: str | None = None

    actor: str | None = None
    origen: str = "farmacia"
    texto_origen: str = ""
    detalle: dict = Field(default_factory=dict)


class Cargo(BaseModel):
    """Un concepto facturable, con su trazabilidad completa."""

    id: str | None = None
    paciente_id: str
    orden_id: str | None = None
    ejecucion_id: str | None = None
    creado: str = Field(default_factory=_now)

    codigo_tarifario: str
    sistema_tarifario: str
    descripcion: str
    cantidad: float = 1.0
    importe_unitario: float = 0.0
    estado: EstadoCargo = EstadoCargo.PROPUESTO

    @property
    def importe(self) -> float:
        return round(self.cantidad * self.importe_unitario, 2)


class Descuadre(BaseModel):
    """Una orden y su ejecución no cuadran. Casi siempre es clínico."""

    tipo: TipoDescuadre
    termino: str
    timestamp: str
    detalle: str
    orden_id: str | None = None
    ejecucion_id: str | None = None

    @property
    def es_incidente_de_seguridad(self) -> bool:
        """Ambos tipos lo son, y conviene decirlo explícitamente.

        Una orden sin ejecutar significa que el paciente no recibió lo
        prescrito. Una ejecución sin orden, que recibió algo que nadie
        autorizó. Ninguna de las dos es un problema de facturación.
        """
        return True


class Cuenta(BaseModel):
    """La cuenta del paciente como proyección, no como cálculo final.

    El problema de las seis horas de espera al alta no es de velocidad de
    proceso: es que la cuenta se calcula en bloque al final. Si cada tic
    acumula sus cargos, al alta no hay nada que calcular, sólo que cerrar.
    """

    paciente_id: str
    generada: str = Field(default_factory=_now)
    cargos: list[Cargo] = Field(default_factory=list)
    descuadres: list[Descuadre] = Field(default_factory=list)
    moneda: str = "USD"

    @property
    def confirmados(self) -> list[Cargo]:
        return [c for c in self.cargos if c.estado is EstadoCargo.CONFIRMADO]

    @property
    def propuestos(self) -> list[Cargo]:
        return [c for c in self.cargos if c.estado is EstadoCargo.PROPUESTO]

    @property
    def total_confirmado(self) -> float:
        return round(sum(c.importe for c in self.confirmados), 2)

    @property
    def total_propuesto(self) -> float:
        """Lo que está pendiente de que una persona lo revise."""
        return round(sum(c.importe for c in self.propuestos), 2)

    @property
    def cerrable(self) -> bool:
        """¿Se puede dar el alta sin dejar nada sin resolver?"""
        return not self.propuestos and not self.descuadres
