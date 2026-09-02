"""Índice terminológico sobre SQLite.

Sustituye al índice en memoria de la versión anterior, que cargaba el
vocabulario entero en diccionarios de Python y ejecutaba `rapidfuzz` sobre
**todos** los términos en cada consulta. Con la extensión española de
SNOMED eso son más de un millón de comparaciones por hallazgo, y varios
cientos de MB residentes en el proceso.

Aquí la recuperación es en dos fases:

1. **FTS5** reduce el millón de términos a unas decenas de candidatos,
   usando índice invertido y ranking BM25. Coste logarítmico, dentro de
   SQLite, sin cargar nada en memoria.
2. **rapidfuzz** puntúa sólo esos candidatos. Sigue aportando la tolerancia
   a erratas y variantes morfológicas, pero sobre 50 cadenas en vez de un
   millón.

El vocabulario es intercambiable. El repositorio incluye una semilla propia
que funciona sin descargar nada; SNOMED, HPO o CIE-10 se importan aparte si
tienes la licencia correspondiente.
"""

import json
import logging
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ..db.store import Database, GraphRepo, normalizar

logger = logging.getLogger(__name__)

# Cuántos candidatos devuelve FTS5 antes del re-puntuado difuso. Subirlo
# mejora el recall a costa de llamadas más caras al LLM en el re-ranking.
CANDIDATOS_FTS = 40


@dataclass
class Candidato:
    concepto_id: int
    codigo: str
    sistema: str
    termino: str
    score: float


