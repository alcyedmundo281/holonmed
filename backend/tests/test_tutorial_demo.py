"""El tutorial sólo existe en modo demo, y no abre un segundo camino al modelo."""

import os
import re
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from holonmed import lanzador
from holonmed.api.app import crear_app
from holonmed.api.routes.tutorial import PAGINA
from holonmed.config import Settings
from holonmed.core.entrada_no_confiable import detectar_instrucciones
from holonmed.core.nota_soap import declarar_procedencia
from scripts import demo


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


def test_demo_react_comparte_modelo_y_aisla_la_base(monkeypatch, tmp_path):
    base_trabajo = tmp_path / "trabajo.db"
    bases = []

    def arrancar(opciones):
        assert opciones == [
            "--puerto-backend",
            "9876",
            "--puerto-frontend",
            "5174",
            "--sin-navegador",
        ]
        settings = Settings(_env_file=None)
        assert not settings.modo_demo
        assert settings.llm_backend == "openai"
        assert settings.llm_host == "http://127.0.0.1:1234"
        assert settings.model_clinical == settings.model_router == "gemma-4-de-prueba"
        assert settings.db_path != base_trabajo
        assert settings.db_path.parent.is_dir()
        assert settings.docs_dir.parent == settings.db_path.parent
        assert os.environ["VITE_API_URL"] == ""
        bases.append(settings.db_path)
        return 0

    monkeypatch.setattr(lanzador, "main", arrancar)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "demo.py",
            "--react",
            "--temporal",
            "--puerto",
            "9876",
            "--puerto-frontend",
            "5174",
            "--modelo",
            "gemma-4-de-prueba",
        ],
    )
    with patch.dict(
        os.environ,
        {"HOLONMED_DB_PATH": str(base_trabajo), "VITE_API_URL": "http://127.0.0.1:8000"},
    ):
        assert demo.main() == 0

    assert len(bases) == 1
    assert not bases[0].parent.exists()
    assert not base_trabajo.exists()


def test_demo_react_reabre_el_mismo_almacenamiento(monkeypatch, tmp_path):
    datos = tmp_path / "datos-demo"

    def arrancar(_opciones):
        settings = Settings(_env_file=None)
        assert settings.db_path == datos / "demo.db"
        if settings.db_path.exists():
            assert settings.db_path.read_bytes() == b"registro de prueba"
        else:
            settings.db_path.write_bytes(b"registro de prueba")
        return 0

    monkeypatch.setattr(demo, "directorio_react", lambda: datos)
    monkeypatch.setattr(lanzador, "main", arrancar)
    monkeypatch.setattr(sys, "argv", ["demo.py", "--react"])
    with patch.dict(os.environ):
        assert demo.main() == demo.main() == 0
    assert (datos / "demo.db").exists()


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


def test_una_medida_ausente_no_se_pinta_como_cero():
    """`CandidataAbductiva.clave` puede ser None (vetada o sin medir) y
    `Number(null)` es 0: la tabla presentaba como medido lo que no se midió."""
    pagina = PAGINA.read_text(encoding="utf-8")
    assert "Number(c.clave)" not in pagina
    assert "medida(c.clave)" in pagina
    assert '"sin medida"' in pagina


def test_solo_el_caso_trampa_del_guion_dispara_el_detector_y_la_pagina_lo_dice():
    """Si el detector marcara un caso normal, el paso entero quedaría retenido
    delante del público; y si la página no leyera la señal, daría otra causa."""
    pagina = PAGINA.read_text(encoding="utf-8")
    bloque = pagina[pagina.index("const CASOS = {") : pagina.index("const PASOS")]
    casos = dict(
        re.findall(r'(\w+): \{\s*protocolo: "[^"]+",\s*texto: "([^"]+)"', bloque)
    )
    assert len(casos) == 4
    for nombre, texto in casos.items():
        assert bool(detectar_instrucciones(texto)) is (nombre == "trampa"), nombre
    assert "instrucciones_detectadas" in pagina


def _casos() -> dict[str, str]:
    pagina = PAGINA.read_text(encoding="utf-8")
    bloque = pagina[pagina.index("const CASOS = {") : pagina.index("const PASOS")]
    crudos = re.findall(r'(\w+): \{\s*protocolo: "[^"]+",\s*texto: "([^"]+)"', bloque)
    return {nombre: texto.replace("\\n", "\n") for nombre, texto in crudos}


def test_la_respuesta_se_ve_como_lista_de_problemas_y_nota():
    pagina = PAGINA.read_text(encoding="utf-8")
    assert "Lista de problemas" in pagina
    assert 'el("pre", {}, nota.texto)' in pagina
    # En las dos salidas con hallazgos, también cuando el tic queda retenido.
    assert pagina.count("pintarNota(dato.evolucion);") == 2


@pytest.mark.parametrize(
    ("caso", "referido", "comprobado"),
    [
        ("completo", "náuseas y vómitos", "Lipasa 900 U/L"),
        ("negativas", "No ha vomitado", "Lipasa 40 U/L"),
        ("calcio", "Dolor epigástrico desde ayer", "Calcio total 7.8 mg/dL"),
    ],
)
def test_los_casos_del_guion_declaran_s_y_o(caso, referido, comprobado):
    """Sin las marcas, la nota del recorrido saldría entera «sin clasificar»."""
    texto = _casos()[caso]

    assert declarar_procedencia(texto, referido) == "subjetivo"
    assert declarar_procedencia(texto, comprobado) == "objetivo"
