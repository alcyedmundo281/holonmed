"""La inversión del pipeline: la abducción delante.

La etapa que se llamaba «inferencia abductiva» era Bayes, y Bayes no
genera hipótesis: pesa una que ya alguien eligió. La abducción real
ocurría en el triaje —un prompt— y de él colgaban la validación, el veto,
los cocientes y el coseno. Ahora la hipótesis la elige la competencia
sobre el grafo del paciente.

Estos tests cubren lo que la inversión trae y no existía: la pasada
genérica con su guarda de cortes, la segunda pasada como paso deductivo,
y «todas vetadas» como estado clínico propio.
"""

import pytest
from test_pipeline import (
    CITADA,
    TRIAJE_QUE_ACUNA,
    VETADA,
    IndexFalso,
    LLMFalso,
    extraccion_de,
)

from holonmed.config import Settings
from holonmed.core.pipeline import (
    CrystallizationPipeline,
    _sin_cortes_inventados,
    _terminos_autorizados,
)
from holonmed.core.skills import Skill, SkillManager
from holonmed.core.terminology import Candidato
from holonmed.core.validator import OntologyValidator
from holonmed.core.verifier import ClinicalVerifier
from holonmed.models import HolonPaciente


class IndexEco:
    """Devuelve como concepto el mismo término que se le pregunta.

    `IndexFalso` normaliza todo al mismo término, que sirve para probar el
    validador y no para probar que dos pasadas aportan cosas distintas:
    con él, «Fiebre» y «Tos» acabarían siendo el mismo infón.
    """

    def __init__(self, codigo="386661006"):
        self.codigo = codigo

    def disponible(self):
        return True

    def buscar_exacto(self, texto):
        return Candidato(1, self.codigo, "holonmed", texto, 100.0)

    def buscar_candidatos(self, texto, limite=15):
        return [Candidato(1, self.codigo, "holonmed", texto, 95.0)]

    def metadatos(self, concepto_id):
        return "R50.9", "Signo clínico"

    def cobertura_de_grafo(self, concepto_ids):
        return {self.codigo} if list(concepto_ids) else set()


def construir(tmp_path, llm, index, decide=True, **protocolos):
    """`decide` se pasa siempre y no se hereda del defecto.

    El defecto es False —la inversión viene apagada hasta que haya
    histórico con el que justificarla— así que un test de la inversión que
    no lo dijera estaría probando el modo contrario sin enterarse. Decirlo
    en cada caso también documenta cuál se está ejercitando.
    """
    for nombre, texto in protocolos.items():
        (tmp_path / f"{nombre}.md").write_text(texto, encoding="utf-8")
    settings = Settings(
        skills_dir=tmp_path, docs_dir=tmp_path / "docs", abduccion_decide=decide
    )
    return CrystallizationPipeline(
        llm=llm,
        skills=SkillManager(settings),
        validador=OntologyValidator(index, LLMFalso(), settings),
        verificador=ClinicalVerifier(LLMFalso(), settings),
        settings=settings,
    )


# --- La pasada genérica y su guarda de cortes -------------------------


def test_la_pasada_generica_no_deja_pasar_un_corte_inventado():
    """La restricción dura: sin cortes declarados, el modelo se los inventa.

    Y aquí importa más que en ninguna otra parte, porque lo que salga de
    esta pasada es el conjunto COMÚN contra el que compiten TODAS las
    candidatas. Un corte inventado no desvía una hipótesis: desvía la
    competencia entera, y todas compiten contra un paciente que no existe.

    La regla no es «hay un número». `general_triage` sí declara los cortes
    universales —Temperatura, frecuencia cardíaca, leucocitos— y
    convertirlos es exactamente lo que se le pide. Lo que no declara son
    los de cada enfermedad, que es donde el conversor documentó su propio
    caso: «lipasa 890» auditada como «>3x el límite normal (aprox.
    250-300)» cuando el protocolo declara 60.
    """
    autorizados = {"fiebre", "leucocitosis"}
    crudos = [
        {"texto_origen": "38.5 grados", "termino_clinico": "Fiebre"},
        {"texto_origen": "leucocitos 18.500", "termino_clinico": "Leucocitosis"},
        {"texto_origen": "lipasa 890", "termino_clinico": "Hiperlipasemia"},
        {"texto_origen": "calcio 6.8", "termino_clinico": "Hipocalcemia"},
        {"texto_origen": "hipocalcemia leve", "termino_clinico": "Hipocalcemia"},
        {"texto_origen": "dolor epigastrico", "termino_clinico": "Dolor epigastrico"},
    ]
    conservados, retirados = _sin_cortes_inventados(crudos, autorizados)

    assert [c["termino_clinico"] for c in conservados] == [
        "Fiebre",  # el protocolo declara su corte
        "Leucocitosis",  # también
        "Hipocalcemia",  # el TEXTO lo dice, no lo deduce el modelo
        "Dolor epigastrico",  # sin números: nunca se toca
    ]
    assert retirados == ["Hiperlipasemia", "Hipocalcemia"]


