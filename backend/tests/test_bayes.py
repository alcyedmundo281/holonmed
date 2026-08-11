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
        termino_snomed=termino,
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
        resultado = motor.calcular(
            {}, SKILL, [infon("Hiperlipasemia (>3x)", estado)]
        )
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
    resultado = AntigenPresentingCell().calcular(
        {}, SKILL, [infon("Hiperlipasemia")]
    )
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
