"""Configuración central de HolonMed.

Todo valor ajustable vive aquí y se lee del entorno (o de `.env`). Ningún
módulo debe leer `os.environ` por su cuenta: así hay un único sitio donde
auditar qué configura el sistema, algo que importa cuando los umbrales que
ajustas son de seguridad clínica.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HOLONMED_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---------------------------------------------------------
    ollama_host: str = "http://127.0.0.1:11434"
    model_clinical: str = "gemma2:9b"
    model_router: str = "llama3"
    temperature: float = 0.0
    llm_timeout_fast: float = 30.0
    llm_timeout_slow: float = 120.0

    # --- Almacenamiento ----------------------------------------------
    # SQLite embebido: un único archivo, sin servidor. Ciframos el disco,
    # no el motor.
    db_path: Path = RAIZ / "data" / "holonmed.db"

    # --- Vocabulario --------------------------------------------------
    # El semilla es contenido propio y se carga solo. Cualquier otra
    # terminología se importa con scripts/importar_terminologia.py.
    vocabulario_semilla: Path = RAIZ / "data" / "vocabulario_semilla.json"
    autocargar_semilla: bool = True

    # --- Presentación del protocolo al modelo ------------------------
    # Cómo se le renderiza al modelo el conocimiento estructurado:
    #   minimo    — sólo la prosa. El modelo NO ve los cortes y los inventa.
    #   prosa     — los cortes redactados como texto corrido.
    #   etiquetas — los cortes delimitados en atributos.
    #
    # Medido sobre 3 ejecuciones (docs/VALIDACION.md): 'minimo' inventó el
    # corte en 9 de 15 auditorías; 'prosa' y 'etiquetas' acertaron las 12,
    # sin ninguna invención. Entre esas dos no hubo diferencia medible, así
    # que gana 'prosa' por gastar menos contexto y suprimir menos la
    # extracción.
    formato_protocolo: str = "prosa"

    # --- Umbrales del validador (seguridad clínica) ------------------
    threshold_validated: float = 85.0
    threshold_alert: float = 75.0
    threshold_audit: float = 60.0
    threshold_hint_fuzzy: float = 92.0
    threshold_fuzzy_fallback: float = 92.0

    # --- API ---------------------------------------------------------
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Rutas -------------------------------------------------------
    skills_dir: Path = RAIZ / "skills"
    docs_dir: Path = RAIZ / "generated_docs"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
