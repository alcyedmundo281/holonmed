"""Tests de las reglas del episodio.

Lo que se comprueba no es que la secuencia feliz funcione, sino que las
cuatro formas de romperla se rechacen **con su razón**. Un rechazo sin
motivo se lee como un fallo del sistema y se reintenta.
"""

from holonmed.core.episodio import Admision, EstadoEpisodio, admite, etiqueta
from holonmed.models import TipoNota

VACIO = EstadoEpisodio()
ABIERTO = EstadoEpisodio(tiene_historia=True)


def test_la_historia_abre_el_episodio():
    assert admite(VACIO, TipoNota.BASE).admitido


def test_nada_precede_a_la_historia():
    """Una evolución sin base sería un hallazgo sin a quién atribuírselo."""
    for tipo in (TipoNota.EVOLUCION, TipoNota.CLINICA, TipoNota.EPICRISIS):
        veredicto = admite(VACIO, tipo)
        assert not veredicto.admitido
        assert "no tiene todavía su historia" in veredicto.motivo


def test_la_historia_no_se_escribe_dos_veces():
    """La segunda cambiaría la lista de problemas sin que nadie lo advirtiera."""
    veredicto = admite(ABIERTO, TipoNota.BASE)
    assert not veredicto.admitido
    assert "ya tiene su historia" in veredicto.motivo


def test_las_notas_clinicas_se_numeran_en_orden():
    assert admite(ABIERTO, TipoNota.CLINICA).ordinal == 1
    tras_una = EstadoEpisodio(tiene_historia=True, notas_clinicas=1)
    assert admite(tras_una, TipoNota.CLINICA).ordinal == 2
    tras_siete = EstadoEpisodio(tiene_historia=True, notas_clinicas=7)
    assert admite(tras_siete, TipoNota.CLINICA).ordinal == 8


def test_el_ordinal_lo_da_quien_autoriza_la_escritura():
    """Calcularlo aparte abriría la puerta a que los dos números difieran."""
    veredicto = admite(ABIERTO, TipoNota.CLINICA)
    assert veredicto.admitido and veredicto.ordinal == 1
    # La evolución no lleva número: sólo la clínica se cita por su ordinal.
    assert admite(ABIERTO, TipoNota.EVOLUCION).ordinal is None


def test_una_epicrisis_sin_nota_clinica_no_cierra_nada():
    """Cerrar sin que nadie haya sintetizado es el documento-ficción de Weed."""
    veredicto = admite(ABIERTO, TipoNota.EPICRISIS)
    assert not veredicto.admitido
    assert "ninguna nota clínica que sintetizar" in veredicto.motivo


def test_la_epicrisis_cierra_cuando_hay_algo_que_cerrar():
    con_clinica = EstadoEpisodio(tiene_historia=True, notas_clinicas=2)
    assert admite(con_clinica, TipoNota.EPICRISIS).admitido


def test_un_episodio_cerrado_no_admite_nada():
    """Si se pudiera seguir escribiendo, la epicrisis sería un documento más."""
    cerrado = EstadoEpisodio(cerrado=True, tiene_historia=True, notas_clinicas=3)
    for tipo in TipoNota:
        veredicto = admite(cerrado, tipo)
        assert not veredicto.admitido
        assert "está cerrado" in veredicto.motivo


def test_el_cierre_manda_sobre_las_demas_reglas():
    """Un episodio cerrado y sin historia se rechaza POR cerrado.

    El orden importa para el mensaje: decirle a alguien que le falta la
    historia clínica de un episodio ya cerrado le manda a arreglar lo que
    no es.
    """
    raro = EstadoEpisodio(cerrado=True)
    assert "está cerrado" in admite(raro, TipoNota.EVOLUCION).motivo


def test_la_secuencia_canonica_entera_pasa():
    """historia → evoluciones → clínica-1 → … → clínica-N → epicrisis."""
    estado = EstadoEpisodio()
    assert admite(estado, TipoNota.BASE).admitido
    estado = EstadoEpisodio(tiene_historia=True)

    ordinales = []
    for _ in range(3):
        assert admite(estado, TipoNota.EVOLUCION).admitido
        veredicto = admite(estado, TipoNota.CLINICA)
        assert veredicto.admitido
        ordinales.append(veredicto.ordinal)
        estado = EstadoEpisodio(
            tiene_historia=True, notas_clinicas=estado.notas_clinicas + 1
        )

    assert ordinales == [1, 2, 3]
    assert admite(estado, TipoNota.EPICRISIS).admitido


def test_solo_la_nota_clinica_lleva_numero():
    assert etiqueta(TipoNota.CLINICA, 2) == "clínica-2"
    assert etiqueta(TipoNota.EVOLUCION, None) == "evolucion"
    assert etiqueta(TipoNota.EPICRISIS, None) == "epicrisis"


def test_una_clinica_sin_ordinal_lo_dice_en_vez_de_callarlo():
    """Citarla es para lo que Weed la numeraba; sin número no se puede."""
    assert etiqueta(TipoNota.CLINICA, None) == "clínica-(sin numerar)"


def test_un_rechazo_siempre_trae_su_razon():
    negativas = [
        admite(VACIO, TipoNota.EVOLUCION),
        admite(ABIERTO, TipoNota.BASE),
        admite(ABIERTO, TipoNota.EPICRISIS),
        admite(EstadoEpisodio(cerrado=True), TipoNota.BASE),
    ]
    for veredicto in negativas:
        assert isinstance(veredicto, Admision)
        assert not veredicto.admitido
        assert len(veredicto.motivo) > 40
