"""Los tres niveles: vetar, contar, balancear.

El caso que gobierna estos tests es el que motivó el diseño: un dolor en
fosa ilíaca derecha puede cumplir criterios de apendicitis, pero si el
paciente está apendicectomizado no tiene ese diagnóstico y se descarta.
"""

import pytest

from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.core.skills import Skill
from holonmed.core.veredicto import EvaluadorDeVeredicto
from holonmed.models import EstadoInfon, Infon, Polaridad, VeredictoSemiotico

APENDICITIS = """---
titulo: Protocolo de apendicitis aguda
condicion:
  nombre: Apendicitis aguda
  codigos: { holonmed: "HM:9001" }
signos:
  - nombre: Apendicectomía
    codigos: { holonmed: "HM:9010" }
    efecto: excluye
    dispara_si: presente
    fuente: "sin apéndice no hay apendicitis"

  - nombre: Dolor en fosa ilíaca derecha
    codigos: { holonmed: "HM:9002" }
    rol: manifestacion
    efecto: bandera_roja
    dispara_si: ausente
    fuente: "..."

  - nombre: Fiebre
    codigos: { holonmed: "HM:9003" }
    efecto: apoya
    dispara_si: presente
    fuente: "..."

  - nombre: Leucocitosis
    codigos: { holonmed: "HM:9004" }
    efecto: apoya
    dispara_si: presente
    fuente: "..."

  - nombre: Signo de Blumberg
    codigos: { holonmed: "HM:9005" }
    efecto: apoya
    dispara_si: presente
    fuente: "..."

balance:
  fuente: "Postuma RB et al, Mov Disord 2015 (forma del criterio)"
  establecida: { apoyos_minimos: 2, banderas_maximas: 0 }
  probable:    { contrapeso: 1, banderas_maximas: 2 }
---

Cuerpo del protocolo.
"""


@pytest.fixture
def skill() -> Skill:
    return Skill("apendicitis", APENDICITIS)


@pytest.fixture
def evaluador() -> EvaluadorDeVeredicto:
    return EvaluadorDeVeredicto()


def infon(termino: str, presente: bool = True, valido: bool = True) -> Infon:
    return Infon(
        texto_origen=termino,
        termino_propuesto=termino,
        termino=termino,
        polaridad=Polaridad.PRESENTE if presente else Polaridad.AUSENTE,
        estado=EstadoInfon.VALIDADO if valido else EstadoInfon.ALERTA,
        confianza=95.0,
        razon_auditoria="[hint_exacto] auditado",
    )


# --- El veto ----------------------------------------------------------


def test_la_apendicectomia_excluye_la_apendicitis(evaluador, skill):
    """El caso que motivó todo el diseño."""
    res = evaluador.evaluar(
        skill, [infon("Dolor en fosa ilíaca derecha"), infon("Fiebre"),
                infon("Leucocitosis"), infon("Apendicectomía")]
    )

    assert res.veto is not None
    assert res.veto.tipo == "exclusion_absoluta"
    assert "Apendicectomía" in res.veto.termino
    assert not res.sostiene


def test_el_veto_gana_aunque_todo_lo_demas_apoye(evaluador, skill):
    """Ninguna cantidad de evidencia contrarresta una imposibilidad."""
    res = evaluador.evaluar(
        skill,
        [infon("Apendicectomía"), infon("Fiebre"), infon("Leucocitosis"),
         infon("Signo de Blumberg"), infon("Dolor en fosa ilíaca derecha")],
    )
    assert res.veto is not None
    assert res.nivel is None


def test_el_veto_deja_su_motivo_visible(evaluador, skill):
    """Se descarta, no se borra: el próximo clínico no rehace el razonamiento."""
    res = evaluador.evaluar(skill, [infon("Apendicectomía")])

    assert res.veto.motivo
    assert res.veto.hipotesis == "Apendicitis aguda"
    assert any("Exclusión absoluta" in t for t in res.traza)


def test_una_exclusion_en_alerta_no_veta(evaluador, skill):
    """Sólo evidencia auditada retira un diagnóstico.

    Es la dirección peligrosa: un falso positivo aquí quita una apendicitis
    a quien la tiene.
    """
    res = evaluador.evaluar(skill, [infon("Apendicectomía", valido=False),
                                    infon("Fiebre"), infon("Leucocitosis")])
    assert res.veto is None
    assert res.nivel == "establecida"


def test_la_exclusion_exige_la_polaridad_declarada(evaluador, skill):
    """«No hay apendicectomía» no excluye nada."""
    res = evaluador.evaluar(
        skill, [infon("Apendicectomía", presente=False), infon("Fiebre"),
                infon("Leucocitosis")]
    )
    assert res.veto is None
    assert res.nivel == "establecida"


