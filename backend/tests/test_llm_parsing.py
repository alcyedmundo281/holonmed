"""Tests del parseo defensivo de respuestas del LLM.

Los modelos locales devuelven JSON envuelto en vallas markdown, precedido
de charla o directamente roto. El pipeline nunca debe romperse por eso, y
tampoco debe rellenar los huecos con suposiciones.
"""

from holonmed.llm.client import extraer_json


def test_json_limpio():
    assert extraer_json('{"valido": true}') == {"valido": True}


def test_json_en_valla_markdown():
    crudo = 'Aquí tienes:\n```json\n{"valido": false, "confianza": 80}\n```\nEspero que sirva.'
    assert extraer_json(crudo) == {"valido": False, "confianza": 80}


def test_json_en_valla_sin_etiqueta():
    assert extraer_json('```\n{"a": 1}\n```') == {"a": 1}


def test_json_precedido_de_charla():
    crudo = 'Claro. El resultado es {"infones": [{"termino_clinico": "Fiebre"}]}'
    assert extraer_json(crudo)["infones"][0]["termino_clinico"] == "Fiebre"


def test_json_anidado_se_conserva_entero():
    crudo = '{"a": {"b": {"c": [1, 2]}}}'
    assert extraer_json(crudo)["a"]["b"]["c"] == [1, 2]


def test_texto_sin_json_devuelve_vacio():
    assert extraer_json("No he podido procesar la petición.") == {}


def test_cadena_vacia():
    assert extraer_json("") == {}


def test_json_roto_devuelve_vacio_en_vez_de_adivinar():
    assert extraer_json('{"valido": tru') == {}


def test_una_lista_en_la_raiz_no_se_acepta():
    """El contrato es un objeto. Una lista se rechaza en vez de adaptarse."""
    assert extraer_json('[{"a": 1}]') == {}
