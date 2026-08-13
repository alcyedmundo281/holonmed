"""Órdenes propuestas a partir del plan, que el médico autoriza o descarta.

El modelo lee el plan y propone las órdenes que ve. **No las crea.** Una
propuesta no autoriza nada: es un borrador que espera una firma, igual que
un pull request espera una revisión.

Esa separación no es cortesía sino la condición para que el resto del
sistema se sostenga. Toda la cadena de facturación se apoya en que la
orden es un acto de autorización de una persona; si un modelo pudiera
crear órdenes, ese apoyo desaparecería y con él la trazabilidad entera.

Por eso la propuesta:

* No se guarda como orden ni tiene identificador de orden.
* Cita el fragmento del plan del que sale, para que revisarla sea leer una
  línea y no reconstruir el razonamiento.
* Señala lo que no pudo determinar —una dosis que no consta— en vez de
  rellenarlo, porque un borrador con huecos visibles se corrige y uno con
  huecos inventados se firma sin mirar.
"""

import logging
from dataclasses import dataclass, field

from ..core.skills import SkillManager
from ..llm import LLMUnavailable, OllamaClient
from .modelos import Orden

logger = logging.getLogger(__name__)


PROMPT_ORDENES = """Eres un asistente que estructura el PLAN de una nota clínica.

Lee el plan y extrae las órdenes que contiene: medicamentos, pruebas,
procedimientos, interconsultas, cuidados.

{catalogo}

PLAN:
"{texto}"

REGLAS:

1. Una orden es algo que **se manda hacer**. «Continúa con dieta absoluta»
   es una orden; «el paciente refiere dolor» no lo es.
2. **No inventes lo que no está.** Si no consta la dosis, deja el campo
   vacío. Un borrador con huecos se corrige; uno relleno a ojo se firma
   sin mirar y acaba administrándose.
3. Si la orden es un medicamento, `termino` es **el nombre del fármaco tal
   como aparece en el plan**: «morfina», «ondansetrón». Nunca «medicamento»,
   «analgesia», «antiemético» ni la vía. Quien lee la orden tiene que saber
   qué se administra, y una categoría no se puede administrar.
4. No conviertas una sola orden en varias ni fundas varias en una.
5. Usa el término del catálogo cuando encaje; si no, el del texto.
6. Cita en `texto_origen` el fragmento exacto del plan del que sale cada
   orden, para que se pueda revisar sin releerlo todo.

Responde SOLO con JSON:
{{"ordenes": [{{"termino": "...", "texto_origen": "cita exacta",
  "dosis": "...", "via": "...", "frecuencia": "...", "duracion": "..."}}]}}
"""


@dataclass
class OrdenPropuesta:
    """Un borrador de orden. No autoriza nada hasta que alguien la firma."""

    termino: str
    texto_origen: str = ""
    detalle: dict[str, str] = field(default_factory=dict)
    codigo: str | None = None
    sistema: str | None = None
    concepto_id: int | None = None
    reconocida: bool = False
    faltantes: list[str] = field(default_factory=list)
    generico: bool = False

    @property
    def resumen(self) -> str:
        partes = [self.termino]
        for clave in ("dosis", "via", "frecuencia", "duracion"):
            if self.detalle.get(clave):
                partes.append(self.detalle[clave])
        return " · ".join(partes)

    def a_orden(self, paciente_id: str, prescriptor: str | None = None) -> Orden:
        """Convierte el borrador en una orden real.

        Sólo debe llamarse cuando una persona lo ha autorizado: es el paso
        en el que un texto propuesto por un modelo se convierte en algo que
        obliga a otros a actuar y habilita un cargo.
        """
        return Orden(
            paciente_id=paciente_id,
            termino=self.termino,
            codigo=self.codigo,
            sistema=self.sistema,
            concepto_id=self.concepto_id,
            texto_origen=self.texto_origen,
            prescriptor=prescriptor,
            detalle=dict(self.detalle),
        )