# --- Las banderas rojas -----------------------------------------------


def test_la_bandera_se_levanta_con_la_ausencia_documentada(evaluador, skill):
    """La bandera es «NO tener dolor en fosa ilíaca derecha»."""
    res = evaluador.evaluar(
        skill, [infon("Dolor en fosa ilíaca derecha", presente=False), infon("Fiebre")]
    )
    assert res.banderas_rojas == ["Dolor en fosa ilíaca derecha"]
    assert res.apoyos == ["Fiebre"]


def test_el_silencio_no_levanta_bandera(evaluador, skill):
    """Que no conste no es que conste que no. Aquí es donde más importa."""
    res = evaluador.evaluar(skill, [infon("Fiebre"), infon("Leucocitosis")])

    assert res.banderas_rojas == []
    assert res.nivel == "establecida"


def test_una_bandera_se_contrarresta_con_un_apoyo(evaluador, skill):
    """El «uno por uno» de MDS."""
    una = evaluador.evaluar(
        skill, [infon("Dolor en fosa ilíaca derecha", presente=False), infon("Fiebre")]
    )
    sola = evaluador.evaluar(
        skill, [infon("Dolor en fosa ilíaca derecha", presente=False)]
    )

    assert una.nivel == "probable"      # contrarrestada
    assert sola.nivel is None           # sin contrapeso, no alcanza nivel


def test_pasar_el_tope_de_banderas_es_un_veto_y_no_un_balance(evaluador):
    """Medido contra MDS: un coseno no puede expresar un tope.

    Cuatro apoyos con tres banderas queda rechazado por el criterio y sin
    embargo daría Φ positiva. Por eso el tope se trata como exclusión
    contada y no como una bandera más.
    """
    protocolo = APENDICITIS.replace(
        "    dispara_si: ausente\n    fuente: \"...\"",
        "    dispara_si: ausente\n    fuente: \"...\"",
    )
    skill = Skill("x", protocolo)
    # Se fuerza el tope bajándolo a 0 en los dos niveles.
    skill.balance.niveles[0].banderas_maximas = 0
    skill.balance.niveles[1].banderas_maximas = 0

    res = evaluador.evaluar(
        skill,
        [infon("Dolor en fosa ilíaca derecha", presente=False),
         infon("Fiebre"), infon("Leucocitosis"), infon("Signo de Blumberg")],
    )
    assert res.veto is not None
    assert res.veto.tipo == "tope_banderas"


# --- Los niveles de certeza -------------------------------------------


def test_dos_apoyos_sin_banderas_dan_el_nivel_mas_estricto(evaluador, skill):
    res = evaluador.evaluar(skill, [infon("Fiebre"), infon("Leucocitosis")])
    assert res.nivel == "establecida"
    assert res.sostiene


def test_un_solo_apoyo_no_alcanza_el_nivel_estricto(evaluador, skill):
    res = evaluador.evaluar(skill, [infon("Fiebre")])
    assert res.nivel == "probable"


def test_sin_evidencia_no_alcanza_ningun_nivel(evaluador, skill):
    res = evaluador.evaluar(skill, [])
    assert res.nivel is None
    assert not res.sostiene


def test_un_protocolo_sin_los_bloques_nuevos_devuelve_None(evaluador):
    """Los protocolos escritos antes de existir esto siguen valiendo."""
    viejo = Skill(
        "viejo",
        "---\ntitulo: X\nsignos:\n  - nombre: Fiebre\n    lr: 2.0\n    fuente: y\n---\n\nx\n",
    )
    assert evaluador.evaluar(viejo, [infon("Fiebre")]) is None


# --- Φ categórico -----------------------------------------------------


def test_el_vector_categorico_no_necesita_ningun_LR(skill):
    """Casi todos los criterios publicados declaran categorías, no cocientes.

    La versión anterior de este test escribía
    `assert res is None or res.phi_categorico is not None`, y como el
    protocolo no declara ningún LR el `res is None` era SIEMPRE cierto: el
    `or` cortocircuitaba y la segunda mitad no se evaluaba nunca. El test
    pasaba por la misma razón por la que debía fallar — una aserción con una
    salida de emergencia que el comportamiento real toma siempre.
    """
    assert all(s.lr is None for s in skill.signos)

    res = MedidorDeAcoplamiento().medir(skill, [infon("Fiebre")])

    assert res is not None, "un protocolo sólo-categorías tiene que ser medible"
    assert res.phi_categorico is not None
    assert res.phi_categorico > 0


