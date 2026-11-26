"""La orden de cristalizar escrita en el chat, reconocida sin modelo.

El router es un modelo: con la orden escrita en la primera palabra puede
clasificarla como consulta general, y entonces la narrativa no pasa por la
validación y vuelve como texto libre. Una orden explícita se decide aquí. Sólo
elige qué **proponer**: guardar sigue exigiendo la confirmación nombrada.
"""

import re

_ORDEN = re.compile(
    r"\A\s*(?:por\s+favor[\s,]+)?"
    r"(?:cristaliza(?:r|me)?|cristal[ií]za(?:me|lo|la)|cristalice|cristal[ií]ceme)"
    r"(?!\w)",
    re.IGNORECASE,
)

# Lo que puede ir entre el verbo y los dos puntos sin ser parte de la narrativa.
# Es una lista cerrada, y ninguna palabra es un rótulo de sección («S», «O»).
_RELLENO = (
    r"esta|este|la|el|siguiente|narrativa|nota|texto|evoluci[oó]n|"
    r"sint[eé]tic[ao]|cl[ií]nic[ao]|de|por\s+favor"
)
_CABECERA = re.compile(rf"\A(?:[\s,]+(?:{_RELLENO})(?!\w))*[ \t]*:", re.IGNORECASE)


def narrativa_de_la_orden(mensaje: str) -> str | None:
    """La narrativa que acompaña a la orden, o `None` si no hay orden.

    La cabecera sólo se recorta cuando termina en dos puntos y está hecha de
    palabras de la lista. Si no, todo lo que sigue al verbo es narrativa:
    sobrar una palabra se ve al revisar la propuesta; perderla, no.

    Devuelve cadena vacía si la orden llega sin nada que procesar.
    """
    orden = _ORDEN.match(mensaje)
    if orden is None:
        return None
    resto = mensaje[orden.end() :]
    cabecera = _CABECERA.match(resto)
    if cabecera is not None:
        resto = resto[cabecera.end() :]
    resto = resto.strip()
    return resto if any(c.isalnum() for c in resto) else ""
