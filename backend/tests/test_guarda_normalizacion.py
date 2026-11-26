"""La normalización propone; no certifica.

Todos los textos son sintéticos y las pruebas corren contra el vocabulario y
el protocolo reales del repositorio. Los dobles reproducen el peor caso: un
re-ranking que elige un concepto equivocado y un auditor que lo aprueba todo.
"""

import json
from pathlib import Path

import pytest

from holonmed.config import Settings
from holonmed.core.pipeline import CrystallizationPipeline
from holonmed.core.skills import SkillManager
from holonmed.core.terminology import Candidato, TerminologyIndex, VocabularyLoader
from holonmed.core.validator import OntologyValidator
from holonmed.core.verifier import ClinicalVerifier
from holonmed.db.store import Database, GraphRepo
from holonmed.models import EstadoInfon, HolonPaciente

RAIZ = Path(__file__).resolve().parents[1]
SEMILLA = RAIZ / "data" / "vocabulario_semilla.json"

PROPUESTO = "Cáncer de páncreas"
ATLANTA = "Hallazgos de imagen compatibles con pancreatitis"
NARRATIVA = "Paciente sintético de 38 años. Antecedente referido: cáncer de páncreas."


class LLMDoble:
    """Elige en el re-ranking lo que se le diga y anota lo que se audita."""

    def __init__(self, eleccion=ATLANTA, extraidos=(), presente=True, aprueba=True):
        self.eleccion = eleccion
        self.extraidos = extraidos
        self.presente = presente
        self.aprueba = aprueba
        self.auditados: list[str] = []

    async def generar(self, prompt, **kwargs):
        if "Auditor de Terminología" in prompt:
            for linea in prompt.splitlines():
                numero, _, termino = linea.partition(". ")
                if numero.isdigit() and termino == self.eleccion:
                    return numero
            return "0"
        return "acute_pancreatitis"

    async def generar_json(self, prompt, **kwargs):
        if "Auditor Médico" in prompt:
            marca = "HALLAZGO A AUDITAR:" if self.presente else "AFIRMACIÓN A AUDITAR:"
            self.auditados.append(prompt.split(marca)[1].split('"')[1])
            clave = "valido" if self.presente else "ausencia_confirmada"
            return {clave: self.aprueba, "analisis": "lo dice el texto", "confianza": 99}
        return {
            "resumen": "Resumen sintético.",
            "infones": [
                {
                    "texto_origen": "cáncer de páncreas",
                    "termino_clinico": termino,
                    "presente": self.presente,
                }
                for termino in self.extraidos
            ],
        }

    async def elegir_opcion(self, prompt, *, opciones_validas, defecto, **kwargs):
        return defecto


class IndiceDeUnCandidato:
    """Un candidato con la similitud que se pida, para probar la frontera."""

    def __init__(self, score):
        self.score = score

    def buscar_candidatos(self, texto, limite=15):
        return [Candidato(1, "HM:TEST", "holonmed", "Concepto sintético", self.score)]

    def metadatos(self, concepto_id):
        return None, None


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    db = Database(tmp_path_factory.mktemp("guarda") / "x.db")
    VocabularyLoader(db).cargar_semilla(SEMILLA)
    yield db
    db.conexion().close()


def _validador(db, llm):
    return OntologyValidator(
        TerminologyIndex(db, GraphRepo(db)), llm, Settings(skills_dir=RAIZ / "skills")
    )


async def _tic(db, llm):
    settings = Settings(skills_dir=RAIZ / "skills")
    pipeline = CrystallizationPipeline(
        llm=llm,
        skills=SkillManager(settings),
        validador=_validador(db, llm),
        verificador=ClinicalVerifier(llm, settings),
        settings=settings,
    )
    return await pipeline.ejecutar(
        NARRATIVA, HolonPaciente(paciente_id="t"), skill_forzada="acute_pancreatitis"
    )


# --- El techo ---------------------------------------------------------


async def test_el_caso_observado_conserva_el_concepto_pero_pide_revision(base):
    match = await _validador(base, LLMDoble()).validar(PROPUESTO)

    assert match.termino == ATLANTA
    assert match.metodo == "rerank_llm"
    assert match.similitud_lexica is not None
    assert match.similitud_lexica < Settings().threshold_validated
    assert match.motivo_revision is not None


async def test_el_caso_observado_no_queda_validado_ni_mueve_la_inferencia(base):
    resultado = await _tic(base, LLMDoble(extraidos=[PROPUESTO]))

    assert resultado.instrucciones_detectadas == []
    (infon,) = resultado.infones
    assert infon.termino == ATLANTA
    assert infon.termino_propuesto == PROPUESTO
    assert infon.estado == EstadoInfon.ALERTA
    assert f"se propuso «{PROPUESTO}»" in infon.razon_auditoria
    # La confianza que se muestra no es el 99 del re-ranking.
    assert infon.confianza < Settings().threshold_validated
    assert resultado.clasificacion is None or resultado.clasificacion.satisfechos == 0
    assert resultado.inferencia is None or all(
        ATLANTA not in linea for linea in resultado.inferencia.traza_logica
    )


@pytest.mark.parametrize(
    ("similitud", "pide_revision"),
    [(45.0, True), (84.9, True), (85.0, False), (95.0, False)],
)
async def test_la_frontera_es_el_umbral_de_validacion(similitud, pide_revision):
    validador = OntologyValidator(
        IndiceDeUnCandidato(similitud),
        LLMDoble(eleccion="Concepto sintético"),
        Settings(),
    )

    match = await validador.validar("término sintético")

    assert (match.motivo_revision is not None) is pide_revision


async def test_el_techo_sigue_al_umbral_configurado():
    validador = OntologyValidator(
        IndiceDeUnCandidato(88.0),
        LLMDoble(eleccion="Concepto sintético"),
        Settings(threshold_validated=90.0),
    )

    match = await validador.validar("término sintético")

    assert match.motivo_revision is not None


# --- Se audita lo que se guarda ---------------------------------------


@pytest.mark.parametrize("presente", [True, False])
async def test_el_auditor_recibe_el_termino_que_se_va_a_guardar(base, presente):
    llm = LLMDoble(extraidos=[PROPUESTO], presente=presente)

    await _tic(base, llm)

    assert llm.auditados == [ATLANTA]


async def test_si_el_auditor_rechaza_lo_guardado_sigue_en_alerta(base):
    resultado = await _tic(base, LLMDoble(extraidos=[PROPUESTO], aprueba=False))

    assert [i.estado for i in resultado.infones] == [EstadoInfon.ALERTA]


# --- Sinónimos declarados ---------------------------------------------


async def test_los_sinonimos_declarados_no_pasan_por_el_techo(base):
    """El coste de la guarda cae sobre lo que el vocabulario no declara.
    Cada término y sinónimo de la semilla resuelve por vía exacta, sin
    preguntar al modelo."""
    conceptos = json.loads(SEMILLA.read_text(encoding="utf-8"))["conceptos"]
    validador = _validador(base, LLMDoble(eleccion="nada"))
    fallos = []
    for concepto in conceptos:
        for variante in [concepto["termino"], *concepto.get("sinonimos", [])]:
            match = await validador.validar(variante)
            if match.metodo != "exacto" or match.motivo_revision is not None:
                fallos.append((variante, match.metodo))

    assert fallos == []
