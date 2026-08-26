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
from holonmed.models import (
    CandidataAbductiva,
    EstadoInfon,
    HolonPaciente,
    Infon,
    Polaridad,
)

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

    def cobertura_de_grafo(self, concepto_ids):
        # El doble no tiene jerarquía: el concepto se cubre a sí mismo.
        return {self.codigo} if list(concepto_ids) else set()


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


# --- La competencia abductiva -----------------------------------------
#
# Corre en paralelo al triaje y NO decide nada todavía: mide cuánto se
# equivoca el prompt antes de sustituirlo por nada.

CITADA = """---
titulo: Candidata citada
condicion:
  nombre: Condicion citada
ambito_grafo: ["386661006"]
signos:
  - nombre: Fiebre
    lr: 3.0
    fuente: "Wagner JM et al, JAMA 1996"
  - nombre: Tos
    lr: 2.0
    fuente: "Wagner JM et al, JAMA 1996"
---

Cuerpo.
"""

SIN_CITAR = """---
titulo: Candidata sin citar
condicion:
  nombre: Condicion sin citar
ambito_grafo: ["386661006"]
signos:
  - nombre: Fiebre
    lr: 9.0
---

Cuerpo.
"""

# El protocolo de triaje, pero acuñando un trastorno — y no uno
# cualquiera: el término que EXCLUYE a la candidata `imposible`.
TRIAJE_QUE_ACUNA = """---
titulo: Triaje que acuña
condicion:
  nombre: Condicion de triaje
signos:
  - nombre: Fiebre
    lr: 3.0
    fuente: "Wagner JM et al, JAMA 1996"
clasificacion:
  nombre: Criterio de prueba
  fuente: "criterio de prueba"
  requiere: 1
  produce:
    termino: Organo extirpado
  criterios:
    - nombre: Fiebre
      satisface_si: [Fiebre]
---

Cuerpo.
"""


VETADA = """---
titulo: Candidata imposible
condicion:
  nombre: Condicion imposible
ambito_grafo: ["386661006"]
signos:
  - nombre: Fiebre
    lr: 40.0
    fuente: "Wagner JM et al, JAMA 1996"
  - nombre: Organo extirpado
    efecto: excluye
    dispara_si: presente
    fuente: "sin órgano no hay enfermedad"
---

Cuerpo.
"""


@pytest.fixture
def arena(tmp_path):
    """El mismo entorno, más candidatas que el grafo puede proponer."""
    (tmp_path / "general_triage.md").write_text(SKILL, encoding="utf-8")
    settings = Settings(skills_dir=tmp_path, docs_dir=tmp_path / "docs")

    def construir(**protocolos):
        for nombre, texto in protocolos.items():
            (tmp_path / f"{nombre}.md").write_text(texto, encoding="utf-8")
        return CrystallizationPipeline(
            llm=LLMFalso(),
            skills=SkillManager(settings),
            validador=OntologyValidator(
                IndexFalso(score=95.0, exacto=True), LLMFalso(), settings
            ),
            verificador=ClinicalVerifier(LLMFalso(), settings),
            settings=settings,
        )

    return construir


async def test_la_competencia_mide_y_no_decide(arena):
    """La invariante del paso: el protocolo que se USA no cambia.

    Si esto cae, el paso dejó de ser medición y pasó a ser una inversión
    del pipeline a medias — que es otra conversación y otro riesgo.
    """
    pipeline = arena(citada=CITADA)
    resultado = await pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))

    assert resultado.skill_activa == "general_triage"
    assert resultado.ganadora_abductiva == "citada"
    assert resultado.triaje_coincide is False
    # Y lo que se publica sigue saliendo de la skill del triaje.
    assert resultado.acoplamiento is None or (
        resultado.acoplamiento.hipotesis != "Condicion citada"
    )


async def test_la_competencia_guarda_a_las_perdedoras(arena):
    """«Se consideró X y sacó 0.25» ES la traza de auditoría.

    Sin las perdedoras el sistema muestra una conclusión sin decir contra
    qué compitió, que es pedirle al clínico que confíe en el orden.
    """
    pipeline = arena(citada=CITADA, otra=CITADA.replace("citada", "otra"))
    resultado = await pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))

    assert {c.skill for c in resultado.competencia} == {"citada", "otra"}
    assert all(c.clave is not None for c in resultado.competencia)
    assert all(c.lectura == "ponderada" for c in resultado.competencia)


