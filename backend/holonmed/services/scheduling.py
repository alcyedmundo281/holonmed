"""Agenda de citas. Las fechas se leen con la gramática de `core/cita.py`."""

from datetime import datetime, timezone
from typing import Any

from ..core.cita import interpretar_fecha
from ..db import CitaRepo


class SchedulingService:
    def __init__(self, repo: CitaRepo):
        self.repo = repo

    def agendar(self, paciente_id: str, fecha_texto: str, motivo: str) -> dict[str, Any]:
        """Escribe la cita que dice `fecha_texto`.

        Lanza `PeticionInvalida`, sin escribir, si el texto no dice día y
        hora o si la fecha ya pasó.
        """
        fecha = interpretar_fecha(fecha_texto, datetime.now())
        registro = {
            "paciente_id": paciente_id,
            "fecha": fecha.isoformat(),
            "fecha_interpretada": True,
            "motivo": motivo,
            "estado": "agendada",
            "creada": datetime.now(timezone.utc).isoformat(),
        }
        cita_id = self.repo.crear(registro)
        return {
            "estado": "agendada" if cita_id else "no_persistida",
            "id": cita_id,
            "fecha": registro["fecha"],
            "legible": fecha.strftime("%A %d/%m/%Y %H:%M"),
            "motivo": motivo,
        }

    def registrar(
        self, paciente_id: str, fecha: datetime, motivo: str, confirmada_por: str
    ) -> str | None:
        """Escribe una cita ya aprobada, con la fecha que se enseñó.

        No interpreta nada: reinterpretar «mañana» al confirmar podría dar
        otro día que el aprobado.
        """
        return self.repo.crear(
            {
                "paciente_id": paciente_id,
                "fecha": fecha.isoformat(),
                "fecha_interpretada": True,
                "motivo": motivo,
                "estado": "agendada",
                "confirmada_por": confirmada_por,
            }
        )

    def listar(self, paciente_id: str | None = None):
        return self.repo.listar(paciente_id)
