"""Tests del protocolo real de tromboembolia pulmonar.

Fijan una decisión de seguridad: los odds ratio de casos y controles contra
población general NO entran al cálculo, porque se aplicarían sobre una base de
pacientes que ya son sospechosos y contarían dos veces la misma sospecha.
"""

from pathlib import Path

import pytest

from holonmed.config import Settings
from holonmed.core.bayes import AntigenPresentingCell
from holonmed.core.skills import SkillManager
from holonmed.models import EstadoInfon, Infon

SKILLS = Path(__file__).resolve().parents[1] / "skills"


@pytest.fixture(scope="module")
def tep():
    skill = SkillManager(Settings(skills_dir=SKILLS, _env_file=None)).cargar(
        "tromboembolia_pulmonar"
    )
    assert skill is not None
    return skill


def _infon(termino: str) -> Infon:
    return Infon(
        texto_origen="…",
        termino_propuesto=termino,
        termino=termino,
        estado=EstadoInfon.VALIDADO,
    )


def test_la_base_es_la_de_sospecha_y_no_cero(tep):
    assert tep.json_principal["modelo_bayesiano"]["probabilidad_base"] == 0.09


def test_ningun_or_de_poblacion_general_entra_al_calculo(tep):
    assert tep.json_principal["modelo_bayesiano"]["factores_riesgo_a_priori"] == {}


def test_cirugia_reciente_sin_hallazgos_no_mueve_la_probabilidad(tep):
    """El caso que daba 68 % PROBABLE: cirugía de cadera y disnea, sin LR."""
    resultado = AntigenPresentingCell().calcular(
        {"antecedentes": "cirugía de cadera hace 5 días, anticonceptivos, cáncer"},
        tep.json_principal,
        [_infon("Taquicardia"), _infon("Hipoxemia")],
    )
    assert resultado.probabilidad_previa == 9.0
    assert resultado.probabilidad_porcentaje == 9.0
    assert resultado.veredicto == "BAJA_SOSPECHA"


def test_un_hallazgo_con_lr_medido_si_mueve_la_probabilidad(tep):
    resultado = AntigenPresentingCell().calcular(
        {}, tep.json_principal, [_infon("Ventrículo derecho dilatado en ecografía")]
    )
    assert resultado.probabilidad_porcentaje > 9.0
    assert len(resultado.evidencia_utilizada) == 1
