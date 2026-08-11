"""Cliente único de LLM.

Los dos proyectos originales hablaban con Ollama de dos formas distintas
(la librería `ollama` síncrona y llamadas `httpx` crudas a `/api/generate`).
Aquí hay una sola puerta: async, con timeouts explícitos, parseo defensivo
de JSON y temperatura fijada por configuración.

Todo el procesamiento ocurre en local. Ninguna narrativa clínica sale de
la máquina.
"""

import json
import logging
import re
from typing import Any

import httpx

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """Ollama no responde. El pipeline debe degradar, no inventar."""


def extraer_json(texto: str) -> dict[str, Any]:
    """Rescata un objeto JSON de una respuesta de LLM sucia.

    Los modelos locales envuelven el JSON en vallas markdown, lo preceden
    de charla o lo cierran mal. Se intenta, en orden: parseo directo,
    extracción de la valla, y recorte entre la primera `{` y la última `}`.
    Si nada funciona devuelve `{}` — nunca una suposición.
    """
    if not texto:
        return {}

    try:
        parsed = json.loads(texto)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        pass

    fenced = re.search(r"```(?:json)?\s*(.*?)```", texto, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1).strip())
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

    start, end = texto.find("{"), texto.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(texto[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

    logger.warning("No se pudo extraer JSON de la respuesta del LLM")
    return {}


class OllamaClient:
    """Envoltorio async sobre la API de Ollama."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OllamaClient":
        self._client = httpx.AsyncClient(base_url=self.settings.ollama_host)
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.settings.ollama_host)
        return self._client

    async def disponible(self) -> bool:
        """¿Está Ollama arriba? Se usa en el healthcheck, no en el pipeline."""
        try:
            res = await self._ensure_client().get("/api/tags", timeout=5.0)
            return res.status_code == 200
        except httpx.HTTPError:
            return False

    async def modelos_disponibles(self) -> list[str]:
        try:
            res = await self._ensure_client().get("/api/tags", timeout=5.0)
            res.raise_for_status()
            return [m["name"] for m in res.json().get("models", [])]
        except (httpx.HTTPError, KeyError, ValueError):
            return []

    async def generar(
        self,
        prompt: str,
        *,
        model: str | None = None,
        formato_json: bool = False,
        timeout: float | None = None,
        num_ctx: int = 4096,
        temperature: float | None = None,
    ) -> str:
        """Completado de texto plano. Devuelve la respuesta cruda."""
        payload: dict[str, Any] = {
            "model": model or self.settings.model_clinical,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": (
                    temperature
                    if temperature is not None
                    else self.settings.temperature
                ),
                "num_ctx": num_ctx,
            },
        }
        if formato_json:
            payload["format"] = "json"

        try:
            res = await self._ensure_client().post(
                "/api/generate",
                json=payload,
                timeout=timeout or self.settings.llm_timeout_slow,
            )
            res.raise_for_status()
            return res.json().get("response", "")
        except httpx.HTTPError as exc:
            raise LLMUnavailable(
                f"Ollama no respondió en {self.settings.ollama_host}: {exc}"
            ) from exc

    async def generar_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        timeout: float | None = None,
        num_ctx: int = 4096,
    ) -> dict[str, Any]:
        """Completado forzado a JSON, ya parseado y saneado."""
        raw = await self.generar(
            prompt,
            model=model,
            formato_json=True,
            timeout=timeout,
            num_ctx=num_ctx,
        )
        return extraer_json(raw)

    async def elegir_opcion(
        self,
        prompt: str,
        *,
        opciones_validas: list[str],
        defecto: str,
        model: str | None = None,
    ) -> str:
        """Clasificación de opción cerrada, con red de seguridad.

        Si el modelo divaga, alucina una opción inexistente o Ollama está
        caído, se devuelve `defecto`. Un clasificador nunca debe abrir la
        puerta a valores fuera del conjunto.
        """
        try:
            raw = (
                await self.generar(
                    prompt,
                    model=model or self.settings.model_router,
                    timeout=self.settings.llm_timeout_fast,
                    temperature=0.1,
                )
            ).strip().lower()
        except LLMUnavailable as exc:
            logger.warning("Clasificación degradada a '%s': %s", defecto, exc)
            return defecto

        for opcion in opciones_validas:
            if opcion.lower() in raw:
                return opcion

        logger.info("Respuesta '%s' fuera del conjunto; usando '%s'", raw[:60], defecto)
        return defecto
