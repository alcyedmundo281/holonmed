"""Fábrica de la aplicación FastAPI."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..config import Settings, get_settings
from .deps import AppContext
from .routes import chat, clinical, documents, graph, patients

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

DESCRIPCION = """
Sistema de apoyo a la decisión clínica con validación ontológica.

Convierte narrativa clínica libre en **infones**: hallazgos atómicos
normalizados contra un vocabulario controlado y auditados en tres capas
antes de entrar en la historia del paciente.

Todo el procesamiento ocurre en local: Ollama para el razonamiento y
SQLite embebido para los datos. Ninguna narrativa clínica sale de la
máquina.

**No es un dispositivo médico.** Ninguna salida sustituye el juicio de un
profesional sanitario.
"""


def crear_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Inicializando HolonMed…")
        app.state.context = AppContext(settings)
        estado = app.state.context.estado()
        logger.info("Base de datos: %s", estado["base_datos"])
        logger.info("Vocabulario: %s", estado["vocabulario"])
        logger.info("Skills: %s", ", ".join(estado["skills"]) or "ninguna")
        yield
        await app.state.context.cerrar()
        logger.info("HolonMed detenido")

    app = FastAPI(
        title="HolonMed",
        description=DESCRIPCION,
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(clinical.router)
    app.include_router(chat.router)
    app.include_router(patients.router)
    app.include_router(documents.router)
    app.include_router(graph.router)

    @app.get("/health", tags=["sistema"])
    async def health():
        ctx: AppContext = app.state.context
        estado = ctx.estado()
        modelos = await ctx.llm.modelos_disponibles()
        # Que Ollama responda no basta: recién instalado no tiene ningún
        # modelo, y decir "operativo" en ese estado manda al usuario a
        # depurar el sitio equivocado cuando la primera consulta falle.
        instalados = {m.split(":")[0] for m in modelos}
        requeridos = {settings.model_clinical, settings.model_router}
        faltantes = sorted(m for m in requeridos if m.split(":")[0] not in instalados)

        estado["llm"] = {
            "host": settings.ollama_host,
            "disponible": await ctx.llm.disponible(),
            "modelos": modelos,
            "faltantes": faltantes,
            "configurados": {
                "clinico": settings.model_clinical,
                "router": settings.model_router,
            },
        }
        # El sistema es utilizable si puede razonar y validar. La base va
        # embebida, así que un fallo suyo es de disco, no de un servicio
        # ausente, y por eso no entra en este cálculo.
        estado["operativo"] = (
            estado["llm"]["disponible"]
            and not faltantes
            and estado["vocabulario"]["disponible"]
        )
        return estado

    return app


app = crear_app()
