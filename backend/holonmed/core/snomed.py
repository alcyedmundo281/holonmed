"""Normalización y validación ontológica contra SNOMED CT.

Este módulo es el filtro anti-alucinación del sistema. Un LLM produce
texto plausible; SNOMED decide si ese texto corresponde a un concepto
clínico real, y cuál exactamente.

La estrategia es *Broad Retrieve & Re-Rank*: recuperar muchos candidatos
de forma barata (difusa o BM25), y luego pedirle al LLM que actúe como
auditor de terminología para elegir uno — o ninguno. Que pueda decir
"ninguno" es la parte importante.

Dos backends intercambiables:
  * `LocalSnomedIndex`  — Snapshot oficial en memoria, rapidfuzz, cache pickle.
  * `ArangoSnomedIndex` — ArangoSearch con BM25 y analizador español.

Aviso de licencia: SNOMED CT requiere licencia de afiliado en tu país.
Este repositorio contiene el código que lo consume, nunca los datos.
"""

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..config import Settings, get_settings
from ..llm import LLMUnavailable, OllamaClient

logger = logging.getLogger(__name__)

Candidato = tuple[str, str, float]  # (snomed_id, término, score)


# --- Guardas de colisión ---------------------------------------------
# Pares de conceptos que un motor de similitud confunde y que un clínico
# jamás confundiría. La distancia de edición entre "hiperlipasemia" e
# "hiperlipemia" es mínima; la distancia clínica es enorme: una es una
# enzima pancreática, la otra es grasa en sangre.
#
# Cada entrada es un par de marcadores mutuamente excluyentes. Si el input
# contiene uno y el candidato el otro, el emparejamiento se bloquea.
COLISIONES_PROHIBIDAS: list[tuple[str, str]] = [
    ("amilasa", "lipasa"),  # dos enzimas distintas
    ("lipasemia", "lipemia"),  # enzima vs. lípidos
    ("amilasemia", "potasemia"),  # enzima vs. electrolito
    ("amilasemia", "kalemia"),  # idem, con la otra nomenclatura
    ("amilasemia", "potasio"),
    ("calcemia", "potasemia"),  # calcio vs. potasio
    ("calcemia", "kalemia"),
    ("natremia", "potasemia"),  # sodio vs. potasio
    ("natremia", "kalemia"),
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
class SnomedMatch:
    """Resultado de intentar anclar un término a la ontología."""

    snomed_id: str | None
    termino: str
    score: float
    es_ruido: bool
    cie10: str | None = None
    linaje: str | None = None
    metodo: str = "ninguno"

    @classmethod
    def ruido(cls, termino: str, motivo: str = "sin_match") -> "SnomedMatch":
        return cls(
            snomed_id=None,
            termino=termino,
            score=0.0,
            es_ruido=True,
            metodo=motivo,
        )


class SnomedIndex(Protocol):
    """Contrato mínimo que debe cumplir cualquier fuente de SNOMED."""

    def disponible(self) -> bool: ...

    def buscar_candidatos(self, texto: str, limite: int = 15) -> list[Candidato]: ...

    def metadatos(self, snomed_id: str) -> tuple[str | None, str | None]: ...


class LocalSnomedIndex:
    """Snapshot oficial cargado en memoria.

    La primera carga procesa cientos de MB de TSV y tarda; a partir de ahí
    se sirve desde un cache pickle binario y el arranque es instantáneo.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.term_map: dict[str, str] = {}  # término -> concept id
        self.id_to_term: dict[str, str] = {}  # concept id -> término principal
        self.cie10_map: dict[str, str] = {}  # concept id -> código CIE-10
        self.parents: dict[str, str] = {}  # concept id -> concept id del padre
        self.loaded = False

    def disponible(self) -> bool:
        return self.loaded

    def cargar(self) -> tuple[bool, str]:
        cache = self.settings.snomed_cache_path
        if cache.exists() and self._cargar_cache(cache):
            return True, f"Cache SNOMED cargado ({len(self.term_map):,} términos)"

        desc = self.settings.snomed_description_path
        if not desc.exists():
            return False, (
                f"No se encontró el Snapshot de SNOMED en {desc}. "
                "Ejecuta `python scripts/setup_snomed.py --help`."
            )

        try:
            self._ingerir(desc)
        except Exception as exc:  # noqa: BLE001 — se reporta, no se traga
            logger.exception("Fallo ingiriendo SNOMED")
            return False, f"Error procesando el Snapshot: {exc}"

        self._guardar_cache(cache)
        self.loaded = True
        return True, f"Snapshot ingerido ({len(self.term_map):,} términos)"

    def _cargar_cache(self, cache: Path) -> bool:
        try:
            with cache.open("rb") as fh:
                data = pickle.load(fh)
            self.term_map = data["term_map"]
            self.id_to_term = data["id_to_term"]
            self.cie10_map = data.get("cie10_map", {})
            self.parents = data.get("parents", {})
            self.loaded = True
            return True
        except (OSError, pickle.PickleError, KeyError) as exc:
            logger.warning("Cache SNOMED ilegible (%s); se reingiere", exc)
            return False

    def _ingerir(self, desc_path: Path) -> None:
        import pandas as pd  # import perezoso: pandas es caro de importar

        # 1. Vocabulario: sólo descripciones activas.
        df = pd.read_csv(
            desc_path,
            sep="\t",
            dtype=str,
            usecols=["conceptId", "term", "active"],
            low_memory=False,
        )
        df = df[df["active"] == "1"]
        self.term_map = pd.Series(df.conceptId.values, index=df.term).to_dict()
        self.id_to_term = (
            df.drop_duplicates("conceptId").set_index("conceptId")["term"].to_dict()
        )

        # 2. Mapa a CIE-10 (lo que hace facturable un hallazgo).
        map_path = self.settings.snomed_map_path
        if map_path and map_path.exists():
            df_map = pd.read_csv(
                map_path,
                sep="\t",
                dtype=str,
                usecols=["referencedComponentId", "mapTarget", "active"],
            )
            df_map = df_map[df_map["active"] == "1"]
            self.cie10_map = pd.Series(
                df_map.mapTarget.values, index=df_map.referencedComponentId
            ).to_dict()

        # 3. Jerarquía IS_A (typeId 116680003) para el linaje clínico.
        rel_path = self.settings.snomed_relationship_path
        if rel_path and rel_path.exists():
            df_rel = pd.read_csv(
                rel_path,
                sep="\t",
                dtype=str,
                usecols=["sourceId", "destinationId", "typeId", "active"],
            )
            df_rel = df_rel[
                (df_rel["active"] == "1") & (df_rel["typeId"] == "116680003")
            ]
            self.parents = pd.Series(
                df_rel.destinationId.values, index=df_rel.sourceId
            ).to_dict()

    def _guardar_cache(self, cache: Path) -> None:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            with cache.open("wb") as fh:
                pickle.dump(
                    {
                        "term_map": self.term_map,
                        "id_to_term": self.id_to_term,
                        "cie10_map": self.cie10_map,
                        "parents": self.parents,
                    },
                    fh,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
        except OSError as exc:
            logger.warning("No se pudo escribir el cache SNOMED: %s", exc)

    def buscar_candidatos(self, texto: str, limite: int = 15) -> list[Candidato]:
        if not self.loaded:
            return []
        from rapidfuzz import fuzz, process

        crudos = process.extract(
            texto.strip().lower(),
            self.term_map.keys(),
            scorer=fuzz.token_sort_ratio,
            limit=limite,
            score_cutoff=45,
        )
        return [(self.term_map[t], t, float(s)) for t, s, _ in crudos]

    def metadatos(self, snomed_id: str) -> tuple[str | None, str | None]:
        cie10 = self.cie10_map.get(snomed_id)
        padre_id = self.parents.get(snomed_id)
        linaje = self.id_to_term.get(padre_id) if padre_id else None
        return cie10, linaje or "Concepto raíz"


class ArangoSnomedIndex:
    """Búsqueda BM25 sobre una vista ArangoSearch con analizador español.

    Alternativa al índice local cuando SNOMED ya está ingerido en la base
    de datos: no consume RAM del proceso y escala mejor entre instancias.
    """

    VIEW = "snomed_search_view"

    def __init__(self, db, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()

    def disponible(self) -> bool:
        try:
            return self.db is not None and self.db.has_view(self.VIEW)
        except Exception:  # noqa: BLE001 — la disponibilidad nunca debe romper
            return False

    def buscar_candidatos(self, texto: str, limite: int = 15) -> list[Candidato]:
        if not self.disponible():
            return []
        aql = """
            FOR d IN @@view
              SEARCH ANALYZER(d.term IN TOKENS(@term, 'text_es'), 'text_es')
              SORT BM25(d) DESC
              LIMIT @limite
              RETURN { id: d.conceptId, term: d.term, score: BM25(d) }
        """
        try:
            cursor = self.db.aql.execute(
                aql,
                bind_vars={"@view": self.VIEW, "term": texto, "limite": limite},
            )
            filas = list(cursor)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Búsqueda SNOMED en Arango falló: %s", exc)
            return []

        if not filas:
            return []

        # BM25 no está acotado; se normaliza a 0-100 relativo al mejor hit
        # para que sea comparable con los scores de rapidfuzz.
        mejor = max(f["score"] for f in filas) or 1.0
        return [
            (f["id"], f["term"], round(min(100.0, f["score"] / mejor * 100), 2))
            for f in filas
        ]

    def metadatos(self, snomed_id: str) -> tuple[str | None, str | None]:
        aql = """
            FOR c IN SnomedConcepts
              FILTER c.conceptId == @cid
              LIMIT 1
              RETURN { cie10: c.cie10, linaje: c.parentTerm }
        """
        try:
            res = list(self.db.aql.execute(aql, bind_vars={"cid": snomed_id}))
            if res:
                return res[0].get("cie10"), res[0].get("linaje") or "Concepto raíz"
        except Exception as exc:  # noqa: BLE001
            logger.debug("Metadatos SNOMED no disponibles para %s: %s", snomed_id, exc)
        return None, None


PROMPT_AUDITOR = """Actúa como un Auditor de Terminología Médica Senior (SNOMED CT).

INPUT DEL MÉDICO: "{candidato}"

CANDIDATOS DE LA BASE DE DATOS:
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
4. EQUIVALENCIA: "Amilasa elevada" = "Hiperamilasemia" (aceptar).

Ante la duda, responde 0. Un falso negativo se corrige; un falso positivo
contamina la historia clínica.

Responde SOLO con el número del mejor candidato."""


class SnomedValidator:
    """Orquesta las capas de normalización sobre cualquier `SnomedIndex`."""

    def __init__(
        self,
        index: SnomedIndex,
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
    ) -> SnomedMatch:
        """Ancla un término libre a un concepto SNOMED, o lo declara ruido."""
        candidato = texto_candidato.strip().lower()
        if not candidato:
            return SnomedMatch.ruido(texto_candidato, "vacio")

        # CAPA 0 — Skill-hints. El protocolo activo trae códigos SNOMED
        # verificados por un humano; ganan a cualquier heurística.
        if hints:
            match = self._match_por_hint(candidato, hints)
            if match:
                return match

        # CAPA 1 — Recuperación amplia y barata.
        candidatos = self.index.buscar_candidatos(candidato, limite=15)
        if not candidatos:
            return SnomedMatch.ruido(texto_candidato, "sin_candidatos")

        # CAPA 2 — Re-ranking semántico con auditoría clínica.
        match = await self._rerank_con_llm(candidato, candidatos)
        if match:
            return match

        # CAPA 3 — Fallback matemático, con umbral alto y guarda de colisión.
        return self._fallback_fuzzy(texto_candidato, candidato, candidatos)

    def _match_por_hint(
        self, candidato: str, hints: dict[str, str]
    ) -> SnomedMatch | None:
        if candidato in hints:
            sid = hints[candidato]
            cie10, linaje = self.index.metadatos(sid)
            return SnomedMatch(sid, candidato, 100.0, False, cie10, linaje, "hint_exacto")

        from rapidfuzz import fuzz

        for termino_hint, sid in hints.items():
            hint_limpio = termino_hint.lower()
            if hay_colision(candidato, hint_limpio):
                continue
            if fuzz.token_sort_ratio(candidato, hint_limpio) > self.settings.threshold_hint_fuzzy:
                cie10, linaje = self.index.metadatos(sid)
                return SnomedMatch(
                    sid, termino_hint, 100.0, False, cie10, linaje, "hint_difuso"
                )
        return None

    async def _rerank_con_llm(
        self, candidato: str, candidatos: list[Candidato]
    ) -> SnomedMatch | None:
        opciones_txt = "\n".join(
            f"{i + 1}. {term}" for i, (_, term, _) in enumerate(candidatos)
        )
        prompt = PROMPT_AUDITOR.format(candidato=candidato, opciones=opciones_txt)

        try:
            raw = await self.llm.generar(
                prompt,
                model=self.settings.model_router,
                timeout=self.settings.llm_timeout_fast,
            )
        except LLMUnavailable as exc:
            logger.warning("Re-ranking sin LLM (%s); se usará el fallback", exc)
            return None

        seleccion = raw.strip().replace(".", "").split()
        if not seleccion or not seleccion[0].isdigit():
            return None

        idx = int(seleccion[0])
        if idx == 0 or idx > len(candidatos):
            return None  # El auditor dijo "ninguno". Se respeta.

        sid, termino, score_fuzzy = candidatos[idx - 1]

        # El veredicto del LLM no anula las guardas duras.
        motivo = hay_colision(candidato, termino)
        if motivo:
            logger.info("Selección del LLM bloqueada por %s", motivo)
            return None

        # Un concepto confirmado por el auditor merece alta confianza aunque
        # la similitud literal fuera baja (sinónimos lejanos, siglas).
        confianza = 99.0 if score_fuzzy > 40 else score_fuzzy
        cie10, linaje = self.index.metadatos(sid)
        return SnomedMatch(sid, termino, confianza, False, cie10, linaje, "rerank_llm")

    def _fallback_fuzzy(
        self, original: str, candidato: str, candidatos: list[Candidato]
    ) -> SnomedMatch:
        sid, termino, score = candidatos[0]
        if score < self.settings.threshold_fuzzy_fallback:
            return SnomedMatch.ruido(original, "score_insuficiente")
        if hay_colision(candidato, termino):
            return SnomedMatch.ruido(original, "colision_bloqueada")
        cie10, linaje = self.index.metadatos(sid)
        return SnomedMatch(sid, termino, score, False, cie10, linaje, "fuzzy")


def construir_index(settings: Settings | None = None, db=None) -> SnomedIndex:
    """Elige e inicializa el backend SNOMED según la configuración."""
    settings = settings or get_settings()
    backend = settings.resolve_snomed_backend()

    if backend == "arango":
        index = ArangoSnomedIndex(db, settings)
        if index.disponible():
            logger.info("SNOMED: backend ArangoSearch")
            return index
        logger.warning("SNOMED: Arango pedido pero no disponible; se intenta local")

    local = LocalSnomedIndex(settings)
    ok, detalle = local.cargar()
    logger.info("SNOMED: %s", detalle)
    if not ok and db is not None:
        arango = ArangoSnomedIndex(db, settings)
        if arango.disponible():
            logger.info("SNOMED: se recurre a ArangoSearch")
            return arango
    return local
