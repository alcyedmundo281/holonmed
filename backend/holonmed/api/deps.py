"""Contenedor de dependencias de la aplicación.

Los componentes se construyen una sola vez al arrancar y se comparten. Las
rutas los reciben por inyección, lo que permite sustituirlos por dobles en
los tests.
"""

import logging

from fastapi import Request

from ..config import Settings, get_settings
from ..core import (
    AntigenPresentingCell,
    ClinicalVerifier,
    CrystallizationPipeline,
    OntologyValidator,
    SkillManager,
    TerminologyIndex,
    VocabularyLoader,
)
from ..db import (
    CitaRepo,
    Database,
    DocumentoRepo,
    GraphRepo,
    PacienteRepo,
    TicRepo,
)
from ..llm import OllamaClient
from ..services import PrescriptionService, SchedulingService

logger = logging.getLogger(__name__)


class AppContext:
    """Todo el estado vivo de la aplicación, en un solo sitio."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

        self.llm = OllamaClient(self.settings)
        self.database = Database(self.settings.db_path)

        self.grafo = GraphRepo(self.database)
        self.pacientes = PacienteRepo(self.database)
        self.tics = TicRepo(self.database, self.grafo)
        self.citas = CitaRepo(self.database)
        self.documentos = DocumentoRepo(self.database)

        self.terminologia = TerminologyIndex(self.database, self.grafo)
        self._preparar_vocabulario()

        self.skills = SkillManager(self.settings)
        self.validador = OntologyValidator(self.terminologia, self.llm, self.settings)
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

    def _preparar_vocabulario(self) -> None:
        """Carga el vocabulario semilla si la base está vacía.

        Que el sistema sea utilizable recién clonado, sin descargas ni
        licencias, es un requisito y no una comodidad: sin vocabulario el
        validador no puede rechazar nada, y un validador que lo acepta todo
        es peor que no tener validador.
        """
        if not self.settings.autocargar_semilla:
            return
        if self.terminologia.disponible():
            return
        try:
            cargador = VocabularyLoader(self.database)
            n = cargador.cargar_semilla(self.settings.vocabulario_semilla)
            if n:
                logger.info("Vocabulario semilla cargado: %d conceptos", n)
        except Exception:  # noqa: BLE001 — sin vocabulario se arranca igual
            logger.exception("No se pudo cargar el vocabulario semilla")

    async def cerrar(self) -> None:
        await self.llm.close()
        self.database.cerrar()

    def estado(self) -> dict:
        return {
            "base_datos": {
                "conectada": self.database.disponible,
                "ruta": str(self.database.ruta),
                "error": self.database.error,
                "estadisticas": self.database.estadisticas(),
            },
            "vocabulario": {
                "disponible": self.terminologia.disponible(),
                "sistemas": self.terminologia.sistemas_cargados(),
            },
            "skills": self.skills.listar(),
        }


def get_context(request: Request) -> AppContext:
    return request.app.state.context