def test_el_categorico_se_alcanza_por_el_camino_publico(skill):
    """Que la aritmética sea correcta no sirve si `medir()` no llega a ella.

    Los otros tests del vector llaman a `_categorico` directamente, así que
    verifican la aritmética y no la accesibilidad. Éste entra por donde entra
    el pipeline.
    """
    med = MedidorDeAcoplamiento()
    directo, _, _ = med._categorico(skill, [infon("Fiebre"), infon("Anemia")])
    publico = med.medir(skill, [infon("Fiebre"), infon("Anemia")])

    assert publico is not None
    assert publico.phi_categorico == pytest.approx(
        round(directo * publico.anclaje, 4), abs=1e-4
    )


def test_sin_LR_las_bandas_se_leen_del_categorico(skill):
    """Con `phi` a 0 por falta de LR, la banda diría INERCIA — que es falso."""
    res = MedidorDeAcoplamiento().medir(
        skill, [infon("Fiebre"), infon("Leucocitosis"), infon("Signo de Blumberg")]
    )

    assert res.phi == 0.0                       # no hay vector ponderado
    assert res.phi_categorico > 0.20
    assert res.veredicto is not VeredictoSemiotico.INERCIA
    assert any("no declara ningún LR" in t for t in res.traza)


def test_un_signo_declarado_sin_LR_no_es_resto_no_simbolizado(skill):
    """Declarado por categoría es declarado: el protocolo sí lo contempla."""
    res = MedidorDeAcoplamiento().medir(skill, [infon("Fiebre"), infon("Cefalea")])

    assert res.resto_no_simbolizado == ["Cefalea"]


def test_un_protocolo_sin_signos_sigue_devolviendo_None(skill):
    """Ni LR ni categorías: no hay espacio donde medir, y eso no es Φ = 0."""
    vacio = Skill("vacio", "---\ntitulo: Sin nada\n---\n\nx\n")
    assert MedidorDeAcoplamiento().medir(vacio, [infon("Fiebre")]) is None


def test_los_tres_polos_del_vector_categorico(skill):
    med = MedidorDeAcoplamiento()
    dims = [s for s in skill.signos if s.efecto != "excluye"]

    todo_a_favor = [infon("Fiebre"), infon("Leucocitosis"),
                    infon("Signo de Blumberg"), infon("Dolor en fosa ilíaca derecha")]
    todo_en_contra = [infon("Fiebre", presente=False),
                      infon("Leucocitosis", presente=False),
                      infon("Signo de Blumberg", presente=False),
                      infon("Dolor en fosa ilíaca derecha", presente=False)]

    phi_mas, _, _ = med._categorico(skill, todo_a_favor)
    phi_menos, _, _ = med._categorico(skill, todo_en_contra)
    phi_cero, _, _ = med._categorico(skill, [])

    assert len(dims) == 4
    assert phi_mas == pytest.approx(1.0, abs=1e-9)
    assert phi_menos == pytest.approx(-1.0, abs=1e-9)
    assert phi_cero == 0.0


def test_la_bandera_resta_y_el_apoyo_suma(skill):
    med = MedidorDeAcoplamiento()
    solo_apoyo, _, _ = med._categorico(skill, [infon("Fiebre")])
    con_bandera, _, _ = med._categorico(
        skill, [infon("Fiebre"), infon("Dolor en fosa ilíaca derecha", presente=False)]
    )
    assert solo_apoyo > 0
    assert con_bandera == pytest.approx(0.0, abs=1e-9)


def test_la_exclusion_no_es_una_dimension(skill):
    """No resta: veta. Y para cuando esto se calcula, ya se retiró."""
    _, dims, _ = MedidorDeAcoplamiento()._categorico(skill, [infon("Fiebre")])
    assert dims == 4          # cinco signos declarados, uno es exclusión


# --- El núcleo --------------------------------------------------------

CON_NUCLEO = APENDICITIS.replace(
    "signos:",
    """nucleo:
  requiere: [Dolor en fosa ilíaca derecha]

signos:""",
)


def test_sin_nucleo_el_criterio_no_se_aplica(evaluador):
    """No es que el diagnóstico sea imposible: es que aún no cabe preguntarlo."""
    skill = Skill("con_nucleo", CON_NUCLEO)
    res = evaluador.evaluar(skill, [infon("Fiebre"), infon("Leucocitosis")])

    assert res.nivel is None
    assert res.veto is None          # no es una exclusión
    assert any("Núcleo no documentado" in t for t in res.traza)


def test_con_nucleo_documentado_el_criterio_sigue_su_curso(evaluador):
    skill = Skill("con_nucleo", CON_NUCLEO)
    res = evaluador.evaluar(
        skill,
        [infon("Dolor en fosa ilíaca derecha"), infon("Fiebre"), infon("Leucocitosis")],
    )
    assert res.nivel == "establecida"


