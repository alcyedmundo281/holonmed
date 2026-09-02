"""Validación ontológica: el filtro anti-alucinación.

Un LLM produce texto plausible; el vocabulario decide si ese texto
corresponde a un concepto clínico real, y cuál exactamente.

La estrategia es *Broad Retrieve & Re-Rank*: recuperar muchos candidatos de
forma barata (FTS5 + puntuado difuso) y luego pedirle al LLM que actúe como
auditor de terminología para elegir uno — o ninguno. Que pueda decir
"ninguno" es la parte importante.

Este módulo no sabe qué vocabulario hay debajo. Funciona igual con el
semilla del proyecto que con SNOMED CT importado, porque habla con
`TerminologyIndex` y no con un formato concreto.
"""

import logging
from dataclasses import dataclass

from ..config import Settings, get_settings
from ..llm import LLMUnavailable, OllamaClient
from .terminology import Candidato, TerminologyIndex

logger = logging.getLogger(__name__)


# --- Guardas de colisión ---------------------------------------------
# Pares de conceptos que un motor de similitud confunde y que un clínico
# jamás confundiría. La distancia de edición entre "hiperlipasemia" e
# "hiperlipemia" es mínima; la distancia clínica es enorme: una es una
# enzima pancreática, la otra es grasa en sangre.
#
# Si el input contiene un marcador y el candidato el opuesto, el
# emparejamiento se bloquea. Es una guarda dura: ni el LLM la salta.
COLISIONES_PROHIBIDAS: list[tuple[str, str]] = [
    ("amilasa", "lipasa"),  # dos enzimas distintas
    ("amilasemia", "lipasemia"),
    ("lipasemia", "lipemia"),  # enzima vs. lípidos
    ("amilasemia", "potasemia"),  # enzima vs. electrolito
    ("amilasemia", "kalemia"),
    ("calcemia", "potasemia"),  # calcio vs. potasio
    ("calcemia", "kalemia"),
    ("natremia", "potasemia"),  # sodio vs. potasio
    ("natremia", "kalemia"),
    ("calcemia", "natremia"),  # calcio vs. sodio
    ("glucemia", "glucosuria"),  # en sangre vs. en orina
    ("hematuria", "hematemesis"),  # sangre en orina vs. en vómito
    ("hipo", "hiper"),  # dirección del desvío invertida
]


def hay_colision(texto_a: str, texto_b: str) -> str | None:
    """Detecta si dos términos son un emparejamiento clínicamente prohibido."""
    a, b = texto_a.lower(), texto_b.lower()
    for izq, der in COLISIONES_PROHIBIDAS:
        if (izq in a and der in b and izq not in b) or (
            der in a and izq in b and der not in b
        ):
            return f"colisión '{izq}' vs '{der}'"
    return None


@dataclass
class Match:
    """Resultado de intentar anclar un término al vocabulario."""

    concepto_id: int | None
    codigo: str | None
    sistema: str | None
    termino: str
    score: float
    es_ruido: bool
    cie10: str | None = None
    linaje: str | None = None
    metodo: str = "ninguno"

    @classmethod
    def ruido(cls, termino: str, motivo: str = "sin_match") -> "Match":
        return cls(
            concepto_id=None,
            codigo=None,
            sistema=None,
            termino=termino,
            score=0.0,
            es_ruido=True,
            metodo=motivo,
        )


PROMPT_AUDITOR = """Actúa como un Auditor de Terminología Médica Senior.

INPUT DEL MÉDICO: "{candidato}"

CANDIDATOS DEL VOCABULARIO:
{opciones}
0. NINGUNO / NO ESTOY SEGURO

INSTRUCCIONES DE SEGURIDAD:
1. REGLA DE IDENTIDAD: el input debe ser EL MISMO CONCEPTO que el candidato.
   - "Vómitos" NO es "Pancreatitis".
   - NUNCA selecciones una ENFERMEDAD si el input es sólo un SIGNO o SÍNTOMA.
2. QUÍMICA Y ENZIMAS (precisión total):
   - "Hiperamilasemia" (enzima) != "Hiperpotasemia" (electrolito).
   - "Hiperlipasemia" (enzima LIPASA) != "Hiperlipemia" (GRASAS en sangre).
     Confundir enzimas con lípidos es un error crítico: responde 0.
3. ANTÓNIMOS: "Dolor" != "Sin dolor". "Hipocalcemia" != "Hipercalcemia".
4. LOCALIZACIÓN: "sangre en orina" != "sangre en vómito".
5. EQUIVALENCIA: "Amilasa elevada" = "Hiperamilasemia" (aceptar).

Ante la duda, responde 0. Un falso negativo se corrige; un falso positivo
contamina la historia clínica.

Responde SOLO con el número del mejor candidato."""


