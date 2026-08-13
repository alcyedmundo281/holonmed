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

REGLA DE ORO: un hallazgo es VÁLIDO si la evidencia del texto lo sustenta.
Tu única pregunta es «¿dice el texto esto?», no «¿es importante?» ni
«¿aparece en el protocolo?».

PROTOCOLO ACTIVO (referencia para los valores de laboratorio):
================================================================
{protocolo}
================================================================

EVIDENCIA (texto original del paciente):
"{evidencia}"

HALLAZGO A AUDITAR:
"{hallazgo}"

Hay DOS tipos de evidencia y ambos son válidos. Identifica cuál aplica:

A) EVIDENCIA NUMÉRICA — el hallazgo se deduce de una cifra.
   1. Localiza el valor en el texto.
   2. Compáralo con el corte, mostrando la operación.
      Ejemplo: "Hipocalcemia", valor 6.8, corte < 8.5.
      ¿6.8 es menor que 8.5? Sí -> VÁLIDO.
   3. Verifica la DIRECCIÓN: el término debe decir ALTO cuando el valor
      está por encima y BAJO cuando está por debajo. Invertirlo es grave.
   4. Si el protocolo no declara un corte para ese parámetro, usa los
      rangos de referencia habituales en adultos. Que el protocolo no lo
      mencione NO invalida el hallazgo.

B) EVIDENCIA TEXTUAL — el hallazgo es cualitativo y el texto lo afirma.
   Síntomas, signos exploratorios y antecedentes no tienen número, y no
   por eso son falsos. "Vómitos repetidos" sustenta "Vómitos"; "abdomen
   con defensa" sustenta "Irritación peritoneal".
   Basta con que el texto lo afirme de forma reconocible, aunque use
   otras palabras.

Es INVÁLIDO cuando:
  - El texto NIEGA el hallazgo ("no refiere fiebre" -> Fiebre es falso).
  - El valor está dentro del rango normal.
  - El hallazgo no aparece en el texto ni puede deducirse de él.
  - La dirección del desvío está invertida.

No infieras lo que no está escrito, pero tampoco exijas un número donde
la clínica no lo tiene. Ante la duda real, marca inválido.

Responde en JSON, con el análisis en UNA sola frase de menos de 200
caracteres. No uses markdown ni listas dentro del JSON:
{{"valido": true, "analisis": "6.8 < 8.5, calcio por debajo del corte", "confianza": 95}}"""


PROMPT_AUDITOR_AUSENCIA = """Actúa como un Auditor Médico de Seguridad y Calidad (Senior).

PROTOCOLO ACTIVO (referencia para los valores de laboratorio):
================================================================
{protocolo}
================================================================

EVIDENCIA (texto original del paciente):
"{evidencia}"

AFIRMACIÓN A AUDITAR:
«El texto documenta que "{hallazgo}" NO está presente.»

No te preguntamos si "{hallazgo}" es cierto —damos por hecho que no—.
Te preguntamos si **la negación** está respaldada por el texto.

PROCEDIMIENTO. Sigue estos pasos en orden y para en el primero que aplique:

PASO 1 — ¿Hay una CIFRA medida del parámetro en el texto?
   Si la hay, NO es un silencio: alguien lo midió. Compárala con el corte.
     · Valor dentro del rango normal  -> ausencia CONFIRMADA.
       «lipasa 45» con corte en 60 confirma que no hay hiperlipasemia.
       No hace falta ninguna frase que lo niegue: la cifra lo dice.
     · Valor fuera del rango          -> ausencia NO confirmada
       (el hallazgo sí está presente).

PASO 2 — ¿Hay una NEGACIÓN explícita?
   «no refiere fiebre», «niega disnea», «sin dolor torácico»,
   «abdomen blando, sin defensa»  -> ausencia CONFIRMADA.

PASO 3 — ¿El parámetro no aparece por ningún lado?
   Entonces sí es un silencio -> ausencia NO confirmada.
   Que no se hable de algo no significa que no esté: significa que no se
   sabe. Sólo aquí aplica esta regla.

Un dato medido nunca cae en el paso 3.

Responde en JSON. El campo se llama `ausencia_confirmada` para que no
quepa duda de qué se pregunta. Indica también qué paso aplicaste.
Análisis en UNA frase de menos de 200 caracteres:
{{"ausencia_confirmada": true, "paso": 1, "analisis": "lipasa 45 < 60, dentro de rango", "confianza": 95}}"""


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
        ausente: bool = False,
    ) -> Auditoria:
        """Comprueba que la evidencia sostiene el hallazgo.

        Con `ausente=True` la pregunta cambia: ya no es «¿dice el texto
        que esto está?» sino «¿dice el texto que esto NO está?». Son
        preguntas distintas y el prompt también, porque el error a evitar
        es distinto: aquí lo grave es tomar un silencio por una negación.
        """
        plantilla = PROMPT_AUDITOR_AUSENCIA if ausente else PROMPT_AUDITOR
        prompt = plantilla.format(
            protocolo=contenido_skill[:6000],
            evidencia=texto_original,
            hallazgo=hallazgo,
        )

        try:
            res = await self.llm.generar_json(
                prompt,
                model=self.settings.model_clinical,
                timeout=self.settings.llm_timeout_slow,
            )
        except LLMUnavailable as exc:
            logger.warning("Auditoría no disponible: %s", exc)
            return Auditoria.no_evaluado(f"Auditoría no disponible: {exc}")

        if not res:
            logger.warning(
                "Auditoría ilegible para '%s'; se marca como no evaluada", hallazgo[:60]
            )
            return Auditoria.no_evaluado("El auditor no devolvió JSON interpretable")

        # Los modelos locales varían las claves entre ejecuciones; se aceptan
        # las variantes conocidas antes de rendirse.
        valido = _leer_booleano(
            res,
            ("ausencia_confirmada", "valido", "es_valido", "es_logicamente_valido"),
        )
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
