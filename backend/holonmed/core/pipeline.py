"""El pipeline de cristalización: de narrativa libre a infones validados.

Aquí es donde los dos proyectos se encuentran. HolonMed aportaba el rigor
del validador de tres capas pero corría en un script de Streamlit;
InfonMed aportaba la API, la persistencia y la interfaz pero validaba con
una sola búsqueda difusa. Este módulo pone el motor de HolonMed dentro del
cuerpo de InfonMed.

Un *tic* es un ciclo completo:

    triaje → extracción → validación (3 capas) → inferencia bayesiana

Principio de diseño: cada etapa degrada de forma segura. Si el triaje
falla se usa el protocolo general; si el LLM cae la extracción devuelve
vacío en vez de inventar; si el validador no puede confirmar un hallazgo
lo marca como ruido en lugar de dejarlo pasar. El sistema prefiere no
decir nada antes que decir algo falso.
"""

import logging

from ..config import Settings, get_settings
from ..llm import LLMUnavailable, OllamaClient
from ..models import (
    EstadoInfon,
    HolonPaciente,
    Infon,
    Polaridad,
    ResultadoTic,
)
from .acoplamiento import MedidorDeAcoplamiento
from .bayes import AntigenPresentingCell
from .clasificacion import Clasificador
from .skills import Skill, SkillManager
from .validator import OntologyValidator
from .verifier import ClinicalVerifier

logger = logging.getLogger(__name__)

# Peso de cada capa en la confianza final. La ontología pesa más porque es
# determinista: o el concepto existe en SNOMED o no. La auditoría lógica
# depende del juicio de un LLM y por eso pondera menos.
PESO_ONTOLOGICO = 0.6
PESO_LOGICO = 0.4


PROMPT_EXTRACCION = """{protocolo}

---
ROL: ANALISTA CLÍNICO
Lee la narrativa del paciente y extrae hallazgos médicos ATÓMICOS.

{vocabulario}

REGLA DE ORO PARA LABORATORIO:
No extraigas números sueltos: INTERPRÉTALOS con los 'criterios_laboratorio'
del protocolo de arriba.
- "Calcio 7.5"        -> termino_clinico: "Hipocalcemia"
- "Leucocitos 18.500" -> termino_clinico: "Leucocitosis"
- "FC 115"            -> termino_clinico: "Taquicardia"
- Si el texto ya trae la interpretación ("hipocalcemia leve"), úsala.

REGLAS DE PRECISIÓN:
1. IDIOMA: español técnico.
2. ATOMICIDAD: un hallazgo por infón.
3. GRANULARIDAD: no sustituyas un síntoma por una enfermedad.
   "Dolor epigástrico" NO es "Pancreatitis". Extrae el síntoma.
4. BIOQUÍMICA: no confundas amilasa con lipasa, ni enzimas con lípidos.
5. VOCABULARIO: si el protocolo tiene el término exacto, úsalo.
6. LIMPIEZA: sólo el nombre del hallazgo ("Hiperamilasemia", no "Amilasa 1200").
7. POLARIDAD — esto es importante y tiene tres casos, no dos:
   - El texto AFIRMA el hallazgo -> "presente": true
     «vómitos repetidos», «amilasa 1200»
   - El texto lo NIEGA o lo da por normal -> "presente": false
     «no refiere fiebre», «sin dolor torácico», «lipasa 45» (normal)
     Estos NO se descartan: una prueba negativa es evidencia, y de las
     fuertes. Extráelos con presente=false.
   - El texto NO DICE NADA del hallazgo -> no lo extraigas en absoluto.
     No inventes ausencias. Que no se mencione algo no significa que no
     esté: significa que no se sabe, y eso no es un hallazgo.

FORMATO JSON:
{{"resumen": "una frase clínica", "infones": [{{"texto_origen": "cita textual", "termino_clinico": "término normalizado", "presente": true}}]}}"""


