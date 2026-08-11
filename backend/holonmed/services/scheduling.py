"""Agenda de citas con interpretación de fechas en lenguaje natural."""

import logging
from datetime import datetime, timezone
from typing import Any

from ..db import CitaRepo

logger = logging.getLogger(__name__)


class SchedulingService:
    def __init__(self, repo: CitaRepo):
        self.repo = repo

    def agendar(self, paciente_id: str, fecha_texto: str, motivo: str) -> dict[str, Any]:
        fecha = self._interpretar(fecha_texto)
        registro = {
            "paciente_id": paciente_id,
            "fecha": fecha.isoformat() if fecha else fecha_texto,
            "fecha_interpretada": fecha is not None,
            "motivo": motivo,
            "estado": "agendada",
            "creada": datetime.now(timezone.utc).isoformat(),
        }
        cita_id = self.repo.crear(registro)
        return {
            "estado": "agendada" if cita_id else "no_persistida",
            "id": cita_id,
            "fecha": registro["fecha"],
            "legible": fecha.strftime("%A %d/%m/%Y %H:%M") if fecha else fecha_texto,
            "motivo": motivo,
        }

    @staticmethod
    def _interpretar(texto: str) -> datetime | None:
        """"el próximo martes" -> datetime. Devuelve None si no se entiende."""
        try:
            import dateparser
        except ImportError:
            logger.debug("dateparser no instalado; se guarda la fecha en crudo")
            return None
        return dateparser.parse(
            texto,
            languages=["es"],
            settings={"PREFER_DATES_FROM": "future", "DATE_ORDER": "DMY"},
        )

    def listar(self, paciente_id: str | None = None):
        return self.repo.listar(paciente_id)
