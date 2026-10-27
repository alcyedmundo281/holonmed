"""Tests del backend compatible con OpenAI (llama.cpp, LM Studio).

Sin red: se sustituye el transporte HTTP. Lo que se comprueba es el contrato
de la puerta única: misma interfaz que con Ollama, y ante un servidor caído o
una respuesta mal formada, `LLMUnavailable` o `{}` — nunca una suposición.
"""

import json

import httpx
import pytest

from holonmed.config import Settings
from holonmed.llm.client import LLMUnavailable, OllamaClient


def _cliente(handler, **ajustes) -> OllamaClient:
    settings = Settings(llm_backend="openai", _env_file=None, **ajustes)
    cliente = OllamaClient(settings)
    cliente._client = httpx.AsyncClient(
        base_url=settings.llm_host, transport=httpx.MockTransport(handler)
    )
    return cliente


def test_el_host_sigue_al_backend():
    assert Settings(_env_file=None).llm_host == "http://127.0.0.1:11434"
    assert (
        Settings(llm_backend="openai", _env_file=None).llm_host == "http://127.0.0.1:8080"
    )


def test_backend_desconocido_se_rechaza():
    with pytest.raises(ValueError):
        Settings(llm_backend="otro", _env_file=None)


async def test_generar_usa_chat_completions_con_la_temperatura_configurada():
    vistos = {}

    def handler(request: httpx.Request) -> httpx.Response:
        vistos["ruta"] = request.url.path
        vistos["cuerpo"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hola"}}]})

    async with _cliente(handler, model_clinical="medgemma", temperature=0.0) as llm:
        assert await llm.generar("pregunta") == "hola"

    assert vistos["ruta"] == "/v1/chat/completions"
    assert vistos["cuerpo"]["model"] == "medgemma"
    assert vistos["cuerpo"]["temperature"] == 0.0
    assert vistos["cuerpo"]["messages"] == [{"role": "user", "content": "pregunta"}]


async def test_generar_json_rescata_el_json_de_una_valla():
    def handler(request: httpx.Request) -> httpx.Response:
        contenido = 'Claro:\n```json\n{"valido": true}\n```'
        return httpx.Response(
            200, json={"choices": [{"message": {"content": contenido}}]}
        )

    async with _cliente(handler) as llm:
        assert await llm.generar_json("x") == {"valido": True}


async def test_respuesta_mal_formada_es_llm_no_disponible():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    async with _cliente(handler) as llm:
        with pytest.raises(LLMUnavailable):
            await llm.generar("x")


async def test_servidor_caido_es_llm_no_disponible():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin conexión")

    async with _cliente(handler) as llm:
        with pytest.raises(LLMUnavailable):
            await llm.generar("x")
        assert await llm.disponible() is False
        assert await llm.modelos_disponibles() == []


async def test_elegir_opcion_degrada_al_defecto_si_el_servidor_cae():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin conexión")

    async with _cliente(handler) as llm:
        elegida = await llm.elegir_opcion("x", opciones_validas=["a", "b"], defecto="b")
    assert elegida == "b"


def _responde(texto: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": texto}}]})

    return handler


@pytest.mark.parametrize(
    ("respuesta", "esperada"),
    [
        ("tromboembolia_pulmonar", "tromboembolia_pulmonar"),
        ("  Protocolo: Tromboembolia_Pulmonar.\n", "tromboembolia_pulmonar"),
        # Recita la lista: no se elige ninguna, ni la primera.
        ("- acute_pancreatitis\n- tromboembolia_pulmonar", "general_triage"),
        ("tromboembolia_pulmonar o sindrome_coronario_agudo", "general_triage"),
        # Fuera del conjunto.
        ("no sé", "general_triage"),
        ("", "general_triage"),
    ],
)
async def test_elegir_opcion_no_elige_si_la_respuesta_es_ambigua(respuesta, esperada):
    opciones = ["acute_pancreatitis", "general_triage", "tromboembolia_pulmonar"]
    opciones.append("sindrome_coronario_agudo")
    async with _cliente(_responde(respuesta)) as llm:
        elegida = await llm.elegir_opcion(
            "x", opciones_validas=opciones, defecto="general_triage"
        )
    assert elegida == esperada


async def test_elegir_opcion_una_opcion_contenida_en_otra_no_es_ambigua():
    async with _cliente(_responde("apnea_del_sueno")) as llm:
        elegida = await llm.elegir_opcion(
            "x", opciones_validas=["apnea", "apnea_del_sueno"], defecto="apnea"
        )
    assert elegida == "apnea_del_sueno"


async def test_modelos_se_listan_desde_v1_models():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": [{"id": "medgemma-4b-it"}]})

    async with _cliente(handler) as llm:
        assert await llm.disponible() is True
        assert await llm.modelos_disponibles() == ["medgemma-4b-it"]
