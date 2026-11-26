"""Tests de la partida doble.

Lo que se comprueba por encima de todo es que **pendiente no cuente como
pasado por alto**. Inflar la cifra con trabajo que aún no se ha hecho la
haría inservible: una tasa inflada se ignora a la semana.
"""

from holonmed.core.partida_doble import Situacion, conciliar
from holonmed.models import EstadoInfon, Infon, Polaridad


def _infon(termino, estado=EstadoInfon.VALIDADO, acto=None):
    return Infon(
        texto_origen=termino,
        termino_propuesto=termino.lower(),
        termino=termino,
        estado=estado,
        acto=acto,
        actualizado_por="Dra. Ruiz" if acto else None,
        correccion={"termino": ["x", "y"]} if acto == "corregido" else {},
    )


def test_lo_que_ambos_libros_recogen_concuerda():
    balance = conciliar({"t1": [_infon("Fiebre", acto="aceptado")]})

    assert balance.concuerdan == 1
    assert balance.asientos[0].situacion is Situacion.CONCUERDA
    assert not balance.asientos[0].es_discrepancia


def test_una_nota_sin_abrir_deja_todo_pendiente():
    """Pendiente no es pasado por alto: nadie ha dejado nada todavía."""
    balance = conciliar({"t1": [_infon("Fiebre"), _infon("Disnea")]})

    assert balance.pendientes == 2
    assert balance.solo_holonmed == 0
    # Y sin nada revisado, no hay tasa: no es cero, es que no hay con qué
    # compararlo.
    assert balance.tasa_pasados_por_alto is None
    assert balance.conciliados == 0


def test_lo_que_el_clinico_dejo_sin_tocar_en_una_nota_que_si_reviso():
    """Es la cifra de Weed: 5.2 problemas por paciente en urgencias.

    La señal de que la revisó es que hay hermanos suyos con acto.
    """
    balance = conciliar(
        {"t1": [_infon("Fiebre", acto="aceptado"), _infon("Hipopotasemia")]}
    )

    assert balance.concuerdan == 1
    assert balance.solo_holonmed == 1
    assert balance.pendientes == 0
    assert balance.tasa_pasados_por_alto == 0.5
    assert "pasado por alto" in balance.asientos[1].motivo
    assert "PROPONE" in balance.asientos[1].motivo


def test_la_señal_de_revisado_es_por_nota_y_no_global():
    """Una nota revisada no vuelve revisadas a las demás."""
    balance = conciliar(
        {
            "t1": [_infon("Fiebre", acto="aceptado"), _infon("Disnea")],
            "t2": [_infon("Tos")],
        }
    )
    assert balance.solo_holonmed == 1
    assert balance.pendientes == 1


def test_un_rechazo_cuenta_como_revisado_pero_no_como_ratificado():
    """El clínico miró y dijo que no: la nota está revisada, el hallazgo no
    entra en su libro."""
    balance = conciliar({"t1": [_infon("Fiebre", acto="rechazado")]})

    assert balance.solo_holonmed == 1
    assert balance.concuerdan == 0


def test_lo_que_el_clinico_escribio_y_el_validador_no_dio_por_bueno():
    """Mide al índice, no al médico. Es la mitad que suele faltar."""
    balance = conciliar(
        {"t1": [_infon("Rareza", estado=EstadoInfon.ALERTA, acto="aceptado")]}
    )

    assert balance.solo_clinico == 1
    assert balance.tasa_sin_cobertura == 1.0
    assert "cobertura que falta" in balance.asientos[0].motivo


def test_los_pendientes_no_entran_en_ninguna_tasa():
    """Son trabajo sin hacer, no desacuerdo."""
    balance = conciliar(
        {
            "t1": [_infon("Fiebre", acto="aceptado"), _infon("Disnea")],
            "t2": [_infon("Tos"), _infon("Cefalea")],
        }
    )
    assert balance.pendientes == 2
    assert balance.conciliados == 2
    assert balance.tasa_pasados_por_alto == 0.5


def test_el_desglose_dice_que_se_pasa_por_alto_mas_a_menudo():
    """Una cifra sin desglose no se puede accionar."""
    balance = conciliar(
        {
            "t1": [_infon("Fiebre", acto="aceptado"), _infon("Hipopotasemia")],
            "t2": [_infon("Tos", acto="aceptado"), _infon("Hipopotasemia")],
        }
    )
    assert balance.por_termino == {"Hipopotasemia": 2}


def test_una_correccion_tambien_es_ratificacion():
    """Corregir es hacerlo suyo: el hallazgo entra en el libro del clínico."""
    balance = conciliar({"t1": [_infon("Fiebre", acto="corregido")]})
    assert balance.concuerdan == 1


def test_una_tanda_vacia_no_afirma_nada():
    balance = conciliar({})
    assert balance.tasa_pasados_por_alto is None
    assert balance.tasa_sin_cobertura is None
    assert balance.asientos == ()


def test_el_ruido_descartado_no_esta_en_ningun_libro():
    """Lo que el validador tiró y nadie ratificó no es una discrepancia."""
    balance = conciliar({"t1": [_infon("Alucinación", estado=EstadoInfon.RUIDO)]})
    assert balance.asientos == ()
    assert balance.conciliados == 0


def _ausente(termino, **kwargs):
    return _infon(termino, **kwargs).model_copy(update={"polaridad": Polaridad.AUSENTE})


def test_una_ausencia_sin_recoger_no_es_un_problema_pasado_por_alto():
    balance = conciliar(
        {"t1": [_infon("Fiebre", acto="aceptado"), _ausente("Ictericia")]}
    )

    assert balance.solo_holonmed == 0
    assert balance.por_termino == {}
    assert balance.tasa_pasados_por_alto == 0.0
    # No desaparece ni se disfraza de pendiente: se revisó y consta.
    assert balance.ausencias_sin_recoger == 1
    assert balance.pendientes == 0
    assert balance.conciliados == 2
    asiento = balance.asientos[1]
    assert asiento.situacion is Situacion.AUSENCIA_SIN_RECOGER
    assert asiento.polaridad is Polaridad.AUSENTE
    assert not asiento.es_discrepancia


def test_las_ausencias_ratificadas_no_diluyen_la_tasa():
    balance = conciliar(
        {
            "t1": [
                _infon("Fiebre", acto="aceptado"),
                _infon("Hipopotasemia"),
                _ausente("Ictericia", acto="aceptado"),
                _ausente("Ascitis", estado=EstadoInfon.ALERTA, acto="aceptado"),
            ]
        }
    )

    assert balance.tasa_pasados_por_alto == 0.5
    assert balance.ausencias_conciliadas == 2
    # Al índice la ausencia sí lo mide.
    assert balance.tasa_sin_cobertura == 0.25


def test_con_solo_ausencias_revisadas_no_hay_tasa_de_problemas():
    balance = conciliar({"t1": [_ausente("Ictericia", acto="aceptado")]})

    assert balance.tasa_pasados_por_alto is None
    assert balance.tasa_sin_cobertura == 0.0


def test_una_ausencia_sin_revisar_sigue_pendiente():
    balance = conciliar({"t1": [_ausente("Ictericia")]})

    assert balance.pendientes == 1
    assert balance.ausencias_conciliadas == 0
    assert balance.conciliados == 0
