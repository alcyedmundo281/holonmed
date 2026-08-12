"""Modelos de dominio de HolonMed.

El vocabulario es deliberado y viene de la teoría que sostiene el sistema:

* **Infón**: el átomo de verdad. Un hallazgo clínico único, normalizado
  contra SNOMED CT y auditado. Si no pasó el validador, sigue siendo un
  infón, pero marcado como ruido: el sistema nunca borra evidencia, la
  clasifica.
* **Holón**: la historia clínica como organismo. No es un formulario que
  se rellena, es un ente que crece absorbiendo infones a lo largo del
  tiempo. Cada consulta es un *tic* que lo hace crecer.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EstadoInfon(str, Enum):
    """Veredicto del validador de tres capas."""

    VALIDADO = "VALIDADO"  # Ontología y lógica coinciden. Utilizable.
    ALERTA = "ALERTA"  # Acierto ontológico, duda lógica. Requiere ojo humano.
    RUIDO = "RUIDO"  # Descartado. Probable alucinación del modelo.


class Infon(BaseModel):
    """El átomo de verdad: una afirmación clínica validada y trazable."""

    timestamp: str = Field(default_factory=_now)

    # Procedencia
    texto_origen: str = Field(description="Cita textual de la narrativa original")
    termino_propuesto: str = Field(description="Lo que el LLM extrajo, sin normalizar")

    # Normalización ontológica. El sistema de codificación es explícito
    # porque el vocabulario es intercambiable: puede ser el semilla del
    # proyecto, SNOMED CT si tienes licencia, o cualquier otro importado.
    termino: str = Field(description="Término preferente tras la normalización")
    codigo: str | None = None
    sistema: str | None = Field(
        default=None, description="'holonmed' | 'snomed' | 'hpo' | …"
    )
    concepto_id: int | None = Field(
        default=None, description="Clave interna del concepto en el grafo"
    )
    cie10_code: str | None = None
    linaje_clinico: str | None = Field(
        default=None, description="Concepto padre en la jerarquía del grafo"
    )

    # Veredicto y trazabilidad
    estado: EstadoInfon = EstadoInfon.RUIDO
    confianza: float = 0.0
    score_ontologico: float = 0.0
    score_logico: float = 0.0
    razon_auditoria: str = "No evaluado"
    origen_skill: str = "general_triage"

    @property
    def es_valido(self) -> bool:
        return self.estado == EstadoInfon.VALIDADO

    @property
    def es_facturable(self) -> bool:
        """Un infón sólo sirve para facturar si está validado y mapea a CIE-10."""
        return self.es_valido and bool(self.cie10_code)


class InferenciaBayesiana(BaseModel):
    """Salida del motor abductivo: una hipótesis con su razonamiento visible."""

    diagnostico: str
    probabilidad_porcentaje: float
    probabilidad_previa: float
    traza_logica: list[str] = Field(
        default_factory=list, description="Cómo se construyó la probabilidad a priori"
    )
    evidencia_utilizada: list[str] = Field(
        default_factory=list, description="Qué infones movieron la aguja y cuánto"
    )

    @property
    def veredicto(self) -> str:
        if self.probabilidad_porcentaje > 90:
            return "HIPOTESIS_CONFIRMADA"
        if self.probabilidad_porcentaje > 50:
            return "PROBABLE"
        return "BAJA_SOSPECHA"


class ResultadoTic(BaseModel):
    """Todo lo que produce un único ciclo de procesamiento (un *tic*)."""

    tic_id: str | None = None
    timestamp: str = Field(default_factory=_now)
    paciente_id: str
    texto_original: str

    skill_activa: str
    resumen: str = ""
    infones: list[Infon] = Field(default_factory=list)
    inferencia: InferenciaBayesiana | None = None

    @property
    def infones_validados(self) -> list[Infon]:
        return [i for i in self.infones if i.es_valido]

    @property
    def infones_descartados(self) -> list[Infon]:
        return [i for i in self.infones if i.estado == EstadoInfon.RUIDO]


class HolonPaciente(BaseModel):
    """La historia clínica como organismo digital que crece por absorción."""

    paciente_id: str
    nombre: str = "Paciente"
    edad: int | None = None
    sexo: str | None = None
    telefono: str | None = None
    antecedentes: str = ""

    linea_tiempo: list[Infon] = Field(default_factory=list)
    resumen_vivo: str = "Paciente nuevo sin antecedentes registrados."

    def absorber(self, nuevos: list[Infon]) -> None:
        """El crecimiento del holón: sólo se integra lo que fue validado."""
        self.linea_tiempo.extend(i for i in nuevos if i.es_valido)

    def metadatos_para_bayes(self, texto_actual: str = "") -> dict[str, Any]:
        """Contexto que alimenta la probabilidad a priori.

        Se consideran tres fuentes: los antecedentes registrados en la
        ficha, los hallazgos validados de visitas anteriores, y **la
        narrativa de hoy**.

        Incluir la narrativa actual no es opcional: en una primera
        consulta la ficha está vacía y los factores de riesgo sólo
        aparecen en el texto que el clínico acaba de escribir. Sin ella,
        un «bebedor de riesgo con litiasis biliar» arrancaría con la
        prevalencia de la población general.

        Limitación conocida: el emparejamiento de factores es por
        subcadena, así que no entiende negaciones. Una nota que diga «no
        consume alcohol» activaría igualmente un factor «alcohol». Es el
        precio de no meter otra llamada al modelo en el camino, y por eso
        la traza muestra siempre qué factor se aplicó y con qué peso.
        """
        historicos = " ".join(i.termino for i in self.linea_tiempo)
        contexto = f"{self.antecedentes} {historicos} {texto_actual}"
        return {
            "edad": self.edad,
            "sexo": self.sexo,
            "antecedentes": contexto.lower().strip(),
        }


# --- DTOs de la API ---------------------------------------------------


class CrystallizeRequest(BaseModel):
    texto: str = Field(min_length=1, description="Narrativa clínica en bruto")
    paciente_id: str = "default"
    skill: str | None = Field(
        default=None, description="Fuerza una skill y salta el triaje automático"
    )


class ChatRequest(BaseModel):
    mensaje: str = Field(min_length=1)
    paciente_id: str = "default"


class PacienteCreate(BaseModel):
    nombre: str = Field(min_length=1)
    edad: int | None = None
    sexo: str | None = None
    telefono: str | None = None
    antecedentes: str = ""


class CitaCreate(BaseModel):
    paciente_id: str
    fecha: str = Field(description="Fecha en lenguaje natural o ISO")
    motivo: str = "Control"
