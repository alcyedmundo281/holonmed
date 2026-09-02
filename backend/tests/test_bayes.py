"""Tests del motor de inferencia bayesiana.

Se comprueba la aritmética, pero sobre todo las propiedades de seguridad:
que la evidencia no validada no mueva la probabilidad, y que un LR
absurdo en un skill no produzca una certeza del 100 %.
"""

from holonmed.core.bayes import LR_MAXIMO, AntigenPresentingCell
from holonmed.models import EstadoInfon, Infon

SKILL = {
    "name": "Pancreatitis aguda",
    "modelo_bayesiano": {
        "probabilidad_base": 0.05,
        "factores_riesgo_a_priori": {"alcoholismo": 2.8, "litiasis": 3.2},
    },
    "signDetected": [
        {"name": "Hiperlipasemia (>3x)", "bayes_lr": 24.0},
        {"name": "Dolor epigástrico", "bayes_lr": 2.1},
        {"name": "Vómitos", "bayes_lr": 1.6},
    ],
}


def infon(termino: str, estado: EstadoInfon = EstadoInfon.VALIDADO) -> Infon:
    return Infon(
        texto_origen="…",
        termino_propuesto=termino,
        termino=termino,
        estado=estado,
    )


def test_sin_evidencia_devuelve_la_probabilidad_base():
    resultado = AntigenPresentingCell().calcular({}, SKILL, [])
    assert resultado.probabilidad_porcentaje == 5.0
    assert "no se actualizó" in " ".join(resultado.traza_logica)


def test_factor_de_riesgo_eleva_la_probabilidad_previa():
    motor = AntigenPresentingCell()
    sin_factor = motor.calcular({"antecedentes": ""}, SKILL, [])
    con_factor = motor.calcular({"antecedentes": "alcoholismo crónico"}, SKILL, [])
    assert con_factor.probabilidad_previa > sin_factor.probabilidad_previa
    assert any("alcoholismo" in t for t in con_factor.traza_logica)


def test_la_evidencia_validada_actualiza_la_probabilidad():
    resultado = AntigenPresentingCell().calcular(
        {"antecedentes": ""}, SKILL, [infon("Hiperlipasemia (>3x)")]
    )
    # odds previo 0.0526 × LR 24 = 1.263 -> 55.8 %
    assert resultado.probabilidad_porcentaje > 50
    assert len(resultado.evidencia_utilizada) == 1


def test_la_evidencia_no_validada_no_mueve_la_aguja():
    """Un hallazgo en ALERTA o RUIDO se muestra, pero no cuenta como prueba."""
    motor = AntigenPresentingCell()
    base = motor.calcular({}, SKILL, [])
    for estado in (EstadoInfon.ALERTA, EstadoInfon.RUIDO):
        resultado = motor.calcular({}, SKILL, [infon("Hiperlipasemia (>3x)", estado)])
        assert resultado.probabilidad_porcentaje == base.probabilidad_porcentaje
        assert resultado.evidencia_utilizada == []


def test_un_lr_desbocado_se_recorta():
    skill = {
        "name": "Skill mal configurada",
        "modelo_bayesiano": {"probabilidad_base": 0.5},
        "signDetected": [{"name": "Signo", "bayes_lr": 999999}],
    }
    resultado = AntigenPresentingCell().calcular({}, skill, [infon("Signo")])
    assert resultado.probabilidad_porcentaje <= 99.0
    assert f"LR {LR_MAXIMO}" in " ".join(resultado.evidencia_utilizada)


def test_la_probabilidad_nunca_alcanza_el_cien_por_cien():
    skill = {
        "name": "Certeza imposible",
        "modelo_bayesiano": {"probabilidad_base": 0.9},
        "signDetected": [{"name": f"S{i}", "bayes_lr": 50} for i in range(5)],
    }
    infones = [infon(f"S{i}") for i in range(5)]
    resultado = AntigenPresentingCell().calcular({}, skill, infones)
    assert resultado.probabilidad_porcentaje < 100.0


def test_skill_sin_modelo_bayesiano_no_inventa_uno():
    assert AntigenPresentingCell().calcular({}, {"name": "Triaje"}, []) is None


def test_emparejamiento_por_termino_parcial():
    """'Hiperlipasemia' debe casar con la clave 'Hiperlipasemia (>3x)'."""
    resultado = AntigenPresentingCell().calcular({}, SKILL, [infon("Hiperlipasemia")])
    assert len(resultado.evidencia_utilizada) == 1


def test_veredicto_por_umbrales():
    motor = AntigenPresentingCell()
    baja = motor.calcular({}, SKILL, [])
    assert baja.veredicto == "BAJA_SOSPECHA"
    alta = motor.calcular(
        {"antecedentes": "alcoholismo, litiasis"},
        SKILL,
        [infon("Hiperlipasemia (>3x)"), infon("Dolor epigástrico")],
    )
    assert alta.veredicto in {"PROBABLE", "HIPOTESIS_CONFIRMADA"}