class TerminologyIndex:
    """Búsqueda de conceptos sobre el vocabulario cargado en SQLite."""

    def __init__(self, db: Database, grafo: GraphRepo):
        self._db = db
        self._grafo = grafo

    def disponible(self) -> bool:
        try:
            return (
                self._db.conexion().execute("SELECT 1 FROM concepto LIMIT 1").fetchone()
                is not None
            )
        except sqlite3.Error:
            return False

    def sistemas_cargados(self) -> dict[str, int]:
        try:
            filas = self._db.conexion().execute(
                "SELECT sistema, COUNT(*) AS n FROM concepto GROUP BY sistema"
            )
            return {f["sistema"]: f["n"] for f in filas}
        except sqlite3.Error:
            return {}

    def buscar_exacto(self, texto: str) -> Candidato | None:
        """Igualdad tras normalizar. Es el camino barato y el más frecuente."""
        fila = (
            self._db.conexion()
            .execute(
                """SELECT c.id, c.codigo, c.sistema, c.termino
                   FROM termino t JOIN concepto c ON c.id = t.concepto_id
                   WHERE t.normalizado = ?
                   ORDER BY t.preferente DESC LIMIT 1""",
                (normalizar(texto),),
            )
            .fetchone()
        )
        if not fila:
            return None
        return Candidato(
            fila["id"], fila["codigo"], fila["sistema"], fila["termino"], 100.0
        )

    def buscar_codigo(self, codigo: str, sistema: str | None = None) -> Candidato | None:
        """Localiza un concepto por su código. Se usa para validar skills."""
        if sistema:
            sql = """SELECT id, codigo, sistema, termino FROM concepto
                     WHERE codigo = ? AND sistema = ? LIMIT 1"""
            args: tuple[str, ...] = (codigo, sistema)
        else:
            sql = "SELECT id, codigo, sistema, termino FROM concepto WHERE codigo = ? LIMIT 1"
            args = (codigo,)
        try:
            fila = self._db.conexion().execute(sql, args).fetchone()
        except sqlite3.Error:
            return None
        if not fila:
            return None
        return Candidato(
            fila["id"], fila["codigo"], fila["sistema"], fila["termino"], 100.0
        )

    def buscar_candidatos(self, texto: str, limite: int = 15) -> list[Candidato]:
        """Recuperación amplia: FTS5 primero, puntuado difuso después."""
        exacto = self.buscar_exacto(texto)
        if exacto:
            return [exacto]

        crudos = self._fts(texto, CANDIDATOS_FTS)
        if not crudos:
            return []

        from rapidfuzz import fuzz

        objetivo = normalizar(texto)
        puntuados: dict[int, Candidato] = {}
        for fila in crudos:
            score = float(fuzz.token_sort_ratio(objetivo, normalizar(fila["texto"])))
            previo = puntuados.get(fila["concepto_id"])
            # Un concepto puede aparecer por varios sinónimos; se queda con
            # la variante que mejor casa con lo que escribió el clínico.
            if previo is None or score > previo.score:
                puntuados[fila["concepto_id"]] = Candidato(
                    fila["concepto_id"],
                    fila["codigo"],
                    fila["sistema"],
                    fila["termino_preferente"],
                    score,
                )

        ordenados = sorted(puntuados.values(), key=lambda c: c.score, reverse=True)
        return [c for c in ordenados if c.score >= 45][:limite]

    def _fts(self, texto: str, limite: int) -> list[sqlite3.Row]:
        consulta = _consulta_fts(texto)
        if not consulta:
            return []
        aql = """
            SELECT t.concepto_id, t.texto, c.codigo, c.sistema,
                   c.termino AS termino_preferente
            FROM termino_fts f
            JOIN termino t ON t.id = f.rowid
            JOIN concepto c ON c.id = t.concepto_id
            WHERE termino_fts MATCH ?
            ORDER BY bm25(termino_fts) LIMIT ?
        """
        try:
            return self._db.conexion().execute(aql, (consulta, limite)).fetchall()
        except sqlite3.Error as exc:
            logger.warning("Consulta FTS falló para '%s': %s", texto[:40], exc)
            return []

    def metadatos(self, concepto_id: int) -> tuple[str | None, str | None]:
        """Código CIE-10 equivalente y concepto padre."""
        cx = self._db.conexion()
        fila = cx.execute(
            """SELECT codigo_destino FROM mapeo
               WHERE concepto_id = ? AND sistema_destino = 'icd10' LIMIT 1""",
            (concepto_id,),
        ).fetchone()
        cie10 = fila["codigo_destino"] if fila else None
        return cie10, self._grafo.padre_inmediato(concepto_id) or "Concepto raíz"

    def cobertura_de_grafo(self, concepto_ids: Iterable[int]) -> set[str]:
        """Los códigos que cubren a esos conceptos: ellos y sus ancestros.

        Es lo que `SkillManager.para_concepto` necesita para responder «¿qué
        protocolos aplican a este paciente?». Un protocolo declara su ámbito
        por una rama —«cualquier hallazgo pancreático»—, así que preguntar
        sólo por el código exacto del hallazgo no lo encontraría nunca: hay
        que subir por la jerarquía.

        Se incluye el concepto propio y no sólo sus padres, porque un
        protocolo puede declarar como ámbito el concepto mismo.
        """
        codigos: set[str] = set()
        for concepto_id in {c for c in concepto_ids if c}:
            fila = (
                self._db.conexion()
                .execute("SELECT codigo FROM concepto WHERE id = ?", (concepto_id,))
                .fetchone()
            )
            if fila and fila["codigo"]:
                codigos.add(fila["codigo"])
            for ancestro in self._grafo.ancestros(concepto_id):
                if ancestro["codigo"]:
                    codigos.add(ancestro["codigo"])
        return codigos


def _consulta_fts(texto: str) -> str:
    """Construye una consulta FTS5 segura a partir de texto libre.

    FTS5 tiene su propia sintaxis con operadores (`NEAR`, `OR`, `-`, `*`,
    comillas). Como el texto viene de la salida de un LLM, se escapa cada
    palabra entre comillas y se unen con OR: cualquier coincidencia parcial
    recupera candidatos, y el puntuado difuso decide después.
    """
    palabras = [p for p in normalizar(texto).replace('"', " ").split() if len(p) > 1]
    if not palabras:
        return ""
    return " OR ".join(f'"{p}"' for p in palabras[:8])


# =====================================================================
# CARGA DE VOCABULARIO
# =====================================================================


