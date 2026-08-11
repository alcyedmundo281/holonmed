"""Contenedor de dependencias de la aplicación.

Los componentes caros (el índice SNOMED puede ocupar cientos de MB) se
construyen una sola vez al arrancar y se comparten. Las rutas los reciben
por inyección, lo que permite sustituirlos por dobles en los tests.
"""

import logging

from fastapi import Request

from ..config import Settings, get_settings
from ..core import (
    AntigenPresentingCell,
    ClinicalVerifier,
    CrystallizationPipeline,
    SkillManager,
    SnomedValidator,
    construir_index,
)
from ..db import CitaRepo, Database, PacienteRepo, TicRepo
from ..llm import OllamaClient
from ..services import PrescriptionService, SchedulingService

logger = logging.getLogger(__name__)


class AppContext:
    """Todo el estado vivo de la aplicación, en un solo sitio."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

        self.llm = OllamaClient(self.settings)
        self.database = Database(self.settings)
        self.database.conectar()

        self.pacientes = PacienteRepo(self.database)
        self.tics = TicRepo(self.database)
        self.citas = CitaRepo(self.database)

        self.skills = SkillManager(self.settings)
        self.snomed_index = construir_index(self.settings, self.database.db)
        self.validador = SnomedValidator(self.snomed_index, self.llm, self.settings)
        self.verificador = ClinicalVerifier(self.llm, self.settings)

        self.pipeline = CrystallizationPipeline(
            llm=self.llm,
            skills=self.skills,
            validador=self.validador,
            verificador=self.verificador,
            bayes=AntigenPresentingCell(),
            settings=self.settings,
        )

        self.recetas = PrescriptionService(self.settings)
        self.agenda = SchedulingService(self.citas)

    async def cerrar(self) -> None:
        await self.llm.close()

    def estado(self) -> dict:
        return {
            "base_datos": {
                "conectada": self.database.disponible,
                "error": self.database.error,
            },
            "snomed": {
                "backend": type(self.snomed_index).__name__,
                "disponible": self.snomed_index.disponible(),
            },
            "skills": self.skills.listar(),
        }


def get_context(request: Request) -> AppContext:
    return request.app.state.context