def test_los_factores_de_riesgo_de_la_nota_actual_cuentan():
    """En una primera consulta la ficha está vacía y el riesgo sólo está
    en el texto que el clínico acaba de escribir. Ignorarlo hacía que la
    probabilidad previa fuese siempre la poblacional."""
    from holonmed.models import HolonPaciente

    holon = HolonPaciente(paciente_id="nuevo")  # sin antecedentes registrados
    nota = "Varón de 45 años con litiasis biliar conocida."

    sin_nota = AntigenPresentingCell().calcular(holon.metadatos_para_bayes(), SKILL, [])
    con_nota = AntigenPresentingCell().calcular(
        holon.metadatos_para_bayes(nota), SKILL, []
    )

    assert sin_nota.probabilidad_previa == 5.0
    assert con_nota.probabilidad_previa > sin_nota.probabilidad_previa
    assert "litiasis" in " ".join(con_nota.traza_logica)


def test_los_factores_se_emparejan_por_subcadena_literal():
    """Documenta una limitación real, detectada en la primera ejecución
    con un modelo de verdad.

    El protocolo declara el factor 'alcoholismo', pero un clínico escribe
    'bebedor de riesgo'. No comparten ninguna subcadena, así que el factor
    no se aplica y la probabilidad previa se queda corta.

    No es un fallo del código sino del protocolo: la solución es declarar
    las variantes que la gente usa de verdad. Este test existe para que
    quien escriba una skill nueva sepa que el emparejamiento es literal.
    """
    from holonmed.models import HolonPaciente

    holon = HolonPaciente(paciente_id="nuevo")
    motor = AntigenPresentingCell()

    literal = motor.calcular(
        holon.metadatos_para_bayes("paciente con alcoholismo crónico"), SKILL, []
    )
    coloquial = motor.calcular(
        holon.metadatos_para_bayes("paciente bebedor de riesgo"), SKILL, []
    )

    assert "alcoholismo" in " ".join(literal.traza_logica)
    assert coloquial.probabilidad_previa == 5.0  # el factor no se detecta


# --- Evidencia negativa: lo que resta ---------------------------------

SKILL_CON_LR_NEGATIVO = {
    "name": "Pancreatitis aguda",
    "modelo_bayesiano": {"probabilidad_base": 0.5},
    "signDetected": [
        {"name": "Hiperlipasemia (>3x)", "bayes_lr": 26.6, "bayes_lr_negativo": 0.1},
        {"name": "Vómitos", "bayes_lr": 1.6},  # sin LR-: su ausencia no informa
    ],
}


def infon_ausente(termino: str) -> Infon:
    from holonmed.models import Polaridad

    return Infon(
        texto_origen="…",
        termino_propuesto=termino,
        termino=termino,
        polaridad=Polaridad.AUSENTE,
        estado=EstadoInfon.VALIDADO,
    )


def test_una_prueba_negativa_baja_la_probabilidad():
    """Una lipasa normal es la evidencia más potente en contra, y hasta
    ahora el sistema la tiraba: sólo sabía sumar."""
    motor = AntigenPresentingCell()
    base = motor.calcular({}, SKILL_CON_LR_NEGATIVO, [])
    negativo = motor.calcular(
        {}, SKILL_CON_LR_NEGATIVO, [infon_ausente("Hiperlipasemia (>3x)")]
    )

    assert base.probabilidad_porcentaje == 50.0
    assert negativo.probabilidad_porcentaje < 15.0
    assert "en contra" in " ".join(negativo.evidencia_utilizada)
    assert "[ausente]" in " ".join(negativo.evidencia_utilizada)


def test_la_presencia_y_la_ausencia_van_en_direcciones_opuestas():
    motor = AntigenPresentingCell()
    presente = motor.calcular({}, SKILL_CON_LR_NEGATIVO, [infon("Hiperlipasemia (>3x)")])
    ausente = motor.calcular(
        {}, SKILL_CON_LR_NEGATIVO, [infon_ausente("Hiperlipasemia (>3x)")]
    )
    assert presente.probabilidad_porcentaje > 50.0 > ausente.probabilidad_porcentaje


def test_una_ausencia_sin_lr_negativo_no_mueve_nada():
    """Que no haya vómitos no dice gran cosa, y el protocolo lo declara
    no declarando lr_negativo."""
    motor = AntigenPresentingCell()
    base = motor.calcular({}, SKILL_CON_LR_NEGATIVO, [])
    sin_vomitos = motor.calcular({}, SKILL_CON_LR_NEGATIVO, [infon_ausente("Vómitos")])
    assert sin_vomitos.probabilidad_porcentaje == base.probabilidad_porcentaje


def test_una_ausencia_no_validada_no_descarta_nada():
    """El error peligroso sería tomar una ausencia dudosa como prueba
    negativa: descartaría un diagnóstico sin fundamento."""
    from holonmed.models import Polaridad

    dudosa = Infon(
        texto_origen="…",
        termino_propuesto="Hiperlipasemia (>3x)",
        termino="Hiperlipasemia (>3x)",
        polaridad=Polaridad.AUSENTE,
        estado=EstadoInfon.ALERTA,
    )
    motor = AntigenPresentingCell()
    base = motor.calcular({}, SKILL_CON_LR_NEGATIVO, [])
    con_dudosa = motor.calcular({}, SKILL_CON_LR_NEGATIVO, [dudosa])
    assert con_dudosa.probabilidad_porcentaje == base.probabilidad_porcentaje
