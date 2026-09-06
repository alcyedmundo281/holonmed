"""Tests de potencia y acto.

Lo que se comprueba es que el sistema **no pueda presentar como real** lo
que sólo él ha validado, y que la corrección —que es el producto— no se
pueda registrar vacía.
"""

import pytest

from holonmed.core.actualizacion import (
    Acto,
    Actualizacion,
    TasaDeCorreccion,
    describir,
    es_real,
    medir,
)

AHORA = "2026-09-05T10:00:00Z"


def _acto(acto=Acto.ACEPTADO, por="Dra. Ruiz", cambios=None):
    return Actualizacion(acto=acto, por=por, cuando=AHORA, cambios=cambios or {})


def test_lo_que_nadie_actualizo_no_es_real():
    """Es el estado inicial correcto, no un defecto que rellenar."""
    assert not es_real(None)
    assert describir(None) == "potencial: propuesto por el sistema, sin ratificar"


def test_aceptar_y_corregir_actualizan_rechazar_no():
    assert es_real(_acto(Acto.ACEPTADO))
    assert es_real(_acto(Acto.CORREGIDO, cambios={"termino": ("a", "b")}))
    assert not es_real(_acto(Acto.RECHAZADO))


def test_una_actualizacion_sin_nombre_no_es_una_ratificacion():
    """«Alguien lo validó» no se puede auditar, y el contrato pide nombre."""
    with pytest.raises(ValueError, match="nombrada"):
        Actualizacion(acto=Acto.ACEPTADO, por="   ", cuando=AHORA)


def test_una_correccion_sin_decir_que_cambio_no_mide_nada():
    """Medir es para lo que existe la corrección."""
    with pytest.raises(ValueError, match="qué cambió"):
        Actualizacion(acto=Acto.CORREGIDO, por="Dra. Ruiz", cuando=AHORA)


def test_aceptar_no_puede_traer_cambios():
    """Si hubo corrección, el acto es corregir; llamarlo aceptar la escondería."""
    with pytest.raises(ValueError, match="no cambia nada"):
        Actualizacion(
            acto=Acto.ACEPTADO,
            por="Dra. Ruiz",
            cuando=AHORA,
            cambios={"termino": ("a", "b")},
        )


def test_el_rechazo_se_muestra_con_su_autor_en_vez_de_borrarse():
    """Lo rechazado dice algo sobre el sistema, no sobre el paciente."""
    assert describir(_acto(Acto.RECHAZADO)) == "rechazado por Dra. Ruiz"


def test_la_correccion_dice_en_que_campos():
    texto = describir(
        _acto(Acto.CORREGIDO, cambios={"termino": ("a", "b"), "polaridad": ("x", "y")})
    )
    assert texto == "real, corregido por Dra. Ruiz en polaridad, termino"


def test_sin_nadie_que_actue_la_tasa_es_none_y_no_cero():
    """Cero diría que el sistema no se equivocó; lo que pasa es que nadie miró.

    Es la misma distinción que `triaje_coincide` guarda como NULL en vez de
    como 0, y por la misma razón: meterlo en el denominador inventa una tasa.
    """
    tasa = medir([None, None, None])
    assert tasa.tasa is None
    assert tasa.sin_actuar == 3
    assert tasa.actuados == 0


def test_la_tasa_cuenta_correcciones_y_rechazos_como_desacuerdo():
    tasa = medir(
        [
            _acto(Acto.ACEPTADO),
            _acto(Acto.ACEPTADO),
            _acto(Acto.CORREGIDO, cambios={"termino": ("a", "b")}),
            _acto(Acto.RECHAZADO),
            None,
        ]
    )
    assert tasa.actuados == 4
    assert tasa.tasa == 0.5
    # El que nadie miró no cuenta como acierto.
    assert tasa.sin_actuar == 1


def test_la_tasa_dice_en_que_campo_falla_el_sistema():
    """Un contador de aciertos no dice en qué falla; el desglose sí."""
    tasa = medir(
        [
            _acto(Acto.CORREGIDO, cambios={"termino": ("a", "b")}),
            _acto(Acto.CORREGIDO, cambios={"termino": ("c", "d")}),
            _acto(Acto.CORREGIDO, cambios={"polaridad": ("x", "y")}),
        ]
    )
    assert tasa.por_campo == {"termino": 2, "polaridad": 1}


def test_una_tanda_vacia_no_afirma_nada():
    assert medir([]).tasa is None
    assert TasaDeCorreccion().tasa is None