# Campos cuya ausencia conviene señalar en una orden de medicación. No se
# exigen siempre: pedir dosis a «interconsulta a cirugía» sería ruido.
CLAVES_MEDICACION = ("dosis", "via", "frecuencia")

# Categorías que un modelo devuelve cuando no se compromete con el fármaco.
# Una categoría no se puede administrar, así que la propuesta se marca para
# que nadie la firme sin escribir qué es. No se corrige sola: adivinar el
# medicamento es exactamente lo que no debe hacer.
GENERICOS = {
    "medicamento",
    "medicacion",
    "medicación",
    "farmaco",
    "fármaco",
    "analgesia",
    "analgesico",
    "analgésico",
    "antibiotico",
    "antibiótico",
    "antiemetico",
    "antiemético",
    "tratamiento",
    "medida",
}


class ProponedorOrdenes:
    """Extrae órdenes candidatas del plan, sin crear ninguna."""

    def __init__(self, skills: SkillManager, llm: OllamaClient, terminologia, settings=None):
        self.skills = skills
        self.llm = llm
        self.terminologia = terminologia
        from ..config import get_settings

        self.settings = settings or get_settings()

    async def proponer(self, texto_plan: str) -> list[OrdenPropuesta]:
        catalogo = self._catalogo()
        try:
            datos = await self.llm.generar_json(
                PROMPT_ORDENES.format(catalogo=catalogo, texto=texto_plan),
                model=self.settings.model_clinical,
                timeout=self.settings.llm_timeout_slow,
            )
        except LLMUnavailable as exc:
            logger.error("No se pudieron proponer órdenes: %s", exc)
            return []

        crudas = datos.get("ordenes")
        if not isinstance(crudas, list):
            return []

        propuestas = []
        for cruda in crudas:
            if not isinstance(cruda, dict):
                continue
            termino = str(cruda.get("termino", "")).strip()
            if not termino:
                continue

            detalle = {
                clave: str(cruda[clave]).strip()
                for clave in ("dosis", "via", "frecuencia", "duracion")
                if cruda.get(clave) and str(cruda[clave]).strip().lower()
                not in {"null", "none", "n/a", "-"}
            }

            propuesta = OrdenPropuesta(
                termino=termino,
                texto_origen=str(cruda.get("texto_origen", "")).strip(),
                detalle=detalle,
            )

            # Se resuelve contra el vocabulario para que después encuentre
            # su código tarifario. Que no se reconozca no la invalida: se
            # marca, y el médico decide.
            concepto = self.terminologia.buscar_exacto(termino)
            if concepto:
                propuesta.concepto_id = concepto.concepto_id
                propuesta.codigo, propuesta.sistema = concepto.codigo, concepto.sistema
                propuesta.termino = concepto.termino
                propuesta.reconocida = True

            if detalle.get("dosis"):
                propuesta.faltantes = [
                    c for c in CLAVES_MEDICACION if not detalle.get(c)
                ]

            propuesta.generico = termino.strip().lower() in GENERICOS

            propuestas.append(propuesta)

        return propuestas

    def _catalogo(self) -> str:
        """Procedimientos que el sistema sabe codificar.

        Orientar al modelo hacia ellos mejora que la orden encuentre su
        código, pero no se le prohíbe salirse: un plan puede contener algo
        que el catálogo no cubre y ocultarlo sería peor.
        """
        terminos = []
        for nombre in self.skills.listar():
            skill = self.skills.cargar(nombre)
            if not skill:
                continue
            for p in skill.meta.get("procedimientos") or []:
                if isinstance(p, dict) and p.get("nombre"):
                    terminos.append(str(p["nombre"]))
        if not terminos:
            return ""
        unicos = sorted(set(terminos))
        return (
            "PROCEDIMIENTOS QUE EL SISTEMA RECONOCE (úsalos si encajan, pero "
            f"no te limites a ellos):\n{', '.join(unicos)}\n"
        )
