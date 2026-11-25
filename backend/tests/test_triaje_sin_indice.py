"""Sin `medsemiotics-db`, el triaje se detiene y lo dice.

Antes agrupaba con lo que aportan las skills, y la lista vacía que salía para
un cuadro que sí cumple criterios se leía como «ninguno se cumple». Ahora los
endpoints responden 503 y el tic sale sin agrupaciones, con el motivo. El
arranque no cambia.

Ninguna prueba depende del clon real: «sin índice» se provoca apuntando la
variable a un directorio inexistente, y «con índice» usa fichas sintéticas.
"""

from pathlib import Path

import pytest
from test_pipeline import IndexFalso, LLMFalso, entorno  # noqa: F401

from holonmed.cli import _lineas_competencia, _lineas_sin_candidatas
from holonmed.config import Settings
from holonmed.core.skills import SkillManager
from holonmed.core.triaje import (
    IndiceNoDisponible,
    TriajeOntologico,
    buscar_ruta_medsemiotics,
)
from holonmed.db import Database, GraphRepo, TicRepo
from holonmed.models import CandidataAbductiva, HolonPaciente, ResultadoTic

PROBLEMAS = [{"termino": "Signo de prueba", "codigo": "HM:9001"}]

# Una condición sintética que el cuadro de arriba satisface, para distinguir
# «el triaje corrió» de «el triaje corrió y no encontró nada».
CONDICION = """
id: 'HM:9100'
termino: Condición sintética
procedencia: { fuente: 'doble de prueba' }
signos:
  - concepto: 'HM:9001'
    rol: manifestacion
"""