class VocabularyLoader:
    """Ingesta de vocabulario en el índice.

    Los cargadores son idempotentes: reejecutarlos actualiza en vez de
    duplicar, porque en la práctica se importa varias veces mientras se
    ajusta un vocabulario.
    """

    def __init__(self, db: Database):
        self._db = db

    def cargar_semilla(self, ruta: Path) -> int:
        """Carga el vocabulario base incluido en el repositorio.

        Es contenido propio del proyecto: términos clínicos en español con
        sus sinónimos y su jerarquía, sin códigos de terminologías con
        licencia. Permite que el validador funcione recién clonado el
        repositorio, sin descargas ni trámites.
        """
        if not ruta.exists():
            logger.warning("No se encontró el vocabulario semilla en %s", ruta)
            return 0

        datos = json.loads(ruta.read_text(encoding="utf-8"))
        conceptos = datos.get("conceptos", [])

        cx = self._db.conexion()
        with self._db._escritura:
            ids: dict[str, int] = {}
            for entrada in conceptos:
                codigo = entrada["codigo"]
                cx.execute(
                    """INSERT INTO concepto (sistema, codigo, termino, semantica)
                       VALUES ('holonmed', ?, ?, ?)
                       ON CONFLICT(sistema, codigo)
                       DO UPDATE SET termino = excluded.termino,
                                     semantica = excluded.semantica""",
                    (codigo, entrada["termino"], entrada.get("semantica")),
                )
                fila = cx.execute(
                    "SELECT id FROM concepto WHERE sistema = 'holonmed' AND codigo = ?",
                    (codigo,),
                ).fetchone()
                ids[codigo] = fila["id"]

                cx.execute("DELETE FROM termino WHERE concepto_id = ?", (fila["id"],))
                variantes = [entrada["termino"], *entrada.get("sinonimos", [])]
                cx.executemany(
                    "INSERT INTO termino (concepto_id, texto, normalizado, preferente) VALUES (?,?,?,?)",
                    [
                        (fila["id"], v, normalizar(v), 1 if i == 0 else 0)
                        for i, v in enumerate(dict.fromkeys(variantes))
                    ],
                )

            # La jerarquía se aplica en una segunda pasada: un concepto
            # puede declarar como padre a otro que aún no existía.
            for entrada in conceptos:
                padre = entrada.get("padre")
                if padre and padre in ids and entrada["codigo"] in ids:
                    cx.execute(
                        "INSERT OR IGNORE INTO es_un (hijo_id, padre_id) VALUES (?, ?)",
                        (ids[entrada["codigo"]], ids[padre]),
                    )

            for entrada in conceptos:
                icd10 = entrada.get("icd10")
                if icd10 and entrada["codigo"] in ids:
                    cx.execute(
                        """INSERT OR IGNORE INTO mapeo (concepto_id, sistema_destino, codigo_destino)
                           VALUES (?, 'icd10', ?)""",
                        (ids[entrada["codigo"]], icd10),
                    )

            cx.commit()

        logger.info("Vocabulario semilla: %d conceptos", len(conceptos))
        return len(conceptos)

    def cargar_rf2(
        self,
        descripciones: Path,
        relaciones: Path | None = None,
        mapa: Path | None = None,
        sistema: str = "snomed",
        lote: int = 20_000,
    ) -> dict[str, int]:
        """Importa una release en formato RF2 (el de SNOMED CT).

        El código para leer RF2 es libre; la terminología no se distribuye
        con este repositorio y requiere tu propia licencia de afiliado.

        Se procesa por lotes con `csv` de la biblioteca estándar en vez de
        cargar un DataFrame: son cientos de MB y no hay motivo para tenerlos
        todos en RAM a la vez.
        """
        import csv

        cx = self._db.conexion()
        totales = {"conceptos": 0, "terminos": 0, "relaciones": 0, "mapeos": 0}

        # --- Descripciones: conceptos y sus sinónimos ---
        vistos: set[str] = set()
        with descripciones.open(encoding="utf-8", newline="") as fh, self._db._escritura:
            lector = csv.DictReader(fh, delimiter="\t")
            pendientes_concepto: list[tuple] = []
            pendientes_termino: list[tuple[str, str]] = []

            for fila in lector:
                if fila.get("active") != "1":
                    continue
                cid, texto = fila["conceptId"], fila["term"]
                if cid not in vistos:
                    vistos.add(cid)
                    pendientes_concepto.append((sistema, cid, texto))
                pendientes_termino.append((cid, texto))

                if len(pendientes_termino) >= lote:
                    self._volcar(
                        cx, sistema, pendientes_concepto, pendientes_termino, totales
                    )
                    pendientes_concepto, pendientes_termino = [], []

            self._volcar(cx, sistema, pendientes_concepto, pendientes_termino, totales)
            cx.commit()

        # --- Relaciones IS_A (typeId 116680003) ---
        if relaciones and relaciones.exists():
            with relaciones.open(encoding="utf-8", newline="") as fh, self._db._escritura:
                lector = csv.DictReader(fh, delimiter="\t")
                pendientes = []
                for fila in lector:
                    if fila.get("active") != "1" or fila.get("typeId") != "116680003":
                        continue
                    pendientes.append(
                        (sistema, fila["sourceId"], sistema, fila["destinationId"])
                    )
                    if len(pendientes) >= lote:
                        totales["relaciones"] += self._volcar_relaciones(cx, pendientes)
                        pendientes = []
                totales["relaciones"] += self._volcar_relaciones(cx, pendientes)
                cx.commit()

        # --- Mapa a CIE-10 ---
        if mapa and mapa.exists():
            with mapa.open(encoding="utf-8", newline="") as fh, self._db._escritura:
                lector = csv.DictReader(fh, delimiter="\t")
                mapeos = []
                for fila in lector:
                    destino = fila.get("mapTarget")
                    if fila.get("active") != "1" or not destino:
                        continue
                    mapeos.append((sistema, fila["referencedComponentId"], destino))
                    if len(mapeos) >= lote:
                        totales["mapeos"] += self._volcar_mapeos(cx, mapeos)
                        mapeos = []
                totales["mapeos"] += self._volcar_mapeos(cx, mapeos)
                cx.commit()

        cx.execute("INSERT INTO termino_fts(termino_fts) VALUES ('optimize')")
        cx.commit()
        return totales

    @staticmethod
    def _volcar(cx, sistema, conceptos, terminos, totales) -> None:
        if conceptos:
            cx.executemany(
                """INSERT INTO concepto (sistema, codigo, termino) VALUES (?,?,?)
                   ON CONFLICT(sistema, codigo) DO NOTHING""",
                conceptos,
            )
            totales["conceptos"] += len(conceptos)
        if terminos:
            cx.executemany(
                """INSERT INTO termino (concepto_id, texto, normalizado, preferente)
                   SELECT id, ?2, ?3, 0 FROM concepto WHERE sistema = ?4 AND codigo = ?1""",
                [(cid, texto, normalizar(texto), sistema) for cid, texto in terminos],
            )
            totales["terminos"] += len(terminos)

    @staticmethod
    def _volcar_relaciones(cx, pendientes) -> int:
        if not pendientes:
            return 0
        cx.executemany(
            """INSERT OR IGNORE INTO es_un (hijo_id, padre_id)
               SELECT h.id, p.id FROM concepto h, concepto p
               WHERE h.sistema = ?1 AND h.codigo = ?2
                 AND p.sistema = ?3 AND p.codigo = ?4""",
            pendientes,
        )
        return len(pendientes)

    @staticmethod
    def _volcar_mapeos(cx, pendientes) -> int:
        if not pendientes:
            return 0
        cx.executemany(
            """INSERT OR IGNORE INTO mapeo (concepto_id, sistema_destino, codigo_destino)
               SELECT id, 'icd10', ?3 FROM concepto WHERE sistema = ?1 AND codigo = ?2""",
            pendientes,
        )
        return len(pendientes)
