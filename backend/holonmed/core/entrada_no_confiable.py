"""Texto dirigido al sistema dentro de una narrativa clínica.

La narrativa es entrada no confiable: entra entera en el prompt del
extractor y en el del auditor, y una frase dentro de una nota puede leerse
como instrucción. Observado con un modelo local sobre texto sintético: una
orden pegada en la nota produjo un hallazgo VALIDADO y un `resumen` que
daba por diagnosticado lo que la orden mandaba registrar.

Este módulo no le pregunta nada a ningún modelo —preguntar al modelo si lo
están manipulando es preguntárselo a quien puede estar manipulado—. Son
patrones fijos, y el pipeline decide con ellos.

LO QUE NO GARANTIZA

Es una lista de formas conocidas, en español y en inglés. Una paráfrasis,
otro idioma o una orden redactada como prosa clínica («consta cáncer
confirmado») pasan sin señal. **Que no haya señales no vuelve confiable el
texto.** Es una capa más; no sustituye a la revisión humana.

QUÉ BUSCA, Y QUÉ NO

Busca texto que le habla *al sistema*: anular sus instrucciones, mandarle
escribir en la historia, redefinir qué es, o dictarle el formato de su
respuesta. No busca verbos clínicos en imperativo: «Receta: paracetamol» o
«tomar cada 8 horas» son una nota normal. Tampoco «el paciente ignora las
indicaciones»: se exige hablar de *instrucciones* del sistema o anteriores.

Ante la duda se prefiere señalar. Un falso positivo cuesta una revisión; un
falso negativo, un diagnóstico que nadie hizo escrito en la historia.
"""

import re
import unicodedata

from ..models import SenalInstruccion

_ANULAR = (
    r"(?:ignor(?:a|e|ad|en|ar)|olvid(?:a|e|ad|en|ar)|omit(?:e|a|an|id|ir)"
    r"|descart(?:a|e|ad|en|ar)|desestim(?:a|e|ad|en|ar)|anul(?:a|e|ad|en|ar)"
    r"|sobrescrib(?:e|a|id|an|ir))"
)

_ESCRIBIR = (
    r"(?:registr(?:a|e|ad|en)|anot(?:a|e|ad|en)|escrib(?:e|a|id|an)"
    r"|apunt(?:a|e|ad|en)|consign(?:a|e|ad|en)|document(?:a|e|ad|en)"
    r"|marc(?:a|ad)|marqu(?:e|en)|clasific(?:a|ad)|clasifiqu(?:e|en)"
    r"|respond(?:e|a|ed|an)|devuelv(?:e|a|an)|anad(?:e|a|id|an)"
    r"|incluy(?:e|a|an)|extra(?:e|iga|igan)|diagnostic(?:a|ad)"
    r"|diagnostiqu(?:e|en))"
)

# Comienzo de oración. Es lo que separa la orden («Registra que…») del
# relato («el monitor registra que…», «se anota que…»).
_INICIO = (
    r"(?:^|(?<=[.:;!?¡\n\"'«\[\(>*#-]))[ \t]*"
    r"(?:(?:por favor|ahora|ademas|y),?[ \t]+)?"
)

_PATRONES: dict[str, tuple[str, ...]] = {
    "anulacion_de_instrucciones": (
        rf"\b{_ANULAR}\b[^.\n]{{0,40}}?\binstrucciones[ \t]+"
        r"(?:anteriores|previas|precedentes|del sistema|de arriba)\b",
        rf"\b{_ANULAR}\b[ \t]+(?:todas[ \t]+(?:las|tus)|tus)[ \t]+instrucciones\b",
        rf"\b{_ANULAR}\b[^.\n]{{0,40}}?\b(?:prompt|reglas anteriores)\b",
        r"\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}?"
        r"\b(?:instructions|instruction|prompt|rules)\b",
    ),
    "orden_de_escritura": (
        rf"{_INICIO}{_ESCRIBIR}[ \t]+"
        r"(?:en (?:el|la) (?:historia|expediente|ficha)[^.\n]{0,20}?[ \t])?que\b",
        rf"{_INICIO}{_ESCRIBIR}[ \t][^.\n]{{0,60}}?\bcomo (?:validado|confirmado)\b",
    ),
    "dirigido_al_modelo": (
        r"\b(?:system prompt|prompt del sistema|instrucciones del sistema)\b",
        r"\ba partir de ahora,?[ \t]+(?:eres|actua|responde|debes)\b",
        rf"{_INICIO}(?:eres|actua como)[ \t]+(?:un|una)[ \t]+"
        r"(?:asistente|modelo|ia|inteligencia artificial|sistema)\b",
        rf"{_INICIO}(?:asistente|modelo|sistema|ia),[ \t]+{_ESCRIBIR}\b",
        r"\byou are now\b",
        r"<\|[a-z_]+\|>|\[/?inst\]|<(?:start|end)_of_turn>|</?system>",
    ),
    "formato_de_salida": (
        r"\"(?:valido|es_valido|ausencia_confirmada|termino_clinico|infones)\"[ \t]*:",
        rf"{_INICIO}respond(?:e|a|ed|an)[ \t]+(?:(?:solo|unicamente)[ \t]+)?"
        r"(?:en json|con el numero)\b",
    ),
}

_COMPILADOS = {
    categoria: tuple(re.compile(patron, re.MULTILINE) for patron in patrones)
    for categoria, patrones in _PATRONES.items()
}

AVISO_RESUMEN = (
    "ALERTA: la narrativa contiene texto dirigido al sistema. Se retiene el "
    "resumen del modelo, ningún hallazgo queda validado y no se calcula "
    "inferencia. Revisar el texto original."
)


def _aplanar(texto: str) -> str:
    """Minúsculas, sin acentos, sin caracteres invisibles y sin huecos dobles.

    Los invisibles (categoría `Cf`: ancho cero, guion blando) se quitan
    porque parten una palabra para el patrón y no para quien la lee. Los
    saltos de línea se conservan: marcan comienzo de oración.
    """
    plano = unicodedata.normalize("NFKD", texto).casefold()
    plano = "".join(
        c
        for c in plano
        if not unicodedata.combining(c) and unicodedata.category(c) != "Cf"
    )
    return re.sub(r"[^\S\n]+", " ", plano)


def detectar_instrucciones(texto: str) -> list[SenalInstruccion]:
    """Las señales encontradas, una por categoría y coincidencia distinta.

    El fragmento sale del texto aplanado, no del original: sirve para que
    quien revisa localice la frase, no como cita textual.
    """
    plano = _aplanar(texto)
    senales: list[SenalInstruccion] = []
    vistas: set[tuple[str, str]] = set()
    for categoria, patrones in _COMPILADOS.items():
        for patron in patrones:
            for hallado in patron.finditer(plano):
                fragmento = hallado.group(0).strip()[:160]
                if (categoria, fragmento) not in vistas:
                    vistas.add((categoria, fragmento))
                    senales.append(
                        SenalInstruccion(categoria=categoria, fragmento=fragmento)
                    )
    return senales
