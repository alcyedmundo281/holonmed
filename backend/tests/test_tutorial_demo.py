"""El tutorial sólo existe en modo demo, y no abre un segundo camino al modelo."""

from fastapi.testclient import TestClient

from holonmed.api.app import crear_app
from holonmed.api.routes.tutorial import PAGINA
from holonmed.config import Settings


def _cliente(modo_demo: bool) -> TestClient:
    # Sin `with`: no corre el ciclo de vida y no se crea ninguna base.
    return TestClient(crear_app(Settings(modo_demo=modo_demo)))


def test_el_tutorial_no_se_sirve_fuera_del_modo_demo():
    assert Settings.model_fields["modo_demo"].default is False
    assert _cliente(False).get("/tutorial").status_code == 404
    assert _cliente(False).get("/", follow_redirects=False).status_code == 404


def test_en_modo_demo_se_sirve_con_el_aviso_de_alcance():
    respuesta = _cliente(True).get("/tutorial")
    assert respuesta.status_code == 200
    assert "No es un dispositivo médico" in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"


def test_en_modo_demo_la_raiz_lleva_al_tutorial():
    """`http://localhost:8765` a secas tiene que abrir la página."""
    respuesta = _cliente(True).get("/", follow_redirects=False)
    assert respuesta.headers["location"] == "/tutorial"


def test_la_pagina_no_habla_con_el_modelo_ni_usa_el_chat_con_acciones():
    """Una sola puerta al modelo. Y `/api/chat` queda fuera: su router puede crear
    pacientes y recetas desde texto libre, y devuelve la respuesta cruda."""
    pagina = PAGINA.read_text(encoding="utf-8")
    for prohibido in ("1234", "/v1/chat", "/api/generate", "/api/chat"):
        assert prohibido not in pagina


def test_la_pagina_no_interpreta_como_html_lo_que_escribe_el_modelo():
    pagina = PAGINA.read_text(encoding="utf-8")
    for prohibido in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert prohibido not in pagina
    # El resumen libre del modelo no se muestra.
    assert ".resumen" not in pagina


def test_la_pagina_no_pide_nada_fuera_de_la_maquina():
    pagina = PAGINA.read_text(encoding="utf-8")
    assert "http://" not in pagina and "https://" not in pagina
