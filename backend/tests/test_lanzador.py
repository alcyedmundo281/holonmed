"""El lanzador local se detiene y explica antes de levantar nada.

Sin red externa y sin arrancar procesos.
"""

import socket

import pytest

from holonmed import lanzador
from holonmed.config import Settings


def test_configuracion_de_ollama_se_sustituye_entera():
    entorno: dict[str, str] = {}
    settings = Settings(model_clinical="holonmed-clinico:latest", _env_file=None)
    assert lanzador.usar_lm_studio(settings, entorno) is True
    assert entorno == lanzador.LM_STUDIO


def test_configuracion_openai_del_usuario_se_respeta():
    entorno: dict[str, str] = {}
    settings = Settings(llm_backend="openai", model_clinical="otro", _env_file=None)
    assert lanzador.usar_lm_studio(settings, entorno) is False
    assert entorno == {}


def test_un_puerto_con_alguien_escuchando_esta_ocupado():
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        servidor.listen()
        puerto = servidor.getsockname()[1]
        assert lanzador.puerto_ocupado(puerto) is True
        with pytest.raises(lanzador.Falta, match=str(puerto)):
            lanzador.comprobar_puertos({"frontend": puerto})
    assert lanzador.puerto_ocupado(puerto) is False


def test_sin_node_modules_se_detiene(monkeypatch, tmp_path):
    monkeypatch.setattr(lanzador.shutil, "which", lambda _: "node")
    monkeypatch.setattr(lanzador, "VITE", tmp_path / "no-existe.js")
    with pytest.raises(lanzador.Falta, match="npm ci"):
        lanzador.comprobar_frontend()


def test_sin_node_se_detiene(monkeypatch):
    monkeypatch.setattr(lanzador.shutil, "which", lambda _: None)
    with pytest.raises(lanzador.Falta, match="Node"):
        lanzador.comprobar_frontend()


@pytest.mark.parametrize(
    ("inventario", "explicacion"),
    [
        ((False, None), "lms server start"),
        ((True, None), "lista de modelos legible"),
        ((True, ["otro"]), "lms load medgemma"),
    ],
)
async def test_sin_modelo_utilizable_se_detiene(monkeypatch, inventario, explicacion):
    async def falso(self):
        return inventario

    monkeypatch.setattr(lanzador.OllamaClient, "inventario", falso)
    settings = Settings(
        llm_backend="openai",
        model_clinical="medgemma",
        model_router="medgemma",
        _env_file=None,
    )
    with pytest.raises(lanzador.Falta, match=explicacion):
        await lanzador.comprobar_modelo(settings)
