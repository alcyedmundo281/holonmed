"""El símbolo de conexión no puede ponerse verde sin haberlo comprobado.

Sin red: el servidor de modelos se sustituye por un transporte falso, tanto
en la función pura como en `GET /health`.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from holonmed.api.app import crear_app
from holonmed.config import Settings
from holonmed.core.estado_llm import diagnosticar_modelo


@pytest.mark.parametrize(
    ("responde", "modelos", "estado", "faltantes"),
    [
        (False, None, "sin_conexion", []),
        # Aunque llegara una lista, sin respuesta no hay verde.
        (False, ["medgemma"], "sin_conexion", []),
        (True, None, "sin_comprobar", []),
        (True, [], "falta_modelo", ["medgemma"]),
        (True, ["otro"], "falta_modelo", ["medgemma"]),
        (True, ["medgemma", "otro"], "conectado", []),
        # En un servidor compatible con OpenAI el identificador es exacto.
        (True, ["medgemma:2"], "falta_modelo", ["medgemma"]),
    ],
)
def test_diagnostico_openai(responde, modelos, estado, faltantes):
    d = diagnosticar_modelo(
        responde=responde,
        modelos=modelos,
        requeridos=["medgemma", "medgemma"],
        backend="openai",
    )
    assert (d.estado, d.faltantes) == (estado, faltantes)


@pytest.mark.parametrize(
    ("requerido", "instalado", "estado"),
    [
        ("llama3", "llama3:latest", "conectado"),
        ("llama3:latest", "llama3", "conectado"),
        ("gemma2:9b", "gemma2:9b", "conectado"),
        ("gemma2:9b", "gemma2:2b", "falta_modelo"),
        ("llama3", "llama3:70b", "falta_modelo"),
        ("hf.co:443/org/modelo", "hf.co:443/org/modelo:latest", "conectado"),
    ],
)
def test_diagnostico_ollama_respeta_la_etiqueta(requerido, instalado, estado):
    d = diagnosticar_modelo(
        responde=True, modelos=[instalado], requeridos=[requerido], backend="ollama"
    )
    assert d.estado == estado


def _caido(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("sin conexión")


def _fijo(codigo: int = 200, **cuerpo):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(codigo, **cuerpo)

    return handler


@pytest.mark.parametrize(
    ("handler", "estado", "disponible"),
    [
        (_caido, "sin_conexion", False),
        (_fijo(500), "sin_conexion", False),
        # Otro programa en el puerto: contesta 200 pero no es un inventario.
        (_fijo(text="<html></html>"), "sin_comprobar", True),
        (_fijo(json=[]), "sin_comprobar", True),
        (_fijo(json={}), "sin_comprobar", True),
        (_fijo(json={"data": None}), "sin_comprobar", True),
        (_fijo(json={"data": {}}), "sin_comprobar", True),
        (_fijo(json={"data": [{"nombre": "medgemma"}]}), "sin_comprobar", True),
        (_fijo(json={"data": [{"id": 7}]}), "sin_comprobar", True),
        (_fijo(json={"data": []}), "falta_modelo", True),
        (_fijo(json={"data": [{"id": "medgemma"}]}), "conectado", True),
    ],
)
def test_health_publica_el_estado_del_modelo(tmp_path, handler, estado, disponible):
    settings = Settings(
        llm_backend="openai",
        model_clinical="medgemma",
        model_router="medgemma",
        db_path=tmp_path / "salud.db",
        _env_file=None,
    )
    with TestClient(crear_app(settings)) as cliente:
        llm = cliente.app.state.context.llm
        llm._client = httpx.AsyncClient(
            base_url=settings.llm_host, transport=httpx.MockTransport(handler)
        )
        salud = cliente.get("/health").json()

    assert salud["llm"]["estado"] == estado
    assert salud["llm"]["disponible"] is disponible
    assert salud["llm"]["backend"] == "openai"
    if estado != "conectado":
        assert salud["operativo"] is False
    else:
        assert salud["operativo"] is salud["vocabulario"]["disponible"]