def test_la_guarda_mira_la_cita_y_no_la_narrativa_entera():
    """Basta que la palabra salga en otra frase para colar una invención.

    Un texto que dijera «hipocalcemia leve» en la anamnesis dejaría pasar
    un «Hipocalcemia» derivado del «calcio 6.8» del laboratorio si se
    comparara contra el texto completo. Se compara contra la cita, que es
    la evidencia que el propio modelo alega.
    """
    crudos = [
        {"texto_origen": "hipocalcemia leve", "termino_clinico": "Hipocalcemia"},
        {"texto_origen": "calcio 6.8", "termino_clinico": "Hipocalcemia"},
    ]
    conservados, retirados = _sin_cortes_inventados(crudos, set())

    assert len(conservados) == 1
    assert conservados[0]["texto_origen"] == "hipocalcemia leve"
    assert retirados == ["Hipocalcemia"]


def test_solo_los_cortes_declarados_autorizan_una_interpretacion():
    """Un signo declarado sin corte no autoriza convertir una cifra.

    El protocolo dice que ese hallazgo le interesa, no en qué cifra
    empieza. La diferencia importa: quien declara el corte se hace
    responsable de él y lo acompaña de su fuente.
    """
    con_corte = Skill(
        "con_corte",
        "---\ntitulo: Con corte\nsignos:\n  - nombre: Fiebre\n"
        "laboratorio:\n  - parametro: Temperatura\n    corte_superior: 38.0\n"
        "    termino_si_alto: Fiebre\n---\n\nCuerpo.\n",
    )
    sin_corte = Skill(
        "sin_corte",
        "---\ntitulo: Sin corte\nsignos:\n  - nombre: Fiebre\n---\n\nCuerpo.\n",
    )

    assert _terminos_autorizados(con_corte) == {"fiebre"}
    assert _terminos_autorizados(sin_corte) == set()


# --- Las dos pasadas ---------------------------------------------------


class LLMPorPasada(LLMFalso):
    """Devuelve una extracción distinta según qué pasada la pide.

    Se distinguen por el prompt: el de la pasada genérica prohíbe
    interpretar números y el del protocolo se los da.
    """

    def __init__(self, generica, especifica, triaje="general_triage"):
        super().__init__()
        self._generica = generica
        self._especifica = especifica
        self._triaje = triaje
        self.pasadas: list[str] = []
        self.prompts: list[str] = []

    async def elegir_opcion(self, prompt, *, opciones_validas, defecto, **kwargs):
        """Deja que el triaje elija un protocolo DISTINTO del genérico.

        Con el triaje eligiendo siempre `general_triage`, «leer con el del
        triaje» y «leer con el genérico» son la misma cosa y el modo
        apagado no se puede distinguir del encendido a medias.
        """
        return self._triaje if self._triaje in opciones_validas else defecto

    async def generar_json(self, prompt, **kwargs):
        if "Auditor Médico" in prompt:
            return {"valido": True, "analisis": "ok", "confianza": 92}
        generica = "LOS NÚMEROS NO SE INTERPRETAN" in prompt
        self.pasadas.append("generica" if generica else "especifica")
        self.prompts.append(prompt)
        return self._generica if generica else self._especifica