class OntologyValidator:
    """Orquesta las capas de normalización sobre un `TerminologyIndex`."""

    def __init__(
        self,
        index: TerminologyIndex,
        llm: OllamaClient,
        settings: Settings | None = None,
    ):
        self.index = index
        self.llm = llm
        self.settings = settings or get_settings()

    async def validar(
        self,
        texto_candidato: str,
        hints: dict[str, str] | None = None,
    ) -> Match:
        """Ancla un término libre a un concepto, o lo declara ruido."""
        candidato = texto_candidato.strip()
        if not candidato:
            return Match.ruido(texto_candidato, "vacio")

        # CAPA 0 — Skill-hints. Códigos revisados por un humano en el
        # protocolo activo; ganan a cualquier heurística.
        if hints:
            match = self._match_por_hint(candidato, hints)
            if match:
                return match

        # CAPA 1 — Recuperación amplia (FTS5 acota, difuso puntúa).
        candidatos = self.index.buscar_candidatos(candidato, limite=15)
        if not candidatos:
            return Match.ruido(texto_candidato, "sin_candidatos")

        # Un acierto exacto sobre el vocabulario no necesita arbitraje.
        if candidatos[0].score >= 100.0 and len(candidatos) == 1:
            return self._construir(candidatos[0], "exacto")

        # CAPA 2 — Re-ranking semántico con auditoría clínica.
        match = await self._rerank_con_llm(candidato, candidatos)
        if match:
            return match

        # CAPA 3 — Fallback difuso, con umbral alto y guarda de colisión.
        mejor = candidatos[0]
        if mejor.score < self.settings.threshold_fuzzy_fallback:
            return Match.ruido(texto_candidato, "score_insuficiente")
        if hay_colision(candidato, mejor.termino):
            return Match.ruido(texto_candidato, "colision_bloqueada")
        return self._construir(mejor, "fuzzy")

    def _match_por_hint(self, candidato: str, hints: dict[str, str]) -> Match | None:
        from rapidfuzz import fuzz

        objetivo = candidato.lower()

        if objetivo in hints:
            return self._desde_hint(hints[objetivo], candidato, "hint_exacto")

        for termino_hint, codigo in hints.items():
            limpio = termino_hint.lower()
            if hay_colision(objetivo, limpio):
                continue
            if (
                fuzz.token_sort_ratio(objetivo, limpio)
                > self.settings.threshold_hint_fuzzy
            ):
                return self._desde_hint(codigo, termino_hint, "hint_difuso")
        return None

    def _desde_hint(self, codigo: str, termino: str, metodo: str) -> Match:
        """Un hint aporta el código; el resto de metadatos se busca si existe.

        El protocolo puede referirse a un código de un vocabulario que no
        está cargado. En ese caso el hint sigue valiendo — el término está
        revisado por un humano — pero no hay linaje ni mapeo que ofrecer.
        """
        candidato = self.index.buscar_exacto(termino)
        if candidato:
            return self._construir(
                Candidato(
                    candidato.concepto_id,
                    candidato.codigo,
                    candidato.sistema,
                    candidato.termino,
                    100.0,
                ),
                metodo,
            )
        return Match(
            concepto_id=None,
            codigo=codigo,
            sistema="skill",
            termino=termino,
            score=100.0,
            es_ruido=False,
            metodo=metodo,
        )

    async def _rerank_con_llm(
        self, candidato: str, candidatos: list[Candidato]
    ) -> Match | None:
        opciones = "\n".join(f"{i + 1}. {c.termino}" for i, c in enumerate(candidatos))
        prompt = PROMPT_AUDITOR.format(candidato=candidato, opciones=opciones)

        try:
            raw = await self.llm.generar(
                prompt,
                model=self.settings.model_router,
                timeout=self.settings.llm_timeout_fast,
            )
        except LLMUnavailable as exc:
            logger.warning("Re-ranking sin LLM (%s); se usará el fallback", exc)
            return None

        partes = raw.strip().replace(".", "").split()
        if not partes or not partes[0].isdigit():
            return None

        idx = int(partes[0])
        if idx == 0 or idx > len(candidatos):
            return None  # El auditor dijo "ninguno". Se respeta.

        elegido = candidatos[idx - 1]

        # El veredicto del LLM no anula las guardas duras.
        motivo = hay_colision(candidato, elegido.termino)
        if motivo:
            logger.info("Selección del LLM bloqueada por %s", motivo)
            return None

        # Un concepto confirmado por el auditor merece alta confianza aunque
        # la similitud literal fuera baja (sinónimos lejanos, siglas).
        confirmado = Candidato(
            elegido.concepto_id,
            elegido.codigo,
            elegido.sistema,
            elegido.termino,
            99.0 if elegido.score > 40 else elegido.score,
        )
        return self._construir(confirmado, "rerank_llm")

    def _construir(self, candidato: Candidato, metodo: str) -> Match:
        cie10, linaje = self.index.metadatos(candidato.concepto_id)
        return Match(
            concepto_id=candidato.concepto_id,
            codigo=candidato.codigo,
            sistema=candidato.sistema,
            termino=candidato.termino,
            score=candidato.score,
            es_ruido=False,
            cie10=cie10,
            linaje=linaje,
            metodo=metodo,
        )
