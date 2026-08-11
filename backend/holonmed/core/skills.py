"""Skills clínicas: los protocolos que el sistema puede activar.

Una *skill* es un archivo Markdown con bloques JSON-LD embebidos. El texto
narrativo instruye al LLM; el JSON-LD aporta conocimiento estructurado que
el código consume directamente:

* `signDetected[]`  — signos con su `snomed_id` y su likelihood ratio.
* `criterios_laboratorio` — cortes numéricos y el término clínico que
  corresponde cuando un valor los cruza.
* `modelo_bayesiano` — probabilidad base y factores de riesgo a priori.

De ahí salen los *skill-hints*: un diccionario término→SNOMED ID revisado
por un humano, que tiene prioridad sobre cualquier búsqueda difusa.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from ..config import Settings, get_settings
from ..llm import OllamaClient

logger = logging.getLogger(__name__)

SKILL_POR_DEFECTO = "general_triage"


class Skill:
    """Un protocolo clínico cargado y parseado."""

    def __init__(self, nombre: str, contenido: str):
        self.nombre = nombre
        self.contenido = contenido
        self._bloques: list[dict[str, Any]] | None = None

    @property
    def descripcion(self) -> str:
        """Primera línea del Markdown, usada en el menú de triaje."""
        for linea in self.contenido.splitlines():
            limpia = linea.strip().lstrip("#").strip()
            if limpia:
                return limpia
        return self.nombre

    @property
    def bloques_json(self) -> list[dict[str, Any]]:
        """Todos los objetos JSON válidos embebidos en el Markdown."""
        if self._bloques is None:
            self._bloques = self._parsear_bloques()
        return self._bloques

    def _parsear_bloques(self) -> list[dict[str, Any]]:
        # Los skills se editan a mano y llegan con basura de copiar/pegar:
        # espacios no separables, escapes de Markdown, vallas de código.
        limpio = (
            self.contenido.replace("&nbsp;", " ")
            .replace("\xa0", " ")
            .replace("\\", "")
        )
        bloques: list[dict[str, Any]] = []

        # Se recorren candidatos de mayor a menor: un JSON-LD anidado se
        # captura entero en el primer intento.
        for match in re.finditer(r"\{.*?\}(?=\s*(?:\n\s*\n|$|#))", limpio, re.DOTALL):
            fragmento = match.group(0)
            try:
                data = json.loads(fragmento)
                if isinstance(data, dict):
                    bloques.append(data)
            except json.JSONDecodeError:
                continue

        if not bloques:
            # Segundo intento, más glotón: del primer `{` al último `}`.
            inicio, fin = limpio.find("{"), limpio.rfind("}")
            if inicio != -1 and fin > inicio:
                try:
                    data = json.loads(limpio[inicio : fin + 1])
                    if isinstance(data, dict):
                        bloques.append(data)
                except json.JSONDecodeError:
                    logger.debug("Skill '%s' sin JSON-LD parseable", self.nombre)
        return bloques

    @property
    def json_principal(self) -> dict[str, Any]:
        """El bloque que describe la condición (el que alimenta a Bayes)."""
        for bloque in self.bloques_json:
            if "modelo_bayesiano" in bloque or "signDetected" in bloque:
                return bloque
        return self.bloques_json[0] if self.bloques_json else {}

    def hints_snomed(self) -> dict[str, str]:
        """Diccionario término→SNOMED ID extraído del conocimiento del skill."""
        hints: dict[str, str] = {}

        def registrar(nombre: str | None, codigo: str | None) -> None:
            if nombre and codigo:
                hints[str(nombre).strip().lower()] = str(codigo)

        for bloque in self.bloques_json:
            entidades: list[dict[str, Any]] = [bloque]
            for clave in ("@graph", "containsProblem"):
                valor = bloque.get(clave)
                if isinstance(valor, list):
                    entidades.extend(e for e in valor if isinstance(e, dict))

            for entidad in entidades:
                for signo in entidad.get("signDetected", []) or []:
                    if not isinstance(signo, dict):
                        continue
                    codigo = signo.get("snomed_id") or (
                        signo.get("code", {}).get("codeValue")
                        if isinstance(signo.get("code"), dict)
                        else None
                    )
                    registrar(signo.get("name"), codigo)

                criterios = entidad.get("criterios_laboratorio")
                if isinstance(criterios, dict):
                    for regla in criterios.get("reglas", []) or []:
                        if not isinstance(regla, dict):
                            continue
                        codigo = regla.get("snomed_id") or entidad.get("snomed_id")
                        registrar(regla.get("termino_si_alto"), codigo)
                        registrar(regla.get("termino_si_bajo"), codigo)

        return hints

    def vocabulario_preferido(self) -> list[str]:
        """Términos que el skill prefiere, para guiar la extracción del LLM."""
        nombres = re.findall(r'"name":\s*"([^"]+)"', self.contenido)
        return sorted(set(nombres))


class SkillManager:
    """Descubre, carga y selecciona skills."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.directorio = Path(self.settings.skills_dir)
        self.directorio.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Skill] = {}

    def listar(self) -> list[str]:
        return sorted(p.stem for p in self.directorio.glob("*.md"))

    def catalogo(self) -> str:
        """Menú legible que se le presenta al triaje."""
        lineas = []
        for nombre in self.listar():
            skill = self.cargar(nombre)
            if skill:
                lineas.append(f"- {nombre}: {skill.descripcion}")
        return "\n".join(lineas) or f"- {SKILL_POR_DEFECTO}: Triaje general"

    def cargar(self, nombre: str) -> Skill | None:
        # El nombre puede venir de una respuesta del LLM: se sanea contra
        # traversal antes de tocar el sistema de archivos.
        limpio = Path(nombre.strip().strip("'\"")).name
        if limpio.endswith(".md"):
            limpio = limpio[:-3]
        if not limpio or limpio.startswith("."):
            return None

        if limpio in self._cache:
            return self._cache[limpio]

        ruta = self.directorio / f"{limpio}.md"
        try:
            ruta_real = ruta.resolve()
            if self.directorio.resolve() not in ruta_real.parents:
                logger.warning("Ruta de skill fuera del directorio: %s", nombre)
                return None
            contenido = ruta_real.read_text(encoding="utf-8")
        except (OSError, ValueError):
            return None

        skill = Skill(limpio, contenido)
        self._cache[limpio] = skill
        return skill

    def cargar_o_defecto(self, nombre: str | None) -> Skill:
        skill = self.cargar(nombre) if nombre else None
        if skill:
            return skill
        defecto = self.cargar(SKILL_POR_DEFECTO)
        if defecto:
            return defecto
        # Último recurso: un skill vacío mantiene el pipeline vivo.
        return Skill(SKILL_POR_DEFECTO, "# Triaje general\nExtrae hallazgos clínicos.")

    async def triaje(self, texto_clinico: str, llm: OllamaClient) -> str:
        """Decide qué protocolo activar. El *primer tic* del sistema."""
        disponibles = self.listar()
        if not disponibles:
            return SKILL_POR_DEFECTO
        if len(disponibles) == 1:
            return disponibles[0]

        prompt = f"""TAREA: clasifica el texto clínico en uno de estos protocolos.

PROTOCOLOS DISPONIBLES:
{self.catalogo()}

TEXTO: "{texto_clinico[:500]}"

Responde ÚNICAMENTE con el nombre exacto del protocolo, sin explicación.
Si ninguno encaja claramente, responde: {SKILL_POR_DEFECTO}
PROTOCOLO:"""

        return await llm.elegir_opcion(
            prompt,
            opciones_validas=disponibles,
            defecto=(
                SKILL_POR_DEFECTO if SKILL_POR_DEFECTO in disponibles else disponibles[0]
            ),
        )