@pytest.fixture
def sin_indice(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOLONMED_MEDSEMIOTICS_DIR", str(tmp_path / "no_existe"))


@pytest.fixture
def con_indice(indice_minimo: Path) -> Path:
    (indice_minimo / "condiciones" / "sintetica.yaml").write_text(
        CONDICION, encoding="utf-8"
    )
    return indice_minimo


# --- El motor --------------------------------------------------------------


@pytest.mark.parametrize("entrada", [PROBLEMAS, [], "texto libre"])
def test_sin_indice_agrupar_se_detiene_y_no_devuelve_una_lista(
    sin_indice, entrada
) -> None:
    """Ni siquiera sin problemas: `[]` afirmaría que se miró."""
    with pytest.raises(IndiceNoDisponible, match="Triaje detenido"):
        TriajeOntologico(skills_manager=SkillManager()).agrupar_problemas(entrada)


def test_con_indice_agrupa(con_indice) -> None:
    agrupaciones = TriajeOntologico().agrupar_problemas(PROBLEMAS)
    assert [a.condicion_id for a in agrupaciones] == ["HM:9100"]


def test_una_variable_mal_puesta_no_se_sustituye_por_otro_clon(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("HOLONMED_MEDSEMIOTICS_DIR", str(tmp_path / "no_existe"))
    # Aunque hubiera un clon hermano, que es lo que antes se leía en su lugar.
    monkeypatch.setattr(Path, "is_dir", lambda self: self.name == "medsemiotics-db")
    assert buscar_ruta_medsemiotics() is None


@pytest.mark.parametrize("vacia", ["conceptos", "condiciones"])
def test_un_indice_a_medias_tambien_detiene(indice_minimo, vacia) -> None:
    (indice_minimo / vacia / "prueba.yaml").unlink()
    with pytest.raises(IndiceNoDisponible, match=vacia):
        TriajeOntologico().agrupar_problemas(PROBLEMAS)


def test_el_motivo_no_lleva_rutas_de_la_maquina(tmp_path, indice_minimo) -> None:
    """Llega a la respuesta de la API y se guarda en el tic."""
    with pytest.raises(IndiceNoDisponible) as exc:
        TriajeOntologico(ruta_medsemiotics=tmp_path).agrupar_problemas(PROBLEMAS)
    assert str(tmp_path) not in str(exc.value)
    assert tmp_path.name not in str(exc.value)


# --- La API ------------------------------------------------------------------


def _peticiones(tmp_path: Path):
    from fastapi.testclient import TestClient

    from holonmed.api.app import crear_app
    from holonmed.api.deps import AppContext, get_context

    ajustes = Settings(db_path=tmp_path / "api.db", autocargar_semilla=False)
    contexto = AppContext(ajustes)
    app = crear_app(ajustes)
    app.dependency_overrides[get_context] = lambda: contexto
    with TestClient(app) as cliente:
        respuestas = (
            cliente.get("/api/pacientes/p1/triage"),
            cliente.post("/api/triage/agrupar", json=PROBLEMAS),
        )
        otra = cliente.get("/api/skills")
    contexto.database.cerrar()
    return respuestas, otra


def test_sin_indice_los_endpoints_de_triaje_responden_503(sin_indice, tmp_path) -> None:
    respuestas, otra = _peticiones(tmp_path)
    for respuesta in respuestas:
        assert respuesta.status_code == 503
        assert "Triaje detenido" in respuesta.json()["detail"]
    # El resto del sistema arranca y sirve igual.
    assert otra.status_code == 200


def test_con_indice_los_endpoints_de_triaje_responden(con_indice, tmp_path) -> None:
    (get, post), _ = _peticiones(tmp_path)
    assert get.status_code == 200
    assert post.status_code == 200
    assert "HM:9100" in [a["condicion_id"] for a in post.json()]


# --- El tic ------------------------------------------------------------------


class LLMQueNoDebeElegir(LLMFalso):
    async def elegir_opcion(self, prompt, *, opciones_validas, defecto, **kwargs):
        raise AssertionError("con el triaje detenido el prompt no elige protocolo")


async def test_sin_indice_el_tic_sale_sin_agrupaciones_y_dice_por_que(
    sin_indice,
    entorno,  # noqa: F811
    tmp_path,
) -> None:
    # Un segundo protocolo, para que haya algo que elegir.
    (tmp_path / "otro.md").write_text("# Otro protocolo\n", encoding="utf-8")
    pipeline = entorno(LLMQueNoDebeElegir(), IndexFalso(score=95.0, exacto=True))

    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )

    assert resultado.aviso_triaje is not None
    assert "Triaje detenido" in resultado.aviso_triaje
    assert resultado.agrupaciones_triage == []
    assert resultado.skill_activa == "general_triage"
    # Nada que comparar con el grafo: no eligió nada.
    assert resultado.skill_triaje is None
    assert resultado.triaje_coincide is None
    assert resultado.triaje_en_candidatas is None
    # La extracción no depende del índice: el tic no se pierde.
    assert resultado.infones


async def test_sin_indice_un_protocolo_forzado_se_respeta(
    sin_indice,
    entorno,  # noqa: F811
    tmp_path,
) -> None:
    (tmp_path / "otro.md").write_text("# Otro protocolo\n", encoding="utf-8")
    pipeline = entorno(LLMQueNoDebeElegir(), IndexFalso(score=95.0, exacto=True))

    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t"), skill_forzada="otro"
    )

    assert resultado.skill_activa == "otro"
    assert resultado.aviso_triaje is not None


async def test_con_indice_el_tic_no_lleva_aviso(
    con_indice,
    entorno,  # noqa: F811
) -> None:
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )
    assert resultado.aviso_triaje is None


def test_el_motivo_se_persiste_y_no_se_cuenta_como_falta_de_competencia(
    tmp_path,
) -> None:
    base = Database(tmp_path / "t.db")
    tics = TicRepo(base, GraphRepo(base))
    tic_id = tics.guardar(
        ResultadoTic(
            paciente_id="p1",
            texto_original="texto sintético",
            skill_activa="general_triage",
            aviso_triaje="Triaje detenido: prueba",
        )
    )

    assert tic_id is not None
    guardado = tics.tic_completo(tic_id)
    assert guardado is not None
    assert guardado["aviso_triaje"] == "Triaje detenido: prueba"
    medida = tics.acuerdo_del_triaje("p1")
    assert medida["triaje_detenido"] == 1
    assert medida["sin_competencia"] == 0
    base.cerrar()


def test_la_consola_no_atribuye_eleccion_a_un_triaje_detenido() -> None:
    r = ResultadoTic(
        paciente_id="t",
        texto_original="x",
        skill_activa="general_triage",
        aviso_triaje="Triaje detenido: prueba",
        sin_candidatas="nada_validado",
        competencia=[CandidataAbductiva(skill="a")],
    )
    texto = "\n".join(_lineas_sin_candidatas(r) + _lineas_competencia(r))
    assert "eligió el triaje" not in texto
    assert "El triaje estaba detenido" in texto
