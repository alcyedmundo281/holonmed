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

    # --- Quién elige la hipótesis ------------------------------------
    # True: la elige la competencia abductiva sobre el grafo del paciente.
    # False: la elige el prompt de triaje y la competencia sólo mide, que
    # es como corría hasta el ciclo 7.
    #
    # El interruptor existe porque el diseño pone una precondición que hoy
    # NO está satisfecha: «antes de sustituir el prompt por esa regla hay
    # que saber cuánto se equivoca». Esa cifra la produce
    # `TicRepo.acuerdo_del_triaje()` sobre el histórico, y hasta que haya
    # histórico suficiente no hay con qué decidir. Un centro que prefiera
    # medir primero pone esto en False y no pierde la medición: el triaje
    # y la competencia siguen corriendo los dos, y `triaje_coincide` se
    # sigue registrando en cualquiera de los dos modos.
    abduccion_decide: bool = True

    # --- Facturación --------------------------------------------------
    # Qué catálogo de precios se usa. Cada hospital o aseguradora carga el
    # suyo con scripts/importar_tarifario.py; 'demo' trae importes
    # inventados para que el circuito funcione recién clonado.
    sistema_tarifario: str = "demo"
    tarifario_demo: Path = RAIZ / "data" / "tarifario_demo.json"
    autocargar_tarifario: bool = True

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
