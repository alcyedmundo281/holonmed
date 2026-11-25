"""Recetas propuestas que esperan una confirmación nombrada.

Viven sólo en memoria a propósito: una propuesta no es parte del registro
clínico. Si el proceso se reinicia se pierden y hay que pedirlas otra vez.

Que las guarde el servidor y no el cliente es lo que garantiza que sólo se
puede confirmar lo que pasó por el detector y por la validación de forma, y
que se escribe exactamente lo que se enseñó.
"""

from ..models import PropuestaReceta

# Tope de memoria, no parámetro clínico: al superarlo sale la más antigua.
MAX_PENDIENTES = 100


class PropuestasReceta:
    def __init__(self) -> None:
        self._pendientes: dict[str, PropuestaReceta] = {}

    def guardar(self, propuesta: PropuestaReceta) -> None:
        self._pendientes[propuesta.propuesta_id] = propuesta
        while len(self._pendientes) > MAX_PENDIENTES:
            del self._pendientes[next(iter(self._pendientes))]

    def ver(self, propuesta_id: str) -> PropuestaReceta | None:
        return self._pendientes.get(propuesta_id)

    def retirar(self, propuesta_id: str) -> None:
        self._pendientes.pop(propuesta_id, None)
