"""Tests del pipeline de cristalización con dobles de prueba.

No se necesita Ollama ni ningún vocabulario cargado: se sustituyen el LLM y
el índice por dobles deterministas. Lo que se verifica es la máquina de
estados del validador, que es donde vive la seguridad clínica del sistema.
"""

import pytest

from holonmed.config import Settings
from holonmed.core.pipeline import CrystallizationPipeline
from holonmed.core.skills import SkillManager
from holonmed.core.terminology import Candidato
from holonmed.core.validator import OntologyValidator
from holonmed.core.verifier import ClinicalVerifier
from holonmed.models import EstadoInfon, HolonPaciente

SKILL = """# SKILL: PRUEBA

{
    "name": "Condición de prueba",
    "modelo_bayesiano": {"probabilidad_base": 0.1},
    "signDetected": [{"name": "Fiebre", "snomed_id": "386661006", "bayes_lr": 3.0}]
}
"""


def extraccion_de(termino: str, cita: str = "cita textual"):
    return {"resumen": "…", "infones": [{"texto_origen": cita, "termino_clinico": termino}]}


# Término deliberadamente ausente de los skill-hints del protocolo de
# prueba: obliga al pipeline a pasar por el índice y el re-ranking en vez
# de resolverse en la capa 0.
TERMINO_SIN_HINT = "Coluria"


class LLMFalso:
    """Devuelve respuestas predefinidas según lo que pida el prompt."""

    def __init__(self, extraccion=None, auditoria_valida=True, rerank="1"):
        self.extraccion = (
            extraccion if extraccion is not None else extraccion_de("Fiebre", "38.5 °C")
        )
        self.auditoria_valida = auditoria_valida
        self.rerank = rerank

    async def generar(self, prompt, **kwargs):
        if "Auditor de Terminología" in prompt:
            return self.rerank
        return "general_triage"

    async def generar_json(self, prompt, **kwargs):
        if "Auditor Médico" in prompt:
            return {
                "valido": self.auditoria_valida,
                "analisis": "38.5 supera el corte de 38.0",
                "confianza": 92,
            }
        return self.extraccion

    async def elegir_opcion(self, prompt, *, opciones_validas, defecto, **kwargs):
        return defecto


class IndexFalso:
    """Índice terminológico con un score fijo y controlable."""

    def __init__(self, score=95.0, termino="Fiebre", codigo="386661006", exacto=False):
        self.score = score
        self.termino = termino
        self.codigo = codigo
        self.exacto = exacto

    def disponible(self):
        return True

    def buscar_exacto(self, texto):
        if not self.exacto:
            return None
        return Candidato(1, self.codigo, "holonmed", self.termino, 100.0)

    def buscar_candidatos(self, texto, limite=15):
        return [Candidato(1, self.codigo, "holonmed", self.termino, self.score)]

    def metadatos(self, concepto_id):
        return "R50.9", "Signo clínico"


@pytest.fixture
def entorno(tmp_path):
    (tmp_path / "general_triage.md").write_text(SKILL, encoding="utf-8")
    settings = Settings(skills_dir=tmp_path, docs_dir=tmp_path / "docs")

    def construir(llm, index):
        return CrystallizationPipeline(
            llm=llm,
            skills=SkillManager(settings),
            validador=OntologyValidator(index, llm, settings),
            verificador=ClinicalVerifier(llm, settings),
            settings=settings,
        )

    return construir


async def test_un_hallazgo_solido_queda_validado(entorno):
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))

    assert len(resultado.infones) == 1
    infon = resultado.infones[0]
    assert infon.estado == EstadoInfon.VALIDADO
    assert infon.codigo == "386661006"
    assert infon.sistema == "holonmed"
    assert infon.cie10_code == "R50.9"
    assert infon.es_facturable


async def test_un_skill_hint_tiene_prioridad_sobre_el_indice(entorno):
    """Un código verificado por un humano gana a la similitud del motor.

    El índice devuelve un score bajísimo, pero 'Fiebre' está en los
    signDetected del protocolo, así que se resuelve en la capa 0.
    """
    pipeline = entorno(LLMFalso(), IndexFalso(score=5.0, exacto=True))
    resultado = await pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))

    infon = resultado.infones[0]
    assert infon.estado == EstadoInfon.VALIDADO
    assert "hint_exacto" in infon.razon_auditoria


