"""Una ficha rota en un índice presente detiene el triaje y se nombra.

Antes se saltaba con un log de depuración: la condición no salía en la lista, o
sus criterios se quedaban sin los sinónimos del concepto perdido, y en ambos
casos un criterio que se cumple se podía leer como que no.

Todas las fichas son sintéticas.
"""

from pathlib import Path

import pytest
from test_pipeline import IndexFalso, LLMFalso, entorno  # noqa: F401
from test_triaje_sin_indice import CONDICION, PROBLEMAS, _peticiones

from holonmed.core.triaje import (
    MAX_FICHAS_NOMBRADAS,
    FichaIlegible,
    TriajeOntologico,
)
from holonmed.models import HolonPaciente

BASE = "id: 'HM:9200'\ntermino: Ficha sintética rota\n"

# Lo que no vale ni como concepto ni como condición.
ROTAS_COMUNES = {
    "yaml_invalido": "id: [sin cerrar\n",
    "fecha_imposible": BASE + "fecha: 2026-13-45\n",
    "vacia": "",
    "solo_comentario": "# pendiente\n",
    "lista": "- id: 'HM:9200'\n",
    "sin_id": "termino: Sin identificador\n",
    "id_numerico": "id: 9200\ntermino: Identificador numérico\n",
    "sin_termino": "id: 'HM:9200'\n",
    # Se recorría letra a letra, y una sola letra coincide con casi todo.
    "sinonimos_texto": BASE + "sinonimos: fiebre\n",
    "sinonimos_numeros": BASE + "sinonimos: [1, 2]\n",
    "codigos_texto": BASE + "codigos: ninguno\n",
}

ROTAS_DE_CONDICION = {
    "procedencia_texto": "procedencia: una fuente\n",
    "nucleo_nulo": "nucleo:\n",
    "nucleo_vacio": "nucleo: {}\n",
    "nucleo_requiere_texto": "nucleo: { requiere: 'HM:9001' }\n",
    "escalas_mapa": "escalas: { nombre: Centor }\n",
    "escalas_de_textos": "escalas: [Centor]\n",
    "tramos_de_textos": "escalas: [{ nombre: x, tramos: [alto] }]\n",
    "signos_de_textos": "signos: ['HM:9001']\n",
    "signo_sin_concepto": "signos: [{ rol: manifestacion }]\n",
    "rol_nulo": "signos: [{ concepto: 'HM:9001', rol: null }]\n",
    "lr_suelto": "signos: [{ concepto: 'HM:9001', lr_positivo: 3.2 }]\n",
    "lr_texto": "signos: [{ concepto: 'HM:9001', lr_negativo: { valor: alto } }]\n",
}


@pytest.fixture
def indice(indice_minimo: Path) -> Path:
    """Un índice sano, con una condición que `PROBLEMAS` satisface."""
    (indice_minimo / "condiciones" / "sintetica.yaml").write_text(
        CONDICION, encoding="utf-8"
    )
    return indice_minimo


def _romper(indice: Path, ruta: str, contenido: str | bytes) -> Path:
    archivo = indice / ruta
    if isinstance(contenido, bytes):
        archivo.write_bytes(contenido)
    else:
        archivo.write_text(contenido, encoding="utf-8")
    return archivo


def _detenido(indice: Path) -> FichaIlegible:
    with pytest.raises(FichaIlegible, match="Triaje detenido") as exc:
        TriajeOntologico().agrupar_problemas(PROBLEMAS)
    motivo = str(exc.value)
    assert str(indice) not in motivo
    assert indice.name not in motivo
    return exc.value


@pytest.mark.parametrize("carpeta", ["conceptos", "condiciones"])
@pytest.mark.parametrize("contenido", ROTAS_COMUNES.values(), ids=ROTAS_COMUNES)
def test_una_ficha_rota_detiene_y_se_nombra(indice, carpeta, contenido) -> None:
    _romper(indice, f"{carpeta}/rota.yaml", contenido)
    error = _detenido(indice)
    assert [ruta for ruta, _ in error.fichas] == [f"{carpeta}/rota.yaml"]
    assert f"{carpeta}/rota.yaml" in str(error)


