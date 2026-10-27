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


# --- Un `null` del modelo no es una cadena ---------------------------------
#
# `crudo.get(clave, "")` no protege de un `null`: la clave existe, así que el
# defecto no se aplica y `str(None)` da 'None' —cuatro caracteres, verdadera—.
# Se vio corriendo contra Ollama real: un infón salió a pantalla como
#
#     [RUIDO    ] None [AUSENTE]
#
# Es la misma forma que el `tipo:` sin valor de `skills.py`, ahora en el camino
# por donde entra todo lo que dice el modelo.

import pytest  # noqa: E402

from holonmed.core.pipeline import _texto_del_modelo  # noqa: E402


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ({}, ""),  # la clave falta
        ({"t": ""}, ""),  # vacía
        ({"t": "   "}, ""),  # sólo espacios
        ({"t": None}, ""),  # NULL: el caso que fallaba
        ({"t": " Fiebre "}, "Fiebre"),  # normal
        ({"t": 38.5}, "38.5"),  # un número sigue siendo texto
    ],
)
def test_un_campo_nulo_del_modelo_se_lee_como_vacio(crudo, esperado):
    assert _texto_del_modelo(crudo, "t") == esperado


def test_un_termino_nulo_no_produce_un_infon_llamado_None():
    """La consecuencia, afirmada donde se ve: sin término no hay infón.

    Con `str(crudo.get(...))` el infón se creaba con `termino='None'`, pasaba
    la validación ontológica completa —gastando una llamada al auditor por un
    no-hallazgo— y llegaba a la pantalla del clínico.
    """
    assert _texto_del_modelo({"termino_clinico": None}, "termino_clinico") == ""


def test_una_cita_nula_no_se_fabrica():
    """`texto_origen` es la cita de la nota: inventarla es peor que perderla.

    Un infón con `texto_origen='None'` afirma haberse apoyado en un fragmento
    del texto del clínico que no existe.
    """
    assert _texto_del_modelo({"texto_origen": None}, "texto_origen") == ""