async def test_un_hint_sin_vocabulario_cargado_sigue_valiendo(entorno):
    """El protocolo puede citar códigos de un vocabulario no importado.

    El hint sigue siendo válido porque lo revisó un humano, pero no puede
    ofrecer linaje ni mapeo, y eso debe verse en el resultado.
    """
    pipeline = entorno(LLMFalso(), IndexFalso(score=5.0, exacto=False))
    resultado = await pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))

    infon = resultado.infones[0]
    assert infon.estado == EstadoInfon.VALIDADO
    assert infon.codigo == "386661006"
    assert infon.sistema == "skill"
    assert infon.linaje_clinico is None


async def test_acierto_ontologico_sin_respaldo_logico_da_alerta(entorno):
    """El concepto existe, pero la evidencia no lo sostiene: no se valida."""
    pipeline = entorno(LLMFalso(auditoria_valida=False), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar("Texto ambiguo", HolonPaciente(paciente_id="t"))

    infon = resultado.infones[0]
    assert infon.estado == EstadoInfon.ALERTA
    assert not infon.es_valido
    assert not infon.es_facturable


async def test_score_ontologico_bajo_se_marca_como_ruido(entorno):
    pipeline = entorno(
        LLMFalso(extraccion=extraccion_de(TERMINO_SIN_HINT)),
        IndexFalso(score=30.0, termino="otro concepto", codigo="999"),
    )
    resultado = await pipeline.ejecutar("Texto", HolonPaciente(paciente_id="t"))

    infon = resultado.infones[0]
    assert infon.estado == EstadoInfon.RUIDO
    assert resultado.infones_validados == []


async def test_el_ruido_conserva_lo_que_dijo_el_clinico(entorno):
    """Un descarte no debe mostrar un término que el médico nunca escribió."""
    pipeline = entorno(
        LLMFalso(extraccion=extraccion_de(TERMINO_SIN_HINT)),
        IndexFalso(score=10.0, termino="otro concepto", codigo="999"),
    )
    resultado = await pipeline.ejecutar("Texto", HolonPaciente(paciente_id="t"))

    infon = resultado.infones[0]
    assert len(resultado.infones_descartados) == 1
    assert infon.termino == TERMINO_SIN_HINT
    assert infon.codigo is None
    assert "casi coincidió" in infon.razon_auditoria


async def test_una_extraccion_vacia_no_rompe_el_tic(entorno):
    pipeline = entorno(LLMFalso(extraccion={"infones": []}), IndexFalso())
    resultado = await pipeline.ejecutar("Sin hallazgos", HolonPaciente(paciente_id="t"))

    assert resultado.infones == []
    assert resultado.skill_activa == "general_triage"


async def test_el_auditor_puede_rechazar_todos_los_candidatos(entorno):
    """Responder '0' en el re-ranking debe producir ruido, no un match forzado."""
    pipeline = entorno(
        LLMFalso(rerank="0", extraccion=extraccion_de(TERMINO_SIN_HINT)),
        IndexFalso(score=50.0, termino="otro concepto", codigo="999"),
    )
    resultado = await pipeline.ejecutar("Texto", HolonPaciente(paciente_id="t"))

    infon = resultado.infones[0]
    assert infon.estado == EstadoInfon.RUIDO
    assert infon.codigo is None


async def test_solo_la_evidencia_validada_alimenta_a_bayes(entorno):
    pipeline = entorno(LLMFalso(auditoria_valida=False), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar("Texto", HolonPaciente(paciente_id="t"))

    # El infón quedó en ALERTA, así que la probabilidad no debe moverse.
    assert resultado.inferencia is not None
    assert resultado.inferencia.probabilidad_porcentaje == 10.0
    assert resultado.inferencia.evidencia_utilizada == []


async def test_el_holon_solo_absorbe_infones_validados(entorno):
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))
    holon = HolonPaciente(paciente_id="t")
    resultado = await pipeline.ejecutar("Temperatura 38.5", holon)

    holon.absorber(resultado.infones)
    assert len(holon.linea_tiempo) == 1

    ruidoso = entorno(
        LLMFalso(extraccion=extraccion_de(TERMINO_SIN_HINT)),
        IndexFalso(score=20.0, termino="otro concepto", codigo="999"),
    )
    otro = await ruidoso.ejecutar("Texto", holon)
    holon.absorber(otro.infones)
    assert len(holon.linea_tiempo) == 1  # el ruido no entra en la historia
