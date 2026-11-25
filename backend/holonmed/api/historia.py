"""La historia contra la que se calcula un tic, y cómo saber si cambió."""

import hashlib

from ..models import HolonPaciente
from .deps import AppContext


def cargar_holon(ctx: AppContext, holon: HolonPaciente) -> HolonPaciente:
    """Añade al holón la línea de tiempo y el Φ previo que lee el pipeline."""
    holon.linea_tiempo = ctx.tics.linea_tiempo(holon.paciente_id)
    holon.phi_previo = ctx.tics.phi_por_hipotesis(holon.paciente_id)
    return holon


def huella(holon: HolonPaciente) -> str:
    return hashlib.sha256(holon.model_dump_json().encode()).hexdigest()