async def test_una_candidata_imposible_sale_antes_de_dar_su_coseno(arena):
    """Un coseno bonito sobre una imposibilidad es ruido con formato numérico."""
    holon = HolonPaciente(paciente_id="t")
    holon.linea_tiempo.append(
        Infon(
            texto_origen="apendicectomía en 2019",
            termino_propuesto="Organo extirpado",
            termino="Organo extirpado",
            polaridad=Polaridad.PRESENTE,
            estado=EstadoInfon.VALIDADO,
            confianza=99.0,
            razon_auditoria="[hint_exacto] auditado",
        )
    )

    pipeline = arena(citada=CITADA, imposible=VETADA)
    resultado = await pipeline.ejecutar("Temperatura 38.5", holon)

    vetada = next(c for c in resultado.competencia if c.skill == "imposible")
    assert vetada.vetada
    assert vetada.motivo_veto
    assert vetada.clave is None, "una imposibilidad no aporta coseno a la comparación"
    # Y un veto ya no termina el tic: la otra candidata siguió compitiendo.
    assert resultado.ganadora_abductiva == "citada"


async def test_la_compuerta_de_alfa_no_actua_callada(arena):
    """La mejor acoplada queda fuera por α, y se dice en voz alta.

    Callada, el sistema trataría otra cosa sin explicar por qué. Dicha, la
    frase es accionable: manda a arreglar el índice.
    """
    pipeline = arena(citada=CITADA, sin_citar=SIN_CITAR)
    resultado = await pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))

    fuera = next(c for c in resultado.competencia if c.skill == "sin_citar")
    assert fuera.anclaje == 0.0
    assert not fuera.admitida
    assert fuera.clave > next(
        c.clave for c in resultado.competencia if c.skill == "citada"
    ), "la fixture ya no sirve: la excluida tiene que ser la de mejor coseno"

    assert resultado.ganadora_abductiva == "citada"
    assert resultado.aviso_competencia is not None
    assert "sin_citar" in resultado.aviso_competencia


async def test_la_competencia_corre_sobre_el_paciente_de_antes_de_clasificar(tmp_path):
    """Cada candidata compite contra el MISMO paciente, no contra el suyo.

    La etapa 4 acuña un infón específico de la hipótesis activa y lo mete
    en la lista. Compitiendo después, ese término entraría en la evidencia
    de todas las demás — y aquí es literal: el trastorno que acuña el
    triaje es el signo que EXCLUYE a otra candidata. Corriendo después, la
    candidata quedaría vetada por un término que el paciente no tiene y
    que fabricó la hipótesis rival.

    Φ solo no lo detectaría: `_resto_no_simbolizado` salta los infones
    derivados, así que el coseno no se movería. El veto no tiene esa
    guarda, y es por donde el error entra.
    """
    (tmp_path / "general_triage.md").write_text(TRIAJE_QUE_ACUNA, encoding="utf-8")
    (tmp_path / "imposible.md").write_text(VETADA, encoding="utf-8")
    settings = Settings(skills_dir=tmp_path, docs_dir=tmp_path / "docs")
    pipeline = CrystallizationPipeline(
        llm=LLMFalso(),
        skills=SkillManager(settings),
        validador=OntologyValidator(
            IndexFalso(score=95.0, exacto=True), LLMFalso(), settings
        ),
        verificador=ClinicalVerifier(LLMFalso(), settings),
        settings=settings,
    )
    resultado = await pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))

    acunado = [i for i in resultado.infones if i.derivado_de]
    assert acunado, "la fixture ya no sirve: el triaje tiene que acuñar algo"
    assert acunado[0].termino == "Organo extirpado"

    candidata = next(c for c in resultado.competencia if c.skill == "imposible")
    assert not candidata.vetada, (
        "la competencia vio el trastorno que acuñó la hipótesis rival"
    )