@pytest.mark.asyncio
async def test_la_segunda_pasada_relee_la_nota_con_la_hipotesis_puesta(tmp_path):
    """La deducción sobre el texto que ya está en la mano.

    La pasada 1 corre a ciegas y sin poder interpretar un solo número;
    ésta corre sabiendo qué hipótesis se sostiene, con su vocabulario y
    sus cortes. Lo que aparece aquí es literalmente lo que la hipótesis
    predice y la lectura genérica no supo ver — antes de preguntarle nada
    al paciente.
    """
    llm = LLMPorPasada(
        generica=extraccion_de("Fiebre", "38.5 grados"),
        especifica=extraccion_de("Tos", "tos seca"),
    )
    pipeline = construir(
        tmp_path, llm, IndexEco(), general_triage=TRIAJE_QUE_ACUNA, citada=CITADA
    )
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5 con tos seca", HolonPaciente(paciente_id="t")
    )

    assert llm.pasadas == ["generica", "especifica"]
    assert resultado.skill_activa == "citada"
    terminos = {i.termino for i in resultado.infones}
    # Lo que sólo ve la hipótesis se añade…
    assert "Tos" in terminos
    # …y lo que vio la genérica se conserva: la pasada 2 lee con la
    # hipótesis puesta y puede desatender lo que no le concierne, que es
    # justamente el resto que Φ necesita para delatarla si es ajena.
    assert "Fiebre" in terminos


@pytest.mark.asyncio
async def test_sin_ganadora_distinta_no_se_paga_una_segunda_pasada(tmp_path):
    """Releer con el mismo protocolo sería una llamada al modelo por nada."""
    llm = LLMPorPasada(
        generica=extraccion_de("Fiebre", "38.5 grados"),
        especifica=extraccion_de("Tos", "tos seca"),
    )
    pipeline = construir(
        tmp_path,
        llm,
        IndexFalso(score=95.0, exacto=True),
        general_triage=TRIAJE_QUE_ACUNA,
    )
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )

    assert resultado.skill_activa == "general_triage"
    assert llm.pasadas == ["generica"]


# --- Todas vetadas -----------------------------------------------------


@pytest.mark.asyncio
async def test_todas_vetadas_es_un_estado_propio_y_no_una_vuelta_al_triaje(tmp_path):
    """«No encontré hipótesis» y «todas son imposibles» no son lo mismo.

    Lo segundo dice algo: que todo lo que el grafo propone para este
    paciente es estructuralmente imposible. O hay que ampliar el ámbito de
    los protocolos, o los antecedentes que las excluyen están mal
    registrados. Caer al triaje lo taparía con el comportamiento de
    siempre, y el clínico no vería nunca que el índice se le queda corto.
    """
    pipeline = construir(
        tmp_path,
        LLMFalso(extraccion=extraccion_de("Organo extirpado", "sin organo")),
        IndexFalso(
            score=95.0, exacto=True, termino="Organo extirpado", codigo="386661006"
        ),
        general_triage=TRIAJE_QUE_ACUNA,
        imposible=VETADA,
    )
    resultado = await pipeline.ejecutar("Sin organo", HolonPaciente(paciente_id="t"))

    assert resultado.competencia
    assert all(c.vetada for c in resultado.competencia)
    assert resultado.todas_vetadas is not None
    assert "está vetada" in resultado.todas_vetadas
    # Con su motivo dentro: sin él, el clínico no sabe qué corregir.
    assert "sin órgano no hay enfermedad" in resultado.todas_vetadas.lower()
    assert "ampliar el ámbito" in resultado.todas_vetadas
    # Y no se cae al triaje: no hay probabilidad ni Φ sobre una hipótesis
    # que nadie sostiene.
    assert resultado.inferencia is None
    assert resultado.acoplamiento is None


@pytest.mark.asyncio
async def test_sin_candidatas_en_el_grafo_decide_el_triaje(tmp_path):
    """La red de seguridad: un paciente sin conceptos que cubran un ámbito.

    Quedarse sin hipótesis por eso sería peor que usar la de siempre, y no
    es el caso de «todas vetadas»: aquí el grafo no propuso nada, no
    propuso imposibles.
    """
    pipeline = construir(
        tmp_path,
        LLMFalso(),
        IndexFalso(score=95.0, exacto=True),
        general_triage=TRIAJE_QUE_ACUNA,
    )
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )

    assert resultado.competencia == []
    assert resultado.todas_vetadas is None
    assert resultado.skill_activa == "general_triage"
    assert resultado.acoplamiento is not None