@pytest.mark.parametrize("cuerpo", ROTAS_DE_CONDICION.values(), ids=ROTAS_DE_CONDICION)
def test_una_condicion_mal_formada_detiene(indice, cuerpo) -> None:
    _romper(indice, "condiciones/rota.yaml", BASE + cuerpo)
    assert [r for r, _ in _detenido(indice).fichas] == ["condiciones/rota.yaml"]


@pytest.mark.parametrize("carpeta", ["conceptos", "condiciones"])
def test_una_ficha_que_no_es_utf8_detiene(indice, carpeta) -> None:
    _romper(indice, f"{carpeta}/rota.yaml", "termino: señal\n".encode("latin-1"))
    assert "no se pudo leer" in str(_detenido(indice))


def test_un_fallo_que_la_validacion_no_preve_tambien_detiene(indice, monkeypatch) -> None:
    def revienta(texto: str) -> None:
        raise KeyError("forma imprevista")

    monkeypatch.setattr("holonmed.core.triaje._extraer_pmid", revienta)
    with pytest.raises(FichaIlegible, match="no se pudo procesar"):
        TriajeOntologico().agrupar_problemas(PROBLEMAS)


def test_el_motivo_no_copia_el_contenido_de_la_ficha(indice) -> None:
    _romper(indice, "condiciones/rota.yaml", "id: [centinela_del_contenido\n")
    assert "centinela_del_contenido" not in str(_detenido(indice))


def test_con_muchas_rotas_el_motivo_nombra_algunas_y_cuenta_el_resto(indice) -> None:
    total = MAX_FICHAS_NOMBRADAS + 3
    for n in range(total):
        _romper(indice, f"condiciones/rota_{n}.yaml", "")
    error = _detenido(indice)
    assert len(error.fichas) == total
    assert str(error).count(".yaml") == MAX_FICHAS_NOMBRADAS
    assert "y 3 más" in str(error)


@pytest.mark.parametrize("carpeta", ["conceptos", "condiciones"])
def test_corregida_la_ficha_el_mismo_motor_vuelve_a_agrupar(indice, carpeta) -> None:
    archivo = _romper(indice, f"{carpeta}/rota.yaml", "")
    triaje = TriajeOntologico()
    # Dos veces: el fallo no deja en caché un índice incompleto.
    for _ in range(2):
        with pytest.raises(FichaIlegible):
            triaje.agrupar_problemas(PROBLEMAS)

    archivo.write_text(BASE, encoding="utf-8")

    assert [a.condicion_id for a in triaje.agrupar_problemas(PROBLEMAS)] == ["HM:9100"]


def test_los_campos_opcionales_nulos_o_vacios_valen(indice) -> None:
    _romper(
        indice,
        "condiciones/opcionales.yaml",
        BASE
        + "sinonimos: []\ncodigos:\nprocedencia:\nescalas:\n"
        + "signos: [{ concepto: 'HM:9001', lr_positivo: { valor: null } }]\n",
    )
    ids = {a.condicion_id for a in TriajeOntologico().agrupar_problemas(PROBLEMAS)}
    assert ids == {"HM:9100", "HM:9200"}


def test_los_endpoints_responden_503_y_nombran_la_ficha(indice, tmp_path) -> None:
    _romper(indice, "condiciones/rota.yaml", "")
    respuestas, otra = _peticiones(tmp_path)
    for respuesta in respuestas:
        assert respuesta.status_code == 503
        assert "condiciones/rota.yaml" in respuesta.json()["detail"]
    assert otra.status_code == 200


async def test_el_tic_sale_sin_agrupaciones_y_nombra_la_ficha(
    indice,
    entorno,  # noqa: F811
) -> None:
    _romper(indice, "conceptos/rota.yaml", "")
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))

    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )

    assert resultado.aviso_triaje is not None
    assert "conceptos/rota.yaml" in resultado.aviso_triaje
    assert resultado.agrupaciones_triage == []
    assert resultado.skill_triaje is None
    assert resultado.infones