# --- La regla de orden, aparte del pipeline ---------------------------


def _fila(nombre, clave, anclaje, admitida=True, vetada=False):
    return CandidataAbductiva(
        skill=nombre, clave=clave, anclaje=anclaje, admitida=admitida, vetada=vetada
    )


def test_se_ordena_por_coseno_y_no_por_phi():
    """La decisión con contenido de toda la regla.

    Φ = α · cos, y α es la calidad documental del PROTOCOLO, no una
    propiedad del paciente. Aquí la mejor acoplada cita menos, así que
    ordenar por Φ la relega — y el sistema trataría al paciente con el
    protocolo mejor escrito en vez de con el que encaja.
    """
    acoplada = _fila("acoplada", clave=0.90, anclaje=0.69)      # Φ = 0.621
    documentada = _fila("documentada", clave=0.75, anclaje=0.87)  # Φ = 0.653

    ganadora, aviso = CrystallizationPipeline._ordenar_candidatas(
        [acoplada, documentada]
    )

    assert ganadora.skill == "acoplada"
    assert aviso is None
    # Y que la fixture siga midiendo lo que dice medir:
    assert documentada.clave * documentada.anclaje > acoplada.clave * acoplada.anclaje


def test_la_compuerta_es_de_admision_y_no_de_peso():
    """α excluye o deja pasar; una vez dentro, no pondera el orden."""
    ganadora, _ = CrystallizationPipeline._ordenar_candidatas(
        [
            _fila("apenas_citada", clave=0.80, anclaje=0.30),
            _fila("muy_citada", clave=0.70, anclaje=0.99),
        ]
    )
    assert ganadora.skill == "apenas_citada"


def test_una_vetada_no_entra_en_el_orden_ni_en_el_aviso():
    ganadora, aviso = CrystallizationPipeline._ordenar_candidatas(
        [
            _fila("imposible", clave=0.99, anclaje=0.9, vetada=True),
            _fila("posible", clave=0.40, anclaje=0.9),
        ]
    )
    assert ganadora.skill == "posible"
    assert aviso is None


def test_sin_ninguna_admitida_no_hay_ganadora():
    """Todas fuera no es «no encontré hipótesis»: es que ninguna compite."""
    ganadora, aviso = CrystallizationPipeline._ordenar_candidatas(
        [_fila("sin_citar", clave=0.99, anclaje=0.0, admitida=False)]
    )
    assert ganadora is None
    assert aviso is None


async def test_el_pipeline_lee_la_duda_y_reabre_la_indagacion(entorno):
    """La etapa 8 está viva: nadie leía `duda` y ahora algo la lee.

    Se afirma como equivalencia y no como valor: la reapertura existe
    exactamente cuando Φ dice que hay duda. Un test que comprobara un
    caso concreto pasaría igual con la etapa desconectada si ese caso no
    dudara.
    """
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))

    hay_duda = bool(resultado.acoplamiento and resultado.acoplamiento.duda)
    assert (resultado.reapertura is not None) is hay_duda


async def test_una_hipotesis_que_no_explica_al_paciente_reabre_la_indagacion(entorno):
    """El caso con duda de verdad, entrando por el pipeline entero.

    El protocolo de prueba declara un solo signo —Fiebre— y lo extraído es
    otra cosa, así que la dimensión declarada queda sin mirar y lo que
    consta no lo explica nadie. Φ cae, y el tic tiene que decirlo en vez
    de terminar como si hubiera concluido.
    """
    llm = LLMFalso(extraccion=extraccion_de(TERMINO_SIN_HINT, "orina oscura"))
    pipeline = entorno(llm, IndexFalso(score=95.0, termino=TERMINO_SIN_HINT,
                                       codigo="167223003", exacto=True))
    resultado = await pipeline.ejecutar("Orina oscura", HolonPaciente(paciente_id="t"))

    assert resultado.acoplamiento is not None
    assert resultado.acoplamiento.duda
    assert resultado.reapertura is not None
    assert resultado.reapertura.hipotesis == resultado.acoplamiento.hipotesis
    assert resultado.reapertura.motivo