class CrystallizationPipeline:
    """Orquesta el ciclo completo de un tic clínico."""

    def __init__(
        self,
        llm: OllamaClient,
        skills: SkillManager,
        validador: OntologyValidator,
        verificador: ClinicalVerifier,
        bayes: AntigenPresentingCell | None = None,
        settings: Settings | None = None,
        clasificador: Clasificador | None = None,
        acoplamiento: MedidorDeAcoplamiento | None = None,
    ):
        self.llm = llm
        self.skills = skills
        self.validador = validador
        self.verificador = verificador
        self.bayes = bayes or AntigenPresentingCell()
        self.clasificador = clasificador or Clasificador()
        self.acoplamiento = acoplamiento or MedidorDeAcoplamiento()
        self.settings = settings or get_settings()

    async def ejecutar(
        self,
        texto: str,
        holon: HolonPaciente,
        skill_forzada: str | None = None,
    ) -> ResultadoTic:
        # --- ETAPA 1: TRIAJE ------------------------------------------
        if skill_forzada:
            skill = self.skills.cargar_o_defecto(skill_forzada)
        else:
            try:
                nombre = await self.skills.triaje(texto, self.llm)
            except LLMUnavailable:
                nombre = None
            skill = self.skills.cargar_o_defecto(nombre)
        logger.info("Tic para %s — protocolo: %s", holon.paciente_id, skill.nombre)

        resultado = ResultadoTic(
            paciente_id=holon.paciente_id,
            texto_original=texto,
            skill_activa=skill.nombre,
        )

        # --- ETAPA 2: EXTRACCIÓN --------------------------------------
        extraidos, resumen = await self._extraer(texto, skill)
        resultado.resumen = resumen
        if not extraidos:
            logger.info("Sin hallazgos extraíbles en el tic")
            return resultado

        # --- ETAPA 3: VALIDACIÓN DE TRES CAPAS ------------------------
        hints = skill.hints_snomed()
        for crudo in extraidos:
            infon = await self._validar_hallazgo(crudo, texto, skill, hints)
            if infon:
                resultado.infones.append(infon)

        # --- ETAPA 4: CLASIFICACIÓN -----------------------------------
        # De hallazgos a trastorno, por criterios publicados. Es el paso
        # que acuña un término nuevo, y lo hace Python: es lógica sobre
        # evidencia validada, no una apreciación del modelo.
        try:
            resultado.clasificacion = self.clasificador.evaluar(
                skill, resultado.infones
            )
            if resultado.clasificacion and resultado.clasificacion.trastorno:
                resultado.infones.append(resultado.clasificacion.trastorno)
        except Exception:  # noqa: BLE001 — un fallo aquí no anula el tic
            logger.exception("Clasificador falló; el tic conserva sus infones")

        # --- ETAPA 5: INFERENCIA ABDUCTIVA ----------------------------
        try:
            resultado.inferencia = self.bayes.calcular(
                holon.metadatos_para_bayes(texto),
                skill.json_principal,
                resultado.infones,
            )
        except Exception:  # noqa: BLE001 — un fallo de Bayes no anula el tic
            logger.exception("Motor bayesiano falló; el tic conserva sus infones")

        # --- ETAPA 6: VALIDACIÓN SEMIÓTICA ----------------------------
        # Bayes ya dijo cuánta evidencia hay. Falta la otra pregunta: si
        # esta hipótesis, tomada como regla de acción, armoniza con el
        # paciente entero o deja fricción. Es aritmética determinista
        # sobre lo que las etapas anteriores ya auditaron — ninguna
        # llamada más al modelo — y en ningún caso toca la probabilidad.
        try:
            resultado.acoplamiento = self.acoplamiento.medir(
                skill,
                # Se mide contra el paciente completo, no sólo contra el
                # texto de hoy: una hipótesis puede encajar en la consulta
                # de esta mañana y desentonar con el hallazgo de la
                # semana pasada. Esa desafinación es justo lo que Φ existe
                # para hacer visible.
                list(holon.linea_tiempo) + resultado.infones,
                resultado.inferencia,
            )
        except Exception:  # noqa: BLE001 — un fallo de Φ no anula el tic
            logger.exception("Medidor de acoplamiento falló; el tic sigue en pie")

        return resultado

    async def _extraer(self, texto: str, skill: Skill):
        """Etapa 2: el LLM propone hallazgos. Nada se da por bueno todavía."""
        vocabulario = ""
        preferidos = skill.vocabulario_preferido()
        if preferidos:
            vocabulario = f"VOCABULARIO PREFERIDO: {preferidos}"

        prompt = PROMPT_EXTRACCION.format(
            protocolo=skill.para_prompt(self.settings.formato_protocolo)[:8000],
            vocabulario=vocabulario,
        )

        try:
            data = await self.llm.generar_json(
                f"{prompt}\n\nNARRATIVA CLÍNICA:\n{texto}\n\nJSON:",
                model=self.settings.model_clinical,
                timeout=self.settings.llm_timeout_slow,
                num_ctx=8192,
            )
        except LLMUnavailable as exc:
            logger.error("Extracción imposible: %s", exc)
            return [], f"Extracción no disponible: {exc}"

        crudos = data.get("infones")
        if not isinstance(crudos, list):
            return [], data.get("resumen", "")

        limpios = [
            item
            for item in crudos
            if isinstance(item, dict) and str(item.get("termino_clinico", "")).strip()
        ]
        return limpios, str(data.get("resumen", ""))

    async def _validar_hallazgo(
        self,
        crudo: dict[str, str],
        texto_original: str,
        skill: Skill,
        hints: dict[str, str],
    ) -> Infon | None:
        termino = str(crudo.get("termino_clinico", "")).strip()
        cita = str(crudo.get("texto_origen", "")).strip()
        if not termino:
            return None

        # Por defecto presente: si el modelo no se pronuncia, no vamos a
        # inventarle una ausencia, que es la dirección peligrosa.
        presente = crudo.get("presente", True)
        polaridad = (
            Polaridad.AUSENTE if presente is False else Polaridad.PRESENTE
        )

        # CAPAS 0-1-2: ¿existe este concepto en la ontología?
        match = await self.validador.validar(termino, hints=hints)

        # CAPA 3: ¿lo sostiene la evidencia? Sólo se audita si la ontología
        # dio una señal mínima — auditar ruido es gastar cómputo en nada.
        certeza_logica = 0.0
        razon = "No auditado (score ontológico insuficiente)"
        es_logico = False

        if match.score >= self.settings.threshold_audit:
            auditoria = await self.verificador.auditar(
                termino,
                texto_original,
                skill.para_prompt(self.settings.formato_protocolo),
                ausente=(polaridad is Polaridad.AUSENTE),
            )
            es_logico = auditoria.es_valido
            razon = auditoria.razon
            certeza_logica = auditoria.certeza

        # Veredicto
        if match.score >= self.settings.threshold_validated and es_logico:
            estado = EstadoInfon.VALIDADO
            confianza = match.score * PESO_ONTOLOGICO + certeza_logica * PESO_LOGICO
        elif match.score >= self.settings.threshold_alert:
            # Acierto ontológico sin respaldo lógico: se muestra al clínico
            # marcado, nunca se descarta en silencio ni se da por bueno.
            estado = EstadoInfon.ALERTA
            confianza = match.score
        else:
            estado = EstadoInfon.RUIDO
            confianza = match.score

        # Un infón descartado conserva lo que dijo el clínico, no lo que el
        # motor estuvo a punto de elegir: mostrar "otro concepto" donde el
        # médico escribió "coluria" confundiría al revisar el descarte. El
        # casi-match queda en la traza, que es donde sirve para auditar.
        if estado == EstadoInfon.RUIDO:
            termino_final = termino
            concepto_id = codigo = sistema = cie10 = linaje = None
            if match.codigo:
                razon = f"descartado (casi coincidió con '{match.termino}'): {razon}"
        else:
            termino_final = match.termino
            concepto_id, codigo, sistema = match.concepto_id, match.codigo, match.sistema
            cie10, linaje = match.cie10, match.linaje

        return Infon(
            texto_origen=cita or texto_original[:120],
            termino_propuesto=termino,
            termino=termino_final,
            polaridad=polaridad,
            codigo=codigo,
            sistema=sistema,
            concepto_id=concepto_id,
            cie10_code=cie10,
            linaje_clinico=linaje,
            estado=estado,
            confianza=round(confianza, 2),
            score_ontologico=round(match.score, 2),
            score_logico=round(certeza_logica, 2),
            razon_auditoria=f"[{match.metodo}] {razon}",
            origen_skill=skill.nombre,
        )