def test_el_nucleo_admite_la_forma_de_MDS(evaluador):
    """bradicinesia + (temblor de reposo O rigidez)."""
    parkinson = """---
titulo: Parkinson
condicion: {nombre: Enfermedad de Parkinson}
nucleo:
  requiere: [Bradicinesia]
  y_al_menos_uno_de: [Temblor de reposo, Rigidez]
signos:
  - nombre: Bradicinesia
    codigos: {holonmed: "HM:8001"}
  - nombre: Temblor de reposo
    codigos: {holonmed: "HM:8002"}
  - nombre: Rigidez
    codigos: {holonmed: "HM:8003"}
  - nombre: Respuesta clara a levodopa
    codigos: {holonmed: "HM:8004"}
    efecto: apoya
  - nombre: Anosmia
    codigos: {holonmed: "HM:8005"}
    efecto: apoya
balance:
  fuente: "Postuma RB et al, Mov Disord 2015;30:1591-601"
  establecida: {apoyos_minimos: 2, banderas_maximas: 0}
  probable: {contrapeso: 1, banderas_maximas: 2}
---

x
"""
    skill = Skill("pd", parkinson)
    apoyos = [infon("Respuesta clara a levodopa"), infon("Anosmia")]

    solo_bradicinesia = evaluador.evaluar(skill, [infon("Bradicinesia")] + apoyos)
    con_rigidez = evaluador.evaluar(
        skill, [infon("Bradicinesia"), infon("Rigidez")] + apoyos
    )
    solo_temblor = evaluador.evaluar(skill, [infon("Temblor de reposo")] + apoyos)

    assert solo_bradicinesia.nivel is None      # falta temblor o rigidez
    assert con_rigidez.nivel == "establecida"
    assert solo_temblor.nivel is None           # falta la bradicinesia


# --- Los tres hallazgos de la revisión --------------------------------


def test_el_nucleo_se_evalua_antes_que_el_tope_de_banderas(evaluador):
    """MDS documenta el parkinsonismo PRIMERO y sólo después juzga la causa.

    Una exclusión absoluta sí precede al núcleo —una apendicectomía excluye
    la apendicitis se haya documentado lo que se haya documentado— pero el
    tope de banderas es una propiedad de la tabla de balance, y el núcleo
    es justamente lo que condiciona que esa tabla se aplique.
    """
    protocolo = CON_NUCLEO.replace(
        "  probable:    { contrapeso: 1, banderas_maximas: 2 }",
        "  probable:    { contrapeso: 1, banderas_maximas: 0 }",
    )
    skill = Skill("x", protocolo)

    # Sin el núcleo documentado, y con una bandera que supera el tope.
    res = evaluador.evaluar(
        skill, [infon("Dolor en fosa ilíaca derecha", presente=False)]
    )

    assert res.veto is None, "el tope no debe vetar antes de comprobar el núcleo"
    assert any("Núcleo no documentado" in t for t in res.traza)


def test_el_nucleo_empareja_igual_que_el_resto_del_sistema(evaluador):
    """Por subcadena, como `bayes.emparejar_termino`, no por igualdad exacta.

    Si el núcleo emparejara distinto que los signos, un mismo infón
    satisfaría un signo y no el núcleo — la clase de divergencia silenciosa
    que la §3.3 de ACOPLAMIENTO.md existe para impedir.
    """
    skill = Skill("con_nucleo", CON_NUCLEO)
    res = evaluador.evaluar(
        skill,
        [infon("Dolor en fosa ilíaca derecha irradiado"), infon("Fiebre"),
         infon("Leucocitosis")],
    )
    assert res.nivel == "establecida"


def test_sin_ningun_signo_que_dispare_no_hay_nivel(evaluador):
    """El agujero de los «cero apoyos», sin depender de que haya núcleo.

    Basta un signo emparejado que NO dispare para que `observados` deje de
    estar vacío: entonces apoyos y banderas valen cero y un nivel sin
    `apoyos_minimos` se satisface con 0 >= 0.
    """
    skill = Skill("apendicitis", APENDICITIS)   # sin bloque `nucleo`

    # El dolor consta PRESENTE: su bandera dispara con la ausencia, así que
    # no dispara nada, pero el signo sí queda emparejado.
    res = evaluador.evaluar(skill, [infon("Dolor en fosa ilíaca derecha")])

    assert res.apoyos == []
    assert res.banderas_rojas == []
    assert res.nivel is None, "un nivel no puede alcanzarse sin nada que lo sostenga"
