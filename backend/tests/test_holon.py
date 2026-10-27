"""Tests del holon anidado.

Lo que se comprueba es la conservación: que bajar por los holones dé lo
mismo que recorrer todos los infones del episodio, y que cuando no lo dé el
sistema lo diga en vez de elegir una de las dos rutas.
"""

from holonmed.core.holon import (
    Documento,
    Nivel,
    componer,
    conciliar,
    nivel_de,
)
from holonmed.models import TipoNota


def _doc(tic_id, tipo, *infones, ordinal=None):
    return Documento(tic_id=tic_id, tipo=tipo, infones=tuple(infones), ordinal=ordinal)


def test_la_evolucion_no_es_un_holon():
    """Aporta infones, no síntesis. Darle un nivel la convertiría en una.

    Es lo contrario de lo que Weed pide al exigir notas tituladas y
    numeradas: la nota suelta no sintetiza, el holon secundario sí.
    """
    assert nivel_de(TipoNota.EVOLUCION) is None
    assert nivel_de(TipoNota.BASE) is Nivel.PRIMARIO
    assert nivel_de(TipoNota.CLINICA) is Nivel.SECUNDARIO
    assert nivel_de(TipoNota.EPICRISIS) is Nivel.FINAL


def test_cada_holon_recoge_lo_acumulado_desde_el_anterior():
    """Es para lo que nace: sintetizar las evoluciones que se juntaron."""
    documentos = [
        _doc("t1", TipoNota.BASE, "i1", "i2"),
        _doc("t2", TipoNota.EVOLUCION, "i3"),
        _doc("t3", TipoNota.EVOLUCION, "i4"),
        _doc("t4", TipoNota.CLINICA, ordinal=1),
    ]
    holones = componer(documentos)

    assert [h.tic_id for h in holones] == ["t1", "t4"]
    assert holones[0].infones_propios == ("i1", "i2")
    # La clínica-1 recoge las dos evoluciones que la precedieron.
    assert holones[1].infones_propios == ("i3", "i4")


def test_el_holon_final_los_contiene_a_todos():
    """Por eso es el final, y no uno más de la serie."""
    documentos = [
        _doc("t1", TipoNota.BASE, "i1"),
        _doc("t2", TipoNota.CLINICA, "i2", ordinal=1),
        _doc("t3", TipoNota.CLINICA, "i3", ordinal=2),
        _doc("t4", TipoNota.EPICRISIS),
    ]
    holones = componer(documentos)

    assert holones[0].compone == ()
    assert holones[1].compone == ("t1",)
    assert holones[2].compone == ("t1", "t2")
    assert holones[3].compone == ("t1", "t2", "t3")
    assert holones[3].nivel is Nivel.FINAL


def test_las_notas_clinicas_se_etiquetan_con_su_ordinal():
    documentos = [
        _doc("t1", TipoNota.BASE),
        _doc("t2", TipoNota.CLINICA, ordinal=2),
        _doc("t3", TipoNota.EPICRISIS),
    ]
    etiquetas = [h.etiqueta for h in componer(documentos)]
    assert etiquetas == ["primario", "clínica-2", "final"]


def test_una_clinica_sin_ordinal_lo_dice_en_vez_de_callarlo():
    holones = componer([_doc("t1", TipoNota.CLINICA)])
    assert holones[0].etiqueta == "clínica-(sin numerar)"


def test_las_dos_rutas_coinciden_en_un_episodio_cerrado():
    documentos = [
        _doc("t1", TipoNota.BASE, "i1"),
        _doc("t2", TipoNota.EVOLUCION, "i2"),
        _doc("t3", TipoNota.CLINICA, ordinal=1),
        _doc("t4", TipoNota.EPICRISIS),
    ]
    conservacion = conciliar(documentos, componer(documentos))

    assert conservacion.coincide
    assert conservacion.perdidos == ()
    assert not conservacion.hay_pendientes


def test_lo_que_llego_tras_el_ultimo_holon_espera_y_no_se_pierde():
    """Es el estado normal entre dos notas clínicas, no un error.

    Confundirlo con una pérdida haría que el sistema gritara cada vez que
    un paciente tiene evoluciones sin sintetizar todavía, que es siempre.
    """
    documentos = [
        _doc("t1", TipoNota.BASE, "i1"),
        _doc("t2", TipoNota.CLINICA, ordinal=1),
        _doc("t3", TipoNota.EVOLUCION, "i9"),
    ]
    conservacion = conciliar(documentos, componer(documentos))

    assert conservacion.coincide
    assert conservacion.huerfanos == ("i9",)
    assert "estado normal" in conservacion.razon


def test_un_infon_que_ningun_holon_recogio_se_denuncia():
    """Elegir una ruta en silencio dejaría una epicrisis que omite hallazgos.

    Se simula la divergencia pasando unos holones a los que les falta lo que
    la composición sí habría recogido.
    """
    documentos = [
        _doc("t1", TipoNota.BASE, "i1"),
        _doc("t2", TipoNota.EVOLUCION, "i2"),
        _doc("t3", TipoNota.CLINICA, ordinal=1),
    ]
    holones = componer(documentos)
    mutilado = [holones[0]]  # se pierde la clínica-1, y con ella `i2`

    conservacion = conciliar(documentos, mutilado)

    assert not conservacion.coincide
    assert conservacion.perdidos == ("i2",)
    assert "en silencio" in conservacion.razon


def test_un_episodio_vacio_no_afirma_nada():
    conservacion = conciliar([], [])
    assert conservacion.coincide
    assert conservacion.perdidos == ()


def test_la_secuencia_canonica_entera_se_compone():
    """historia → evoluciones → clínica-1 → evoluciones → clínica-2 → epicrisis."""
    documentos = [
        _doc("t1", TipoNota.BASE, "i1"),
        _doc("t2", TipoNota.EVOLUCION, "i2"),
        _doc("t3", TipoNota.EVOLUCION, "i3"),
        _doc("t4", TipoNota.CLINICA, ordinal=1),
        _doc("t5", TipoNota.EVOLUCION, "i4"),
        _doc("t6", TipoNota.CLINICA, ordinal=2),
        _doc("t7", TipoNota.EPICRISIS),
    ]
    holones = componer(documentos)

    assert [h.etiqueta for h in holones] == [
        "primario",
        "clínica-1",
        "clínica-2",
        "final",
    ]
    assert holones[1].infones_propios == ("i2", "i3")
    assert holones[2].infones_propios == ("i4",)
    assert conciliar(documentos, holones).coincide
