"""Tests del holon de fondo y de su impresión.

Dos cosas se comprueban por encima de todo: que ningún infón se pierda al
sintetizar, y que una nota disparada por volumen **diga que la pidió el
tamaño**. Lo segundo es la mitad del valor de la distinción.
"""

from holonmed.core.sintesis import (
    Motivo,
    decidir,
    sintetizar,
)
from holonmed.models import EstadoInfon, Infon


def _infon(termino, procedencia="objetivo", texto="", linaje=None):
    return Infon(
        texto_origen=texto or termino,
        termino_propuesto=termino.lower(),
        termino=termino,
        procedencia=procedencia,
        linaje_clinico=linaje,
        estado=EstadoInfon.VALIDADO,
    )


def test_el_fondo_organiza_por_problema_en_el_orden_de_weed():
    """Primero lo que el paciente cuenta, después lo que alguien comprobó.

    Invertirlo hace que el dato objetivo tiña el relato, que es contra lo
    que Weed ordena la nota.
    """
    fondo = sintetizar(
        [
            _infon("Dolor epigástrico", "subjetivo", "refiere dolor desde ayer"),
            _infon("Hiperlipasemia", "objetivo", "lipasa 900"),
        ],
        problemas=["Dolor epigástrico", "Hiperlipasemia"],
    )

    dolor = fondo.bloques[0]
    assert dolor.subjetivo == ("refiere dolor desde ayer",)
    assert dolor.objetivo == ()
    assert fondo.bloques[1].objetivo == ("lipasa 900",)


def test_un_infon_cuelga_del_problema_que_es_su_padre():
    """Se empareja por término y por linaje, no adivinando del texto."""
    fondo = sintetizar(
        [_infon("Fiebre alta", linaje="Fiebre")],
        problemas=["Fiebre"],
    )
    assert fondo.bloques[0].objetivo == ("Fiebre alta",)
    assert fondo.al_dia


def test_lo_que_no_cae_bajo_ningun_problema_no_se_descarta():
    """Lo que no esté en el fondo no llegará nunca al médico.

    Perderlo en silencio sería la peor forma del error aquí, porque el fondo
    es justo lo que alimenta la nota impresa.
    """
    fondo = sintetizar([_infon("Hipopotasemia")], problemas=["Fiebre"])

    assert fondo.sin_sintetizar == ("Hipopotasemia",)
    assert not fondo.al_dia


def test_el_fondo_no_lleva_fecha_ni_firma():
    """Afirma el estado AHORA, y se reescribe. No fecha nada del paciente."""
    fondo = sintetizar([], problemas=[], hasta_tic="t7")

    # Lo único temporal es hasta dónde incorporó, que es un sello sobre sí
    # mismo y no sobre el enfermo.
    assert fondo.hasta_tic == "t7"
    assert not hasattr(fondo, "firmado_por")


def test_un_problema_nuevo_dispara_la_impresion():
    decision = decidir(problemas_antes=["Fiebre"], problemas_ahora=["Fiebre", "Disnea"])

    assert decision.imprime
    assert decision.motivos == (Motivo.PROBLEMA_NUEVO,)
    assert "«Disnea»" in decision.razon
    assert decision.la_pidio_el_paciente


def test_un_problema_resuelto_tambien_dispara():
    decision = decidir(problemas_antes=["Fiebre", "Disnea"], problemas_ahora=["Fiebre"])
    assert decision.motivos == (Motivo.PROBLEMA_RESUELTO,)
    assert "se resolvió" in decision.razon


def test_varios_motivos_no_se_colapsan_en_uno():
    """No es lo mismo «apareció un problema» que «apareció Y otro se promovió»."""
    decision = decidir(
        problemas_antes=["Fiebre"],
        problemas_ahora=["Fiebre", "Disnea"],
        promovidos=["Fiebre"],
        dudas=["Neumonía"],
    )
    assert decision.motivos == (Motivo.PROBLEMA_NUEVO, Motivo.PROMOCION, Motivo.DUDA)


def test_sin_cambios_no_se_imprime():
    decision = decidir(problemas_antes=["Fiebre"], problemas_ahora=["Fiebre"])

    assert not decision.imprime
    assert "sigue al día" in decision.razon


def test_el_volumen_dispara_y_la_nota_dice_que_la_pidio_el_tamano():
    """Una síntesis nacida de un buffer lleno no fecha nada del paciente.

    Presentarla como si lo hiciera sería la ficción que Weed denuncia en la
    nota escrita el domingo por la mañana.
    """
    decision = decidir(
        problemas_antes=["Fiebre"],
        problemas_ahora=["Fiebre"],
        infones_sin_imprimir=40,
        umbral_volumen=30,
    )

    assert decision.imprime
    assert decision.motivos == (Motivo.VOLUMEN,)
    assert "la pidió el tamaño y no el paciente" in decision.razon
    assert not decision.la_pidio_el_paciente


def test_el_volumen_no_habla_cuando_hay_motivo_clinico():
    """Añadir «y el buffer estaba lleno» a un motivo clínico sería ruido."""
    decision = decidir(
        problemas_antes=[],
        problemas_ahora=["Disnea"],
        infones_sin_imprimir=99,
        umbral_volumen=30,
    )
    assert Motivo.VOLUMEN not in decision.motivos


def test_sin_umbral_la_valvula_esta_desactivada():
    """Un umbral inventado imprimiría notas que no fechan nada.

    Elegir el número es una decisión clínica que este módulo no puede tomar,
    así que el defecto es no disparar nunca por volumen.
    """
    decision = decidir(
        problemas_antes=["Fiebre"],
        problemas_ahora=["Fiebre"],
        infones_sin_imprimir=10_000,
    )
    assert not decision.imprime
