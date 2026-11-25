"""Lo que se le exige a una receta extraída antes de enseñarla.

La salida del extractor es texto de un modelo. Antes de que una persona
pueda aprobarla tiene que tener una forma cerrada: lo que aquí no está
declarado no llega ni a la propuesta ni al registro, para que quien
confirma vea todo lo que se va a escribir.
"""

from typing import Any

from ..models import ItemReceta

# El campo canónico y el nombre en inglés que algunos modelos devuelven.
_CAMPOS = (
    ("farmaco", "drug"),
    ("concentracion", "concentration"),
    ("indicaciones", "instructions"),
)


class ExtraccionInvalida(ValueError):
    """La extracción no se puede ofrecer para su aprobación."""


def _texto(valor: Any, campo: str) -> str:
    if valor is None:
        return ""
    if not isinstance(valor, str):
        raise ExtraccionInvalida(f"El campo «{campo}» no es texto.")
    return valor.strip()


def validar_extraccion(datos: dict[str, Any]) -> tuple[list[ItemReceta], str]:
    """Los ítems y las indicaciones generales, o el motivo del rechazo.

    Un ítem defectuoso invalida la receta entera. Descartar sólo ése
    entregaría una receta a la que le falta un fármaco sin que se note.
    """
    crudos = datos.get("items") or datos.get("rx_items")
    if not crudos:
        raise ExtraccionInvalida("No se identificaron medicamentos en la petición.")
    if not isinstance(crudos, list):
        raise ExtraccionInvalida("La lista de medicamentos no es una lista.")

    items: list[ItemReceta] = []
    for crudo in crudos:
        if not isinstance(crudo, dict):
            raise ExtraccionInvalida("Un medicamento no tiene la forma esperada.")
        campos = {
            campo: _texto(crudo.get(campo) or crudo.get(alias), campo)
            for campo, alias in _CAMPOS
        }
        if not campos["farmaco"]:
            raise ExtraccionInvalida("Un medicamento llegó sin nombre de fármaco.")
        items.append(ItemReceta(**campos))

    generales = _texto(datos.get("indicaciones_generales"), "indicaciones_generales")
    return items, generales
