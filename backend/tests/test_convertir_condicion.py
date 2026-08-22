"""El traslado desde medsemiotics-db no inventa lo que el índice no dice.

Estas pruebas necesitan un clon local del índice y se saltan si no está: es
un repositorio separado a propósito. CI lo clona antes de correrlas, así que
allí corren; en una máquina que no lo tenga, se saltan. Cuando está, cada
condición debe producir un protocolo que parsee, que pase su propia revisión
y —lo que de verdad importa— que no traiga ni un cociente que la fuente no
haya publicado tal cual.
"""

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from holonmed.core.skills import Skill  # noqa: E402

convertir_condicion = pytest.importorskip("convertir_condicion")

INDICE = convertir_condicion.INDICE_POR_DEFECTO

pytestmark = pytest.mark.skipif(
    not (INDICE / "condiciones").is_dir(),
    reason=f"no hay un clon de medsemiotics-db en {INDICE}",
)


@pytest.fixture(scope="module")
def indice():
    return convertir_condicion.cargar_indice(INDICE)


def _condiciones():
    if not (INDICE / "condiciones").is_dir():
        return []
    return sorted(convertir_condicion.cargar_indice(INDICE).condiciones)


def _convertir(identificador, indice):
    informe = convertir_condicion.Informe()
    borrador = convertir_condicion.convertir(
        indice.condiciones[identificador], indice, informe
    )
    return Skill(identificador, borrador.texto), indice.condiciones[identificador]


@pytest.mark.parametrize("identificador", _condiciones())
def test_el_borrador_parsea_y_se_revisa_solo(identificador, indice):
    skill, _ = _convertir(identificador, indice)
    assert skill.meta, "el frontmatter generado no es YAML válido"
    assert skill.descripcion
    assert skill.problemas() == []


@pytest.mark.parametrize("identificador", _condiciones())
def test_todo_cociente_trasladado_cita_su_fuente(identificador, indice):
    skill, _ = _convertir(identificador, indice)
    for signo in skill.signos:
        if signo.lr is not None and signo.lr != 1.0:
            assert signo.fuente, f"'{signo.nombre}' llega sin procedencia"


@pytest.mark.parametrize("identificador", _condiciones())
def test_ningun_cociente_sale_de_la_nada(identificador, indice):
    """Todo LR del protocolo tiene que estar publicado así en el índice.

    Es la garantía sobre la que descansa el conversor entero. Un rango entre
    estudios no se promedia y un LR− de 0 no se copia: si aquí aparece un
    número que el índice no declara como `valor`, alguien ha empezado a
    fabricar precisión.
    """
    skill, condicion = _convertir(identificador, indice)

    publicados: dict[str, set[float]] = {}
    for arista in condicion.get("signos") or []:
        termino = indice.termino(str(arista.get("concepto")))
        valores = set()
        for campo in ("lr_positivo", "lr_negativo"):
            bloque = arista.get(campo)
            valor = bloque.get("valor") if isinstance(bloque, dict) else bloque
            if isinstance(valor, (int, float)) and valor > 0:
                valores.add(float(valor))
        if arista.get("estado_lr") == "sin_efecto":
            # `sin_efecto` es lo único que se traduce a un número que el
            # índice no escribe: 1.0, que deja el hallazgo sin efecto.
            valores.add(1.0)
        publicados[termino] = valores

    for signo in skill.signos:
        for cociente in (signo.lr, signo.lr_negativo):
            if cociente is None:
                continue
            assert cociente in publicados.get(signo.nombre, set()), (
                f"'{signo.nombre}': el protocolo declara {cociente} y el índice no"
            )


@pytest.mark.parametrize("identificador", _condiciones())
def test_los_cortes_de_laboratorio_vienen_del_umbral_del_concepto(identificador, indice):
    skill, _ = _convertir(identificador, indice)
    for criterio in skill.laboratorio:
        codigo = criterio.codigos.get("holonmed", "")
        umbral = indice.concepto(codigo).get("umbral") or {}
        assert umbral, f"'{criterio.parametro}' no sale de ningún umbral del índice"
        assert criterio.corte_superior == umbral.get("corte_superior")
        assert criterio.corte_inferior == umbral.get("corte_inferior")
        assert criterio.multiplicador == umbral.get("multiplicador")


def test_el_ambito_del_grafo_no_incluye_la_raiz(indice):
    """Una rama que es la raíz ofrecería el protocolo a cualquier paciente."""
    for identificador in indice.condiciones:
        skill, _ = _convertir(identificador, indice)
        for rama in skill.ambito_grafo:
            semantica = indice.concepto(rama).get("semantica")
            assert semantica != "raiz", f"{identificador}: ámbito en la raíz {rama}"
