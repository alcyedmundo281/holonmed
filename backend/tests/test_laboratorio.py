"""Tests del encaminamiento de resultados de laboratorio.

Lo que se comprueba es que **nada se descarte** y que lo que nadie pidió no
acabe contando como prueba de una hipótesis que no lo pidió.
"""

from holonmed.core.laboratorio import (
    Destino,
    OrdenPendiente,
    encaminar,
    repartir,
)
from holonmed.models import EstadoInfon, Infon, Polaridad

ORDEN = OrdenPendiente(
    orden_id="o1",
    termino="Potasio sérico",
    codigo="HM:0900",
    sistema="holonmed",
    concepto_id=42,
)


def test_lo_que_responde_a_una_orden_cuenta_como_evidencia():
    resultado = encaminar("Potasio sérico", [ORDEN], concepto_id=42)

    assert resultado.destino is Destino.EVIDENCIA
    assert resultado.orden_id == "o1"
    assert "mismo concepto" in resultado.razon


def test_se_empareja_por_concepto_antes_que_por_codigo_o_termino():
    """El concepto es identidad; el término es una cadena.

    Bajar directamente al término emparejaría cosas que sólo se parecen.
    """
    otra = OrdenPendiente(orden_id="o2", termino="Otra cosa", concepto_id=42)
    assert encaminar("Da igual", [otra], concepto_id=42).orden_id == "o2"


def test_se_empareja_por_codigo_dentro_de_su_sistema():
    resultado = encaminar(
        "Nombre distinto", [ORDEN], codigo="HM:0900", sistema="holonmed"
    )
    assert resultado.destino is Destino.EVIDENCIA
    assert "mismo código" in resultado.razon


def test_un_codigo_igual_de_otro_sistema_no_empareja():
    """Los códigos sólo son únicos dentro de su vocabulario."""
    resultado = encaminar("X", [ORDEN], codigo="HM:0900", sistema="snomed")
    assert resultado.destino is Destino.PROBLEMA_NUEVO


def test_el_termino_empareja_aunque_falten_tildes():
    """«Potasio serico» y «Potasio sérico» son la misma petición."""
    assert encaminar("potasio  SERICO", [ORDEN]).destino is Destino.EVIDENCIA


def test_lo_que_nadie_pidio_abre_un_problema_y_no_se_descarta():
    """Es Weed literal: cuando aparece un problema nuevo, va a la lista."""
    resultado = encaminar("Hipopotasemia", [ORDEN], concepto_id=99)

    assert resultado.destino is Destino.PROBLEMA_NUEVO
    assert resultado.orden_id is None
    assert not resultado.cuenta_como_evidencia
    assert "no responde a ninguna orden" in resultado.razon
    assert "lista de problemas" in resultado.razon


def test_sin_ninguna_orden_todo_es_serendipia():
    reparto = repartir(["Sodio", "Cloro"], [])

    assert reparto.evidencia == ()
    assert reparto.problemas_nuevos == ("Sodio", "Cloro")
    assert reparto.hubo_serendipia


def test_una_tanda_se_reparte_en_dos():
    reparto = repartir(["Potasio sérico", "Calcio"], [ORDEN])

    assert reparto.evidencia == ("Potasio sérico",)
    assert reparto.problemas_nuevos == ("Calcio",)


def test_un_hallazgo_serendipico_no_suma_en_la_inferencia():
    """Contaría como prueba de una hipótesis un dato recogido para otra cosa.

    Sigue en la historia y en la lista de problemas: lo que cambia no es si
    entra, sino de qué es evidencia.
    """
    pedido = Infon(
        texto_origen="K 5.9",
        termino_propuesto="potasio",
        termino="Hiperpotasemia",
        estado=EstadoInfon.VALIDADO,
        polaridad=Polaridad.PRESENTE,
    )
    serendipico = pedido.model_copy(update={"abre_problema": True})

    assert pedido.confirma
    assert not serendipico.confirma
    # Pero sigue siendo un hallazgo válido, y sigue en la historia.
    assert serendipico.es_valido


def test_el_defecto_es_que_no_abre_problema():
    """Es el caso de todo lo escrito antes de este ciclo."""
    infon = Infon(
        texto_origen="x", termino_propuesto="x", termino="X", estado=EstadoInfon.VALIDADO
    )
    assert not infon.abre_problema
    assert infon.responde_a is None
    assert infon.confirma
