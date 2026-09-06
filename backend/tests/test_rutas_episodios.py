"""Tests de la interfaz por la que entra todo.

No se comprueba que FastAPI enrute: se comprueba que el contrato **no deje
pasar** lo que la secuencia de Weed no admite, y que lo que sale de la
institución exija firma.

El pipeline se dobla porque estas rutas no lo prueban a él: probarlo aquí
exigiría Ollama y taparía lo que sí se quiere ver.
"""

import pytest
from fastapi.testclient import TestClient

from holonmed.api.app import crear_app
from holonmed.api.deps import AppContext, get_context
from holonmed.config import Settings
from holonmed.models import ResultadoTic


class _PipelineDoble:
    """Devuelve un tic vacío: lo que se prueba es la secuencia, no la extracción."""

    async def ejecutar(self, texto, holon):
        return ResultadoTic(
            paciente_id=holon.paciente_id,
            texto_original=texto,
            skill_activa="general_triage",
        )


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    ajustes = Settings(db_path=tmp_path / "h.db", autocargar_semilla=False)
    contexto = AppContext(ajustes)
    contexto.pipeline = _PipelineDoble()

    app = crear_app(ajustes)
    app.dependency_overrides[get_context] = lambda: contexto
    with TestClient(app) as cliente:
        yield cliente
    contexto.database.cerrar()


def _abrir(cliente, alcance="comprehensiva"):
    respuesta = cliente.post(
        "/api/episodios",
        json={"paciente_id": "p1", "motivo": "dolor", "alcance_base": alcance},
    )
    assert respuesta.status_code == 201
    return respuesta.json()["episodio_id"]


def _escribir(cliente, episodio, tipo, texto="algo"):
    return cliente.post(
        f"/api/episodios/{episodio}/documentos",
        json={"texto": texto, "tipo": tipo},
    )


def test_una_evolucion_no_puede_preceder_a_la_historia(cliente):
    """Y el 409 trae el motivo: un rechazo sin razón se reintenta."""
    episodio = _abrir(cliente)
    respuesta = _escribir(cliente, episodio, "evolucion")

    assert respuesta.status_code == 409
    assert "historia clínica" in respuesta.json()["detail"]


def test_la_secuencia_canonica_entra_entera(cliente):
    episodio = _abrir(cliente)
    assert _escribir(cliente, episodio, "base").status_code == 201
    assert _escribir(cliente, episodio, "evolucion").status_code == 201

    clinica = _escribir(cliente, episodio, "clinica")
    assert clinica.status_code == 201
    # La nota clínica sale numerada: `clínica-2` sólo significa algo
    # respecto de `clínica-1`.
    assert clinica.json()["ordinal_clinica"] == 1

    assert _escribir(cliente, episodio, "epicrisis").status_code == 201


def test_una_segunda_historia_clinica_se_rechaza(cliente):
    episodio = _abrir(cliente)
    _escribir(cliente, episodio, "base")
    respuesta = _escribir(cliente, episodio, "base")

    assert respuesta.status_code == 409
    assert "ya tiene su historia" in respuesta.json()["detail"]


def test_la_escalera_de_holones_se_lee_con_su_conciliacion(cliente):
    """Viaja junta a propósito: quien lee los holones necesita saber si
    están completos, y quien tuviera que acordarse de preguntarlo no lo
    preguntaría."""
    episodio = _abrir(cliente)
    _escribir(cliente, episodio, "base")
    _escribir(cliente, episodio, "clinica")

    cuerpo = cliente.get(f"/api/episodios/{episodio}/holones").json()
    assert [h["etiqueta"] for h in cuerpo["holones"]] == ["primario", "clínica-1"]
    assert cuerpo["conservacion"]["coincide"]


def test_la_base_dice_que_falta_y_a_quien_pedirselo(cliente):
    """«Incompleta» sin destinatario no es accionable.

    Y el reparto por actor es lo que hace visible que la fase 1 de Weed no
    la teclea el médico.
    """
    episodio = _abrir(cliente)
    cuerpo = cliente.get(f"/api/episodios/{episodio}/base?edad=45").json()

    assert not cuerpo["completa"]
    quienes = set(cuerpo["faltan_por_quien"])
    assert {"paciente", "enfermeria", "medico", "laboratorio"} <= quienes


def test_sin_edad_la_base_condicionada_se_detiene(cliente):
    """Ni saltar los ítems por edad ni exigirlos sería cierto."""
    episodio = _abrir(cliente)
    cuerpo = cliente.get(f"/api/episodios/{episodio}/base").json()

    assert not cuerpo["completa"]
    assert "la edad no consta" in cuerpo["razon"]
    assert cuerpo["faltan_por_quien"] == {}


def test_la_base_minima_se_pide_como_minima(cliente):
    """Un episodio atendido con la mínima no se lee como comprehensivo."""
    episodio = _abrir(cliente, alcance="episodica")
    cuerpo = cliente.get(f"/api/episodios/{episodio}/base?edad=30").json()

    assert cuerpo["alcance"] == "episodica"
    assert "mínima" in cuerpo["base"].lower()


def test_cerrar_sin_firma_se_rechaza(cliente):
    """La epicrisis sale de la institución: «alguien la cerró» no se audita."""
    episodio = _abrir(cliente)
    respuesta = cliente.post(f"/api/episodios/{episodio}/cerrar?firmante=%20%20")

    assert respuesta.status_code == 422
    assert "firma con nombre" in respuesta.json()["detail"]


def test_un_episodio_cerrado_no_admite_mas_documentos(cliente):
    episodio = _abrir(cliente)
    _escribir(cliente, episodio, "base")
    cliente.post(f"/api/episodios/{episodio}/cerrar?firmante=Dra.%20Ruiz")

    respuesta = _escribir(cliente, episodio, "evolucion")
    assert respuesta.status_code == 409
    assert "cerrado" in respuesta.json()["detail"]


def test_un_episodio_inventado_no_existe(cliente):
    assert _escribir(cliente, "9999", "base").status_code == 404
