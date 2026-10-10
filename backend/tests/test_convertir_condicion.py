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
    skill, condicion = _convertir(identificador, indice)
    assert skill.meta, "el frontmatter generado no es YAML válido"
    assert skill.descripcion
    problemas = skill.problemas()
    if not skill.signos and not skill.laboratorio:
        # Única excepción: una condición cuya evidencia entera es una exclusión
        # sostenida por un cociente medido. `excluye` sería un veto absoluto y el
        # conversor se niega a emitirla (HM:6035, HM:6039), así que el borrador
        # queda sin signos y lo dice. Es lo correcto: nadie puede promoverlo sin
        # decidir primero qué hacer con esa evidencia.
        aristas = condicion.get("signos") or []
        assert aristas and all(
            a.get("efecto") == "excluye" and a.get("sostiene") != "mecanismo"
            for a in aristas
        ), "un borrador sin signos que no se explica por exclusiones medidas"
        assert problemas == ["no declara signos ni criterios de laboratorio"]
    else:
        assert problemas == []


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
        publicados.setdefault(termino, set()).update(valores)

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


# ── los borradores de --sync-all no se activan solos ─────────────────────────


def test_los_borradores_no_los_lee_el_cargador_de_skills():
    """El cargador sólo lee `skills/*.md`: un borrador sin prosa ni prevalencia
    no puede llegar al triaje hasta que un humano lo suba un nivel."""
    from holonmed.config import get_settings
    from holonmed.core.skills import SkillManager

    directorio = convertir_condicion.DIRECTORIO_BORRADORES
    assert directorio.parent == convertir_condicion.DIRECTORIO_SKILLS
    cargados = set(SkillManager(get_settings()).listar())
    asignados = {p.stem for p in directorio.glob("*.md")}
    assert asignados, "no hay borradores que comprobar"
    assert not cargados & asignados


def test_lo_ya_cubierto_se_detecta_por_codigo_no_por_nombre_de_archivo():
    """`acute_pancreatitis.md` no se llama como lo llamaría el conversor y sólo
    declara SNOMED: compararlo por nombre lo duplicaría."""
    cubiertas = convertir_condicion.condiciones_con_protocolo()
    assert "snomed:197456007" in cubiertas
    assert "holonmed:HM:6016" in cubiertas
