"""Recetas propuestas que esperan una confirmación nombrada."""

from ..models import PropuestaReceta
from .propuestas import MAX_PENDIENTES, Propuestas

__all__ = ["MAX_PENDIENTES", "PropuestasReceta"]


class PropuestasReceta(Propuestas[PropuestaReceta]):
    pass
