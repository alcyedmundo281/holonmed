"""Tests de la procedencia de un infón.

La regla que se comprueba aquí es la que más fácil se rompe sola con el
tiempo: que lo que clasifica es **quién lo asevera**, no de qué instrumento
salió el número.
"""

import pytest

from holonmed.core.procedencia import (
    PERMITIDAS,
    Procedencia,
    admite,
    clasificar_por_defecto,
    motivo_del_rechazo,
)
from holonmed.models import OrigenTic


def test_lo_que_el_paciente_refiere_es_subjetivo_aunque_sea_una_cifra():
    """Una glucemia traída de casa es el relato de una lectura que nadie vio.

    Es la regla entera en un caso: el instrumento no clasifica, el que
    asevera sí. Confundirlos llevaría a auditar contra un punto de corte una
    cifra que nadie midió.
    """
    assert admite(OrigenTic.PACIENTE, Procedencia.SUBJETIVO)
    assert not admite(OrigenTic.PACIENTE, Procedencia.OBJETIVO)
    assert "su relato de una lectura" in motivo_del_rechazo(
        OrigenTic.PACIENTE, Procedencia.OBJETIVO
    )


@pytest.mark.parametrize(
    "origen", [OrigenTic.LABORATORIO, OrigenTic.IMAGEN, OrigenTic.FARMACIA]
)
def test_una_maquina_no_tiene_sintomas(origen):
    assert admite(origen, Procedencia.OBJETIVO)
    assert not admite(origen, Procedencia.SUBJETIVO)


@pytest.mark.parametrize("origen", [OrigenTic.CONSULTA, OrigenTic.ENFERMERIA])
def test_quien_escucha_y_explora_puede_las_dos(origen):
    """Una nota de consulta lleva las dos clases en el mismo párrafo.

    «Refiere dolor epigástrico desde ayer» es subjetivo aunque lo teclee el
    médico; «abdomen blando, sin defensa» es objetivo.
    """
    assert admite(origen, Procedencia.SUBJETIVO)
    assert admite(origen, Procedencia.OBJETIVO)


def test_holonmed_deduce_y_no_asevera():
    """Un infón que el sistema presentara como observado afirmaría haber visto."""
    assert admite(OrigenTic.HOLONMED, Procedencia.DERIVADO)
    assert not admite(OrigenTic.HOLONMED, Procedencia.SUBJETIVO)
    assert not admite(OrigenTic.HOLONMED, Procedencia.OBJETIVO)
    assert "deduce" in motivo_del_rechazo(OrigenTic.HOLONMED, Procedencia.OBJETIVO)


def test_un_origen_que_no_declara_nada_no_recibe_nada():
    """Ante lo que no sabemos leer, el sistema se detiene.

    Suponer el caso más permisivo para `otro` sería justo la puerta por la
    que se cuela todo lo que no quiso declararse.
    """
    for procedencia in Procedencia:
        assert not admite(OrigenTic.OTRO, procedencia)
    assert "no declara" in motivo_del_rechazo(OrigenTic.OTRO, Procedencia.OBJETIVO)


def test_solo_se_clasifica_por_defecto_a_quien_no_tiene_alternativa():
    assert clasificar_por_defecto(OrigenTic.LABORATORIO) is Procedencia.OBJETIVO
    assert clasificar_por_defecto(OrigenTic.PACIENTE) is Procedencia.SUBJETIVO
    assert clasificar_por_defecto(OrigenTic.HOLONMED) is Procedencia.DERIVADO


def test_a_la_consulta_no_se_le_elige_por_ella():
    """Elegir por quien puede las dos es mezclar lo contado con lo comprobado.

    Es el error que la regla existe para impedir, así que el valor por
    defecto se niega en vez de arriesgar el más frecuente.
    """
    assert clasificar_por_defecto(OrigenTic.CONSULTA) is None
    assert clasificar_por_defecto(OrigenTic.ENFERMERIA) is None
    assert clasificar_por_defecto(OrigenTic.OTRO) is None


def test_la_tabla_cubre_todos_los_actores():
    """Un actor nuevo sin fila entraría con el conjunto vacío y se notaría.

    Pero se prefiere que falle aquí, al añadirlo, y no el día que alguien
    intente registrar un infón y no entienda por qué se rechaza.
    """
    assert set(PERMITIDAS) == set(OrigenTic)
