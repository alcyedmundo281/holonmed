"""Tests de `holonmed consultar`: fallo cerrado cuando el modelo no está."""

import httpx
import pytest

from holonmed import cli
from holonmed.llm import client as cliente_mod


def _servidor(modelos: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": m} for m in modelos]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    return handler


@pytest.fixture
def con_servidor(monkeypatch):
    monkeypatch.setenv("HOLONMED_LLM_BACKEND", "openai")
    monkeypatch.setenv("HOLONMED_MODEL_CLINICAL", "medgemma")
    cli.get_settings.cache_clear()
    original = httpx.AsyncClient

    def instalar(modelos):
        monkeypatch.setattr(
            cliente_mod.httpx,
            "AsyncClient",
            lambda **kw: original(
                transport=httpx.MockTransport(_servidor(modelos)), **kw
            ),
        )

    yield instalar
    cli.get_settings.cache_clear()


async def test_responde_si_el_modelo_esta_cargado(con_servidor, capsys):
    con_servidor(["medgemma"])
    assert await cli._consultar("hola", None) == 0
    assert "ok" in capsys.readouterr().out


async def test_se_detiene_si_el_modelo_no_esta_cargado(con_servidor, capsys):
    con_servidor(["otro"])
    assert await cli._consultar("hola", None) == 1
    assert "no está cargado" in capsys.readouterr().err


async def test_se_detiene_si_el_servidor_no_responde(con_servidor, capsys):
    con_servidor([])
    assert await cli._consultar("hola", None) == 1
    assert "Sin respuesta" in capsys.readouterr().err