@pytest.mark.asyncio
async def test_el_interruptor_devuelve_la_decision_al_triaje(tmp_path):
    """`abduccion_decide=False` es el modo anterior, y no apaga la medición.

    El diseño pone una precondición que hoy no está satisfecha —«antes de
    sustituir el prompt por esa regla hay que saber cuánto se equivoca»—
    y la cifra sale del histórico. Con el interruptor bajado, el triaje
    vuelve a decidir y la competencia sigue corriendo: sin eso, apagar la
    inversión costaría también la medida que justifica encenderla.
    """
    pipeline = construir(
        tmp_path,
        LLMFalso(),
        IndexEco(),
        decide=False,
        general_triage=TRIAJE_QUE_ACUNA,
        citada=CITADA,
    )
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )

    assert resultado.skill_activa == "general_triage"
    # La competencia sigue midiendo, que es el punto.
    assert resultado.ganadora_abductiva == "citada"
    assert resultado.triaje_coincide is False


def test_la_inversion_viene_apagada_y_es_una_decision(tmp_path):
    """El defecto es `False`, y eso se fija aquí porque es deliberado.

    No está a medias: está esperando su cifra. El diseño pone la
    precondición —«antes de sustituir el prompt por esa regla hay que
    saber cuánto se equivoca»— y esa cifra sale de `acuerdo_del_triaje()`
    sobre el histórico, que hoy no existe. Encenderla sin ella sería
    cambiar el mecanismo que elige el diagnóstico apoyándose en una
    intuición, que es justo lo que el paso 2 existía para evitar.

    Se fija como test y no como comentario para que subirla sea un cambio
    que alguien tenga que defender, y no un descuido.
    """
    assert Settings(skills_dir=tmp_path).abduccion_decide is False


def test_apagada_cuesta_una_sola_lectura(tmp_path):
    """El modo conservador tiene que ser también el barato.

    Apagar la inversión no puede costar la llamada de más que la inversión
    necesita: sin ella no hay segunda pasada que dar, y la primera se hace
    ya con el protocolo del triaje. La competencia sigue midiendo, sobre
    ese mismo conjunto, que es exactamente lo que medía antes del ciclo 7.
    """
    import asyncio

    # El triaje elige «citada», que NO es el protocolo genérico: si no,
    # leer con el del triaje y leer con el genérico serían lo mismo y el
    # modo apagado no se distinguiría de un encendido a medias.
    llm = LLMPorPasada(
        generica=extraccion_de("Fiebre", "38.5 grados"),
        especifica=extraccion_de("Tos", "tos seca"),
        triaje="citada",
    )
    pipeline = construir(
        tmp_path,
        llm,
        IndexEco(),
        decide=False,
        general_triage=TRIAJE_QUE_ACUNA,
        citada=CITADA,
    )
    resultado = asyncio.run(
        pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))
    )

    # Una sola lectura, y con el protocolo del triaje.
    assert llm.pasadas == ["especifica"]
    # «Tos» sólo la declara `citada`; el genérico de esta arena declara
    # únicamente «Fiebre». Es lo que distingue con qué se leyó.
    assert "«Tos»" in llm.prompts[0]
    assert resultado.skill_activa == "citada"
    # Y la medición no se pierde: el grafo compitió igual.
    assert resultado.ganadora_abductiva == "citada"
    assert resultado.triaje_coincide is True


def test_encendida_cuesta_dos_y_la_primera_es_la_generica(tmp_path):
    """La simétrica: la inversión paga la deducción, y se ve cuál es cuál."""
    import asyncio

    llm = LLMPorPasada(
        generica=extraccion_de("Fiebre", "38.5 grados"),
        especifica=extraccion_de("Tos", "tos seca"),
    )
    pipeline = construir(
        tmp_path,
        llm,
        IndexEco(),
        decide=True,
        general_triage=TRIAJE_QUE_ACUNA,
        citada=CITADA,
    )
    resultado = asyncio.run(
        pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))
    )

    assert llm.pasadas == ["generica", "especifica"]
    assert resultado.skill_activa == "citada"
