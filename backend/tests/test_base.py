"""Tests de la base de datos definida — la fase 1 de Weed.

Lo que se comprueba aquí no es que el parser lea YAML, sino que la base se
niegue a darse por cumplida cuando no lo está. Ése es el valor entero de la
pieza: una base que se completa sola no es una base.
"""

from pathlib import Path

import pytest

from holonmed.core.base import (
    Alcance,
    Base,
    ItemBase,
    Quien,
    SeccionBase,
    cargar,
    cargar_todas,
    evaluar,
    validar,
)

BASES = Path(__file__).resolve().parents[1] / "base"


def _base(*items: ItemBase, alcance: Alcance = Alcance.COMPREHENSIVA) -> Base:
    return Base(
        titulo="prueba",
        version="1.0.0",
        alcance=alcance,
        secciones=(SeccionBase(nombre="única", items=items),),
    )


def test_una_base_completa_se_declara_completa():
    base = _base(ItemBase("Edad", Quien.PACIENTE), ItemBase("Peso", Quien.ENFERMERIA))
    estado = evaluar(base, ["Edad", "Peso"], edad=40)
    assert estado.completa
    assert estado.faltan == ()


def test_lo_que_falta_se_dice_y_se_dice_a_quien_pedirselo():
    """«La base está incompleta» sin destinatario no es accionable.

    Una lista de huecos que nadie sabe quién llena se queda sin llenar, así
    que el estado los reparte por actor.
    """
    base = _base(
        ItemBase("Edad", Quien.PACIENTE),
        ItemBase("Presión arterial", Quien.ENFERMERIA),
        ItemBase("Hemograma", Quien.LABORATORIO),
    )
    estado = evaluar(base, ["Edad"], edad=40)

    assert not estado.completa
    assert estado.faltan_por_quien == {
        "enfermeria": ["Presión arterial"],
        "laboratorio": ["Hemograma"],
    }


def test_la_comparacion_no_se_rompe_por_mayusculas_ni_espacios():
    base = _base(ItemBase("Presión arterial", Quien.ENFERMERIA))
    assert evaluar(base, ["  PRESIÓN   ARTERIAL "], edad=30).completa


def test_sin_edad_una_base_que_depende_de_ella_se_detiene():
    """Ni saltar el ítem ni exigirlo sería cierto, así que no se elige.

    Saltarlo afirmaría que no aplica; exigirlo, que sí. El sistema no lo
    sabe, y el contrato dice que ante un dato ausente se detiene y explica
    en vez de completar para poder continuar.
    """
    base = _base(
        ItemBase("Edad", Quien.PACIENTE),
        ItemBase("Perfil lipídico", Quien.LABORATORIO, desde_edad=40),
    )
    estado = evaluar(base, ["Edad", "Perfil lipídico"], edad=None)

    assert not estado.completa
    assert "la edad no consta" in estado.razon
    # No inventa una lista de faltantes: no sabe cuáles son.
    assert estado.faltan == ()


def test_un_item_fuera_de_su_rango_de_edad_no_se_exige():
    base = _base(ItemBase("Perfil lipídico", Quien.LABORATORIO, desde_edad=40))
    assert evaluar(base, [], edad=25).completa
    assert not evaluar(base, [], edad=55).completa


@pytest.mark.parametrize("archivo", ["adulto", "episodica"])
def test_las_bases_del_proyecto_cargan_y_son_validas(archivo):
    base = cargar(BASES / f"{archivo}.md")
    assert base.items
    assert validar([base]) == []


def test_la_base_minima_se_declara_como_tal():
    """Un episodio atendido con la mínima no puede leerse como comprehensivo.

    Es la razón entera de que la excepción esté declarada: en cuanto es
    informal, se convierte en la regla los días de mucha carga.
    """
    bases = cargar_todas(BASES)
    assert bases["adulto"].alcance is Alcance.COMPREHENSIVA
    assert bases["episodica"].alcance is Alcance.EPISODICA
    assert len(bases["episodica"].items) < len(bases["adulto"].items)


def test_un_item_sin_quien_no_cuenta(tmp_path):
    """Un ítem que nadie obtiene sólo sirve para que la base nunca se cierre."""
    ruta = tmp_path / "coja.md"
    ruta.write_text(
        "---\n"
        "titulo: Coja\n"
        "alcance: comprehensiva\n"
        "secciones:\n"
        "  - nombre: única\n"
        "    items:\n"
        "      - { nombre: Edad, quien: paciente }\n"
        "      - { nombre: Algo, quien: el_viento }\n"
        "---\n",
        encoding="utf-8",
    )
    base = cargar(ruta)
    assert [i.nombre for i in base.items] == ["Edad"]


def test_un_alcance_ausente_es_un_error_y_no_un_defecto(tmp_path):
    """Suponer «comprehensiva» daría por cubierto lo que nadie preguntó."""
    ruta = tmp_path / "sin_alcance.md"
    ruta.write_text(
        "---\ntitulo: Sin alcance\nsecciones: []\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="alcance"):
        cargar(ruta)


def test_validar_caza_el_rango_invertido_y_el_duplicado():
    base = _base(
        ItemBase("Edad", Quien.PACIENTE),
        ItemBase("edad", Quien.ENFERMERIA),
        ItemBase("Imposible", Quien.MEDICO, desde_edad=60, hasta_edad=30),
    )
    problemas = validar([base])
    assert any("dos veces" in p for p in problemas)
    assert any("invertido" in p for p in problemas)


def test_una_base_sin_items_no_es_una_base():
    vacia = Base(titulo="vacía", version="1.0.0", alcance=Alcance.COMPREHENSIVA)
    assert any("no exige ni un ítem" in p for p in validar([vacia]))
