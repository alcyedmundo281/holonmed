"""Configuración central de HolonMed.

Todo valor ajustable vive aquí y se lee del entorno (o de `.env`). Ningún
módulo debe leer `os.environ` por su cuenta: así hay un único sitio donde
auditar qué configura el sistema, algo que importa cuando los umbrales
que ajustas son de seguridad clínica.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # --- ArangoDB ----------------------------------------------------
    arango_url: str = "http://localhost:8529"
    arango_db: str = "holonmed"
    arango_user: str = "root"
    arango_password: str = "changeme"

    # --- SNOMED ------------------------------------------------------
    snomed_backend: str = "auto"  # local | arango | auto
    snomed_dir: Path = Path("./data/snomed")
    snomed_descriptions: str = (
        "sct2_Description_SpanishExtensionSnapshot-es_INT_20251110.txt"
    )
    snomed_map: str | None = (
        "der2_iisssccRefset_ExtendedMapSpanishExtensionSnapshot_INT_20251110.txt"
    )
    snomed_relationships: str | None = (
        "sct2_Relationship_SpanishExtensionSnapshot_INT_20251110.txt"
    )

    # --- Umbrales del validador (seguridad clínica) ------------------
    # Cambiarlos altera qué hallazgos el sistema considera fiables.
    threshold_validated: float = 85.0
    threshold_alert: float = 75.0
    threshold_audit: float = 60.0
    # Similitud mínima para aceptar un skill-hint difuso sin pasar por el LLM.
    threshold_hint_fuzzy: float = 92.0
    # Similitud mínima del fallback puramente matemático (sin juicio del LLM).
    threshold_fuzzy_fallback: float = 92.0

    # --- API ---------------------------------------------------------
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Rutas -------------------------------------------------------
    skills_dir: Path = Path("./skills")
    docs_dir: Path = Path("./generated_docs")

    # --- Integraciones opcionales ------------------------------------
    gdrive_enabled: bool = False
    gdrive_credentials_path: Path | None = None
    gdrive_folder_id: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def snomed_description_path(self) -> Path:
        return self.snomed_dir / self.snomed_descriptions

    @property
    def snomed_map_path(self) -> Path | None:
        return self.snomed_dir / self.snomed_map if self.snomed_map else None

    @property
    def snomed_relationship_path(self) -> Path | None:
        return (
            self.snomed_dir / self.snomed_relationships
            if self.snomed_relationships
            else None
        )

    @property
    def snomed_cache_path(self) -> Path:
        return self.snomed_dir / "snomed_cache.pkl"

    def resolve_snomed_backend(self) -> str:
        """Decide el backend real cuando la configuración dice 'auto'."""
        if self.snomed_backend != "auto":
            return self.snomed_backend
        if self.snomed_cache_path.exists() or self.snomed_description_path.exists():
            return "local"
        return "arango"


@lru_cache
def get_settings() -> Settings:
    return Settings()
