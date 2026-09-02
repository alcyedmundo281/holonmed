"""Extracción de registros operativos según el protocolo de cada rol.

Cada actor documenta cosas distintas. Enfermería necesita el horario
indicado y el administrado; farmacia, el lote y las condiciones de
elaboración. En vez de codificar esas diferencias, cada rol declara sus
campos en su propio protocolo —`enfermeria.md`, `farmacia.md`— y este
módulo extrae lo que ese protocolo pide.

Lo importante no es lo que encuentra sino **lo que señala que falta**. Una
causa real de que los procedimientos se queden sin facturar no es que no
se hagan: es que se documentan a medias mientras se está atendiendo, y
nadie se entera hasta que la cuenta ya no cuadra.

Aquí el registro incompleto se detecta en el momento, cuando todavía se
puede corregir.
"""

import logging
from dataclasses import dataclass, field

from ..core.skills import Skill, SkillManager
from ..llm import LLMUnavailable, OllamaClient

logger = logging.getLogger(__name__)


PROMPT_REGISTRO = """Eres un asistente que estructura registros asistenciales.

{protocolo}

CAMPOS A EXTRAER:
{campos}

REGISTRO ESCRITO POR EL PROFESIONAL:
"{texto}"

REGLA ABSOLUTA: **no inventes ningún valor**. Si un campo no consta en el
texto, devuélvelo como null. Un campo vacío se ve y se corrige; un campo
inventado no se ve y contamina el registro.

No deduzcas horarios, dosis ni lotes que no estén escritos. No completes
un nombre a medias. No supongas la vía por el medicamento.

Responde SOLO con un JSON de {{campo: valor}}, usando exactamente los
nombres de campo de la lista.
"""


@dataclass
class RegistroOperativo:
    """Lo extraído de un registro, con lo que falta señalado."""

    rol: str
    campos: dict[str, str] = field(default_factory=dict)
    faltantes: list[str] = field(default_factory=list)

    @property
    def completo(self) -> bool:
        return not self.faltantes

    def resumen(self) -> str:
        if self.completo:
            return f"Registro de {self.rol} completo"
        return f"Registro de {self.rol} incompleto: falta {', '.join(self.faltantes)}"


class ExtractorOperativo:
    """Aplica el protocolo de un rol sobre un registro en texto libre."""

    def __init__(self, skills: SkillManager, llm: OllamaClient, settings=None):
        self.skills = skills
        self.llm = llm
        from ..config import get_settings

        self.settings = settings or get_settings()

    def protocolo_de(self, rol: str) -> Skill | None:
        """Localiza el protocolo declarado para un rol.

        Se busca por el campo `rol` del frontmatter, no por el nombre del
        archivo: un centro puede llamar a sus protocolos como quiera.
        """
        for nombre in self.skills.listar():
            skill = self.skills.cargar(nombre)
            if skill and skill.tipo == "operativo" and skill.rol == rol:
                return skill
        return None

    async def extraer(self, texto: str, rol: str) -> RegistroOperativo:
        skill = self.protocolo_de(rol)
        if not skill or not skill.campos:
            logger.info("Sin protocolo operativo para el rol '%s'", rol)
            return RegistroOperativo(rol=rol)

        descripciones = "\n".join(
            f"- {c.nombre}: {c.titulo}"
            + (f". {c.descripcion}" if c.descripcion else "")
            + (" [OBLIGATORIO]" if c.requerido else "")
            for c in skill.campos
        )

        try:
            datos = await self.llm.generar_json(
                PROMPT_REGISTRO.format(
                    protocolo=skill.contenido[:4000],
                    campos=descripciones,
                    texto=texto,
                ),
                model=self.settings.model_clinical,
                timeout=self.settings.llm_timeout_slow,
            )
        except LLMUnavailable as exc:
            logger.error("Extracción operativa imposible: %s", exc)
            datos = {}

        extraidos: dict[str, str] = {}
        for campo in skill.campos:
            valor = datos.get(campo.nombre)
            if valor is None:
                continue
            texto_valor = str(valor).strip()
            # Los modelos devuelven "null", "N/A" o "" cuando no encuentran
            # algo. Tratarlos como valor convertiría un hueco en un dato.
            if not texto_valor or texto_valor.lower() in {
                "null",
                "none",
                "n/a",
                "no consta",
                "-",
            }:
                continue
            extraidos[campo.nombre] = texto_valor

        faltantes = [
            c.titulo for c in skill.campos_requeridos if c.nombre not in extraidos
        ]
        return RegistroOperativo(rol=rol, campos=extraidos, faltantes=faltantes)
