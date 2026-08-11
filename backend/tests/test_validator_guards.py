"""Tests de las guardas de colisión del validador ontológico.

Estos casos vienen de errores reales observados con modelos locales:
confundir lipasa con lípidos, o amilasa con potasio. Son fallos que un
motor de similitud comete con naturalidad porque las cadenas se parecen, y
que en una historia clínica son graves.
"""

import pytest

from holonmed.core.validator import Match, hay_colision


@pytest.mark.parametrize(
    ("entrada", "candidato"),
    [
        ("hiperlipasemia", "hiperlipemia"),  # enzima vs. grasas
        ("hiperamilasemia", "hiperpotasemia"),  # enzima vs. electrolito
        ("hiperamilasemia", "hiperkalemia"),  # idem, otra nomenclatura
        ("amilasa elevada", "lipasa elevada"),  # dos enzimas distintas
        ("hipocalcemia", "hipercalcemia"),  # dirección invertida
        ("hiponatremia", "hipopotasemia"),  # sodio vs. potasio
        ("hipocalcemia", "hiponatremia"),  # calcio vs. sodio
        ("hiperglucemia", "glucosuria"),  # en sangre vs. en orina
        ("hematuria", "hematemesis"),  # sangre en orina vs. en vómito
    ],
)
def test_colisiones_prohibidas_se_detectan(entrada, candidato):
    assert hay_colision(entrada, candidato) is not None


@pytest.mark.parametrize(
    ("entrada", "candidato"),
    [
        ("hiperamilasemia", "amilasa elevada"),  # sinónimos legítimos
        ("dolor epigástrico", "dolor en epigastrio"),
        ("leucocitosis", "leucocitos elevados"),
        ("fiebre", "hipertermia"),
        ("astenia", "cansancio"),
    ],
)
def test_los_sinonimos_legitimos_no_se_bloquean(entrada, candidato):
    assert hay_colision(entrada, candidato) is None


def test_la_colision_es_simetrica():
    assert hay_colision("hiperlipasemia", "hiperlipemia") is not None
    assert hay_colision("hiperlipemia", "hiperlipasemia") is not None


def test_el_constructor_de_ruido_no_produce_codigo():
    """Un match de ruido nunca puede arrastrar un código ni un concepto."""
    match = Match.ruido("término inventado", "sin_candidatos")
    assert match.es_ruido
    assert match.codigo is None
    assert match.concepto_id is None
    assert match.score == 0.0
    assert match.metodo == "sin_candidatos"
