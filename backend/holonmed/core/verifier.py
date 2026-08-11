"""Auditoría lógica: la segunda capa del filtro anti-alucinación.

SNOMED responde "¿este concepto existe?". Este módulo responde una
pregunta distinta y más difícil: "¿la evidencia del texto sostiene este
hallazgo?".

El caso típico es el laboratorio. Un modelo lee "Calcio 6.8", sabe que
existe el concepto Hipocalcemia, y lo afirma. Pero afirmarlo requiere
comparar 6.8 contra el corte del protocolo (8.5) y verificar que la
dirección del desvío coincide. Los LLM se equivocan sistemáticamente en
esa comparación, así que se les obliga a mostrarla paso a paso.
"""

import logging
from dataclasses import dataclass

from ..config import Settings, get_settings
from ..llm import LLMUnavailable, OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class Auditoria:
    es_valido: bool
    razon: str
    certeza: float

    @classmethod
    def no_evaluado(cls, motivo: str) -> "Auditoria":
        return cls(False, motivo, 0.0)


PROMPT_AUDITOR = """Actúa como un Auditor Médico de Seguridad y Calidad (Senior).

REGLA DE ORO: un hallazgo es VÁLIDO sólo si la evidencia lo sustenta de
forma unívoca.

PROTOCOLO ACTIVO (incluye los criterios de laboratorio):
================================================================
{protocolo}
================================================================

EVIDENCIA (texto original del paciente):
"{evidencia}"

HALLAZGO A AUDITAR:
"{hallazgo}"

TAREA — anclaje matemático explícito:
1. Localiza en el texto el valor numérico correspondiente al hallazgo.
2. Compara ese valor contra el corte del protocolo, mostrando la operación.
   Ejemplo: hallazgo "Hipocalcemia", valor 6.8, corte "< 8.5".
   Razonamiento: ¿6.8 es menor que 8.5? Sí -> VÁLIDO.
3. Verifica la DIRECCIÓN del desvío: que el término diga ALTO cuando el
   valor está por encima, y BAJO cuando está por debajo. Invertirlo es un
   error grave.
4. Si no hay evidencia numérica ni descripción explícita, o el valor está
   en rango normal, el hallazgo es FALSO.

No infieras lo que no está escrito. Ante la duda, marca inválido.

Responde en JSON:
{{"valido": true/false, "analisis": "razonamiento paso a paso", "confianza": 0-100}}"""


class ClinicalVerifier:
    """Valida hallazgos contra los criterios del protocolo activo."""

    def __init__(self, llm: OllamaClient, settings: Settings | None = None):
        self.llm = llm
        self.settings = settings or get_settings()

    async def auditar(
        self,
        hallazgo: str,
        texto_original: str,
        contenido_skill: str,
    ) -> Auditoria:
        prompt = PROMPT_AUDITOR.format(
            protocolo=contenido_skill[:6000],
            evidencia=texto_original,
            hallazgo=hallazgo,
        )

        try:
            res = await self.llm.generar_json(
                prompt,
                model=self.settings.model_clinical,
                timeout=self.settings.llm_timeout_fast,
            )
        except LLMUnavailable as exc:
            logger.warning("Auditoría no disponible: %s", exc)
            return Auditoria.no_evaluado(f"Auditoría no disponible: {exc}")

        if not res:
            return Auditoria.no_evaluado("El auditor no devolvió JSON interpretable")

        # Los modelos locales varían las claves entre ejecuciones; se aceptan
        # las variantes conocidas antes de rendirse.
        valido = _leer_booleano(res, ("valido", "es_valido", "es_logicamente_valido"))
        razon = _leer_texto(res, ("analisis", "razon", "explicacion", "reasoning"))
        certeza = _leer_numero(res, ("confianza", "certeza", "certeza_logica"), 0.0)

        return Auditoria(valido, razon or "Sin detalle", certeza)


def _leer_booleano(data: dict, claves: tuple) -> bool:
    for clave in claves:
        if clave in data:
            valor = data[clave]
            if isinstance(valor, bool):
                return valor
            if isinstance(valor, str):
                return valor.strip().lower() in {"true", "sí", "si", "valido", "yes"}
    return False


def _leer_texto(data: dict, claves: tuple) -> str:
    for clave in claves:
        valor = data.get(clave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    return ""


def _leer_numero(data: dict, claves: tuple, defecto: float) -> float:
    for clave in claves:
        valor = data.get(clave)
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            try:
                return float(valor.strip().rstrip("%"))
            except ValueError:
                continue
    return defecto
