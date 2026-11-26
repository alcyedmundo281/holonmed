"""Lo que se le exige a una cita, y a un alta pedida por chat.

La fecha tiene que decir día y hora sin que nadie los complete, llegue por el
chat o por `/api/citas`. Además, los campos que devuelve el router son texto de
un modelo: aquí se comprueba que estén **escritos en el mensaje**. Lo que falte
o admita dos lecturas se rechaza.

La fecha no pasa por un intérprete de lenguaje libre: rellena lo que no se
dijo (la hora la toma del reloj, y un «10» suelto se vuelve una fecha). La
gramática es cerrada y el texto entero tiene que encajar en ella.
"""

import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any

_MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_NUMERO_DE_MES = {nombre: n for n, nombre in enumerate(_MESES, start=1)}
_NUMERO_DE_MES["setiembre"] = 9

_DIAS_RELATIVOS = {"hoy": 0, "mañana": 1, "pasado mañana": 2}

_FECHA = re.compile(
    r"(?:(?:para|el)\s+)*(?:d[ií]a\s+)?"
    r"(?:(?P<relativo>hoy|pasado\s+mañana|mañana)"
    r"|(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<a>\d{4})"
    r"|(?P<ia>\d{4})-(?P<im>\d{2})-(?P<id>\d{2})"
    rf"|(?P<ld>\d{{1,2}})\s+de\s+(?P<mes>{'|'.join(_NUMERO_DE_MES)})"
    r"\s+(?:de|del)\s+(?P<la>\d{4}))"
    r"(?:\s*,)?\s+(?:a\s+las?\s+)?"
    r"(?P<hora>[01]?\d|2[0-3]):(?P<minuto>[0-5]\d)(?:\s*h)?"
)

FORMATOS_DE_FECHA = (
    "Escribe día y hora juntos (24 h, con minutos): «dd/mm/aaaa a las hh:mm», "
    "«d de mes de aaaa a las hh:mm» o «mañana a las hh:mm»."
)


class PeticionInvalida(ValueError):
    """La petición no se puede ofrecer para su aprobación."""


def citado_del_mensaje(valor: Any, mensaje: str, campo: str) -> str:
    """El trozo del mensaje original que coincide con `valor`.

    Sólo se toleran diferencias de mayúsculas y de espacios, y lo que se
    devuelve es lo que escribió la persona. Un valor ausente, o que no esté
    en el mensaje, lo puso el modelo y no se usa.
    """
    if not isinstance(valor, str) or not valor.strip():
        raise PeticionInvalida(f"Falta {campo} en el mensaje.")
    partes = unicodedata.normalize("NFC", valor).split()
    patron = r"(?<!\w)" + r"\s+".join(map(re.escape, partes)) + r"(?!\w)"
    hallado = re.search(patron, unicodedata.normalize("NFC", mensaje), re.IGNORECASE)
    if hallado is None:
        raise PeticionInvalida(
            f"No se usa {campo}: «{valor.strip()}» no está escrito así en el mensaje."
        )
    return hallado.group(0)


def interpretar_fecha(texto: str, ahora: datetime) -> datetime:
    """Día y hora que dice `texto`, o el motivo por el que no se aceptan."""
    plano = unicodedata.normalize("NFC", texto).strip().casefold()
    hallado = _FECHA.fullmatch(plano)
    if hallado is None:
        raise PeticionInvalida(
            f"Como fecha se leyó «{texto}», que no dice día y hora sin "
            f"ambigüedad. {FORMATOS_DE_FECHA}"
        )
    g = hallado.groupdict()
    try:
        if g["relativo"]:
            dias = _DIAS_RELATIVOS[" ".join(g["relativo"].split())]
            dia = ahora.date() + timedelta(days=dias)
            anio, mes, numero = dia.year, dia.month, dia.day
        elif g["d"]:
            anio, mes, numero = int(g["a"]), int(g["m"]), int(g["d"])
        elif g["ia"]:
            anio, mes, numero = int(g["ia"]), int(g["im"]), int(g["id"])
        else:
            anio, mes, numero = int(g["la"]), _NUMERO_DE_MES[g["mes"]], int(g["ld"])
        fecha = datetime(anio, mes, numero, int(g["hora"]), int(g["minuto"]))
    except ValueError as exc:
        raise PeticionInvalida(f"La fecha «{texto}» no existe.") from exc
    if fecha <= ahora:
        raise PeticionInvalida(f"La fecha «{texto}» ya pasó.")
    return fecha
