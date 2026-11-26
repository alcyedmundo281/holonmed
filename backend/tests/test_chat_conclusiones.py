"""Las reglas que reconocen la orden de cristalizar y retienen conclusiones.

Cómo las usa el chat se prueba en `test_chat_confirmacion.py`. Todo el texto es
sintético.
"""

import pytest

from holonmed.core.consulta_libre import CONCLUSION, INDICACION, motivos_de_retencion
from holonmed.core.orden_chat import narrativa_de_la_orden

# Fragmentos de lo que contestó un modelo local pequeño a una narrativa
# sintética que el router tomó por consulta general.
RESPUESTA_OBSERVADA = [
    "Este valor sugiere una posible pancreatitis aguda.",
    "**Posibles Diagnósticos Diferenciales:**",
    "* **Pancreatitis Aguda:** Es la causa más probable dada la elevación.",
    "La combinación sugiere una alta probabilidad de pancreatitis aguda.",
    "Se recomienda repetir el análisis en sangre.",
    "**Próximos Pasos:**",
    "Se podrían solicitar otros marcadores inflamatorios.",
    "Estudios para determinar la etiología y guiar el tratamiento.",
]


@pytest.mark.parametrize(
    ("mensaje", "narrativa"),
    [
        ("Cristalizar: S: Refiere tos.", "S: Refiere tos."),
        ("Cristaliza esta narrativa sintética: Amilasa 900.", "Amilasa 900."),
        ("  por favor, cristaliza la nota:\nS: tos\nO: x", "S: tos\nO: x"),
        ("CRISTALÍZAME: refiere cefalea", "refiere cefalea"),
        # Sin dos puntos, o con palabras fuera de la lista, no se recorta nada.
        ("cristaliza refiere cefalea", "refiere cefalea"),
        ("Cristaliza el dolor de ayer: leve", "el dolor de ayer: leve"),
        ("Cristaliza la nota S: tos", "la nota S: tos"),
        ("Cristaliza\nS: tos", "S: tos"),
    ],
)
def test_la_orden_deja_la_narrativa_entera(mensaje, narrativa):
    assert narrativa_de_la_orden(mensaje) == narrativa


@pytest.mark.parametrize(
    "mensaje",
    [
        "¿Cristalizar guarda algo?",
        "No cristalices esta nota",
        "¿Qué es la cristaluria?",
        "cristalizados en el sedimento: ¿qué significa?",
        "Agenda una cita para cristalizar la nota",
    ],
)
def test_lo_que_no_es_una_orden_no_se_toma_por_orden(mensaje):
    assert narrativa_de_la_orden(mensaje) is None


@pytest.mark.parametrize(
    "mensaje", ["Cristalizar", "Cristaliza esta nota: ", "cristaliza:."]
)
def test_la_orden_sin_narrativa_queda_vacia(mensaje):
    assert narrativa_de_la_orden(mensaje) == ""


@pytest.mark.parametrize("respuesta", RESPUESTA_OBSERVADA)
def test_cada_conclusion_observada_se_retiene(respuesta):
    assert motivos_de_retencion(respuesta)


@pytest.mark.parametrize(
    ("respuesta", "categoria"),
    [
        ("El paciente tiene una pancreatitis.", CONCLUSION),
        ("Los datos son compatibles con colecistitis.", CONCLUSION),
        ("Probablemente se trate de una colecistitis.", CONCLUSION),
        ("El diagnóstico más probable es otro.", CONCLUSION),
        ("Se debe iniciar hidratación.", INDICACION),
        ("Administre analgesia.", INDICACION),
        ("Plan de manejo: observación.", INDICACION),
        # El formato, las tildes que falten y lo invisible no la esconden.
        ("SE **RECOMIENDA** repetirlo.", INDICACION),
        ("Se reco​mienda repetirlo.", INDICACION),
        ("la causa mas\nprobable", CONCLUSION),
    ],
)
def test_las_formulas_se_reconocen(respuesta, categoria):
    assert categoria in motivos_de_retencion(respuesta)


@pytest.mark.parametrize(
    "respuesta",
    [
        "La amilasa es una enzima que hidroliza el almidón. Su medición sérica "
        "ayuda a evaluar la función pancreática y a diagnosticar la pancreatitis.",
        "En el historial constan hiperamilasemia y dolor epigástrico.",
        "No tengo datos sobre la lipasa.",
    ],
)
def test_una_explicacion_o_un_resumen_se_ensenan(respuesta):
    assert motivos_de_retencion(respuesta) == []
