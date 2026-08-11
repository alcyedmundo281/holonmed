"""Tests de las guardas de colisión del validador ontológico.

Estos casos vienen de errores reales observados en producción con modelos
locales: confundir lipasa con lípidos, o amilasa con potasio. Son fallos
que un motor de similitud comete con naturalidad porque las cadenas se
parecen, y que en una historia clínica son graves.
"""

import pytest

from holonmed.core.snomed import SnomedMatch, hay_colision


@pytest.mark.parametrize(
    ("entrada", "candidato"),
    [
        ("hiperlipasemia", "hiperlipemia"),  # enzima vs. grasas
        ("hiperamilasemia", "hiperpotasemia"),  # enzima vs. electrolito
        ("amilasa elevada", "lipasa elevada"),  # dos enzimas distintas
        ("hipocalcemia", "hipercalcemia"),  # dirección invertida
        ("hiponatremia", "hipokalemia"),  # sodio vs. potasio
    ],
)
def test_colisiones_prohibidas_se_detectan(entrada, candidato):
    assert hay_colision(entrada, candidato) is not None


@pytest.mark.parametrize(
    ("entrada", "candidato"),
    [
        ("hiperamilasemia", "amilasa elevada"),  # sinónimos legítimos
        ("dolor epigástrico", "dolor en epigastrio"),
        ("leucocitosis", "recuento de leucocitos elevado"),
        ("fiebre", "hipertermia"),
    ],
)
def test_los_sinonimos_legitimos_no_se_bloquean(entrada, candidato):
    assert hay_colision(entrada, candidato) is None


def test_la_colision_es_simetrica():
    assert hay_colision("hiperlipasemia", "hiperlipemia") is not None
    assert hay_colision("hiperlipemia", "hiperlipasemia") is not None


def test_el_constructor_de_ruido_no_produce_codigo():
    """Un match de ruido nunca puede arrastrar un SNOMED ID."""
    match = SnomedMatch.ruido("término inventado", "sin_candidatos")
    assert match.es_ruido
    assert match.snomed_id is None
    assert match.score == 0.0
    assert match.metodo == "sin_candidatos"
