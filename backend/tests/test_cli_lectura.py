"""La lectura semiótica de la CLI.

Hasta ahora la salida de `holonmed tic` mostraba la probabilidad y los
infones y nada más: del segundo eje —el que dice si la hipótesis armoniza
con el paciente entero— no había una línea, ni del criterio contado, ni
del veto que retira un diagnóstico.

Estas funciones deciden cosas —cuál de las dos lecturas de Φ manda, si un
veto calla lo que viene detrás, qué se escribe donde un factor no
existe—, y una decisión metida dentro de un `print` no se puede probar.
Por eso devuelven líneas.
"""

import pytest
from test_acoplamiento import PROTOCOLO
from test_duda import AJENOS, infon
from test_veredicto import APENDICITIS

from holonmed.cli import (
    _lineas_acoplamiento,
    _lineas_competencia,
    _lineas_reapertura,
    _lineas_veredicto,
)
from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.core.duda import ReabridorDeIndagacion
from holonmed.core.skills import Skill
from holonmed.core.veredicto import EvaluadorDeVeredicto
from holonmed.models import CandidataAbductiva, ResultadoTic


@pytest.fixture
def medidor() -> MedidorDeAcoplamiento:
    return MedidorDeAcoplamiento()


@pytest.fixture
def ponderado() -> Skill:
    return Skill("pancreatitis", PROTOCOLO)


@pytest.fixture
def categorico() -> Skill:
    """Apendicitis: declara categorías y ni un solo likelihood ratio."""
    return Skill("apendicitis", APENDICITIS)


def texto(lineas: list[str]) -> str:
    return "\n".join(lineas)


# --- Φ ----------------------------------------------------------------


def test_la_cli_imprime_phi_con_sus_tres_factores(medidor, ponderado):
    salida = texto(_lineas_acoplamiento(medidor.medir(ponderado, [infon("Vomitos")])))

    assert "Acoplamiento (Φ)" in salida
    assert "dirección" in salida and "cobertura" in salida and "explicación" in salida
    assert "Pancreatitis aguda" in salida


def test_en_un_protocolo_categorico_no_imprime_un_cero(medidor, categorico):
    """El mismo cero que ya mintió dos veces, ahora en la consola.

    `phi` vale 0 cuando no hay vector ponderado que proyectar, y ese 0 se
    leería como INERCIA — falso sobre el caso, y sobre la mayor parte del
    índice, porque los criterios publicados declaran categorías.
    """
    acoplamiento = medidor.medir(
        categorico,
        [infon("Fiebre"), infon("Leucocitosis"), infon("Signo de Blumberg")],
    )
    salida = texto(_lineas_acoplamiento(acoplamiento))

    assert acoplamiento.phi == 0.0  # la lectura ponderada no existe
    assert "Φ): +0.0000" not in salida
    assert f"{acoplamiento.phi_categorico:+.4f}" in salida
    assert "lectura categórica" in salida
    assert "ARMONIA" in salida


def test_un_factor_que_no_existe_se_escribe_n_d_y_no_cero(medidor, ponderado):
    """Sin ninguna dimensión medida no hay ángulo: la dirección no vale 0."""
    acoplamiento = medidor.medir(ponderado, [])
    salida = texto(_lineas_acoplamiento(acoplamiento))

    assert acoplamiento.direccion is None
    assert "dirección n/d" in salida


def test_sin_acoplamiento_no_se_imprime_nada():
    assert _lineas_acoplamiento(None) == []


# --- El veto ----------------------------------------------------------


def test_el_veto_se_imprime_como_retirada_y_no_como_nivel(categorico):
    salida = texto(
        _lineas_veredicto(
            EvaluadorDeVeredicto().evaluar(
                categorico, [infon("Fiebre"), infon("Apendicectomía")]
            )
        )
    )

    assert "HIPÓTESIS RETIRADA" in salida
    assert "Apendicectomía" in salida
    assert "no es una probabilidad baja" in salida


def test_el_criterio_contado_lista_apoyos_y_banderas(categorico):
    salida = texto(
        _lineas_veredicto(
            EvaluadorDeVeredicto().evaluar(
                categorico, [infon("Fiebre"), infon("Leucocitosis")]
            )
        )
    )

    assert "Criterio publicado" in salida
    assert "+ Fiebre" in salida
    assert "apoyo(s)" in salida


# --- La duda ----------------------------------------------------------


def test_la_duda_dice_de_que_clase_es_y_que_preguntar(medidor, ponderado):
    acoplamiento = medidor.medir(ponderado, [infon("Vomitos")])
    salida = texto(_lineas_reapertura(ReabridorDeIndagacion().reabrir(acoplamiento)))

    assert "LA INDAGACIÓN SE REABRE" in salida
    assert "se resuelve indagando" in salida
    assert "Hiperlipasemia" in salida  # la pregunta más informativa


@pytest.mark.parametrize(
    ("previo", "esperado"),
    [
        (None, "no se puede decir si la creencia se rompió"),
        (0.83, "SE ROMPIÓ"),
        (0.05, "NUNCA ARRAIGÓ"),
    ],
)
def test_la_trayectoria_se_dice_en_voz_alta(medidor, ponderado, previo, esperado):
    """Los tres estados, incluido el que no hay.

    Callar el `None` dejaría al clínico suponiendo que la creencia venía
    estable, que es justo lo que no se sabe.
    """
    acoplamiento = medidor.medir(ponderado, [infon("Vomitos")])
    salida = texto(
        _lineas_reapertura(ReabridorDeIndagacion().reabrir(acoplamiento, None, previo))
    )

    assert esperado in salida


def test_sin_duda_no_se_imprime_nada(medidor, ponderado):
    """Una creencia operable no imprime una sección vacía."""
    acoplamiento = medidor.medir(
        ponderado,
        [
            infon("Hiperlipasemia"),
            infon("Hiperamilasemia"),
            infon("Dolor epigastrico"),
            infon("Vomitos"),
        ],
    )
    assert not acoplamiento.duda
    assert _lineas_reapertura(ReabridorDeIndagacion().reabrir(acoplamiento)) == []


def test_la_duda_de_explicacion_manda_a_la_abduccion(medidor, ponderado):
    """Las tres clases no se funden en «Φ bajo»."""
    acoplamiento = medidor.medir(
        ponderado, [infon("Hiperlipasemia")] + [infon(t) for t in AJENOS[:16]]
    )
    salida = texto(_lineas_reapertura(ReabridorDeIndagacion().reabrir(acoplamiento)))

    assert "deja sin explicar" in salida
    assert "sin explicar" in texto(_lineas_acoplamiento(acoplamiento))


# --- La competencia ---------------------------------------------------


def _tic_con_competencia() -> ResultadoTic:
    r = ResultadoTic(paciente_id="p", texto_original="x", skill_activa="pancreatitis")
    r.competencia = [
        CandidataAbductiva(
            skill="pancreatitis",
            clave=0.7947,
            lectura="ponderada",
            anclaje=0.98,
            admitida=True,
        ),
        CandidataAbductiva(
            skill="colecistitis",
            clave=0.8613,
            lectura="categorica",
            anclaje=0.0,
            admitida=False,
        ),
        CandidataAbductiva(
            skill="apendicitis",
            anclaje=0.87,
            vetada=True,
            motivo_veto="Apendicectomía: sin apéndice no hay apendicitis",
        ),
    ]
    return r


def test_la_competencia_muestra_las_perdedoras_con_su_motivo():
    """«Se consideró y sacó 0.25» ES la traza de auditoría."""
    tic = _tic_con_competencia()
    tic.ganadora_abductiva = "colecistitis"
    tic.triaje_coincide = False
    salida = texto(_lineas_competencia(tic))

    assert "DISCREPAN" in salida
    assert "sin anclaje" in salida
    assert "vetada" in salida
    assert "sin apéndice" in salida


def test_sin_competencia_con_la_que_comparar_no_se_dice_que_discrepan():
    """`triaje_coincide is None` no es «se equivocó»: es que nadie compitió."""
    tic = _tic_con_competencia()
    tic.triaje_coincide = None
    salida = texto(_lineas_competencia(tic))

    assert "DISCREPAN" not in salida
    assert "con la que comparar" in salida


def test_el_aviso_de_la_compuerta_se_dice_en_voz_alta():
    """Si α actúa callada, el sistema trata otra cosa sin explicar por qué."""
    tic = _tic_con_competencia()
    tic.triaje_coincide = True
    tic.ganadora_abductiva = "pancreatitis"
    tic.aviso_competencia = "colecistitis encaja mejor y su protocolo no cita"
    salida = texto(_lineas_competencia(tic))

    assert "AVISO:" in salida
    assert "no cita" in salida


def test_las_preguntas_no_se_imprimen_dos_veces(medidor, ponderado):
    """Con duda, la reapertura hereda la indagación y la dice con su porqué.

    Repetirla arriba sólo alarga la salida sin añadir nada: son las mismas
    preguntas, palabra por palabra.
    """
    acoplamiento = medidor.medir(ponderado, [infon("Vomitos")])
    reapertura = ReabridorDeIndagacion().reabrir(acoplamiento)

    con_duda = texto(_lineas_acoplamiento(acoplamiento, repite_indagacion=False))
    assert "?" not in con_duda
    assert reapertura.preguntas == acoplamiento.indagacion
    assert "Hiperlipasemia" in texto(_lineas_reapertura(reapertura))


def test_sin_duda_la_indagacion_si_se_imprime(medidor, ponderado):
    """Sin reapertura, lo que queda por mirar no lo dice nadie más."""
    acoplamiento = medidor.medir(
        ponderado, [infon("Hiperlipasemia"), infon("Hiperamilasemia")]
    )
    salida = texto(_lineas_acoplamiento(acoplamiento, repite_indagacion=True))

    assert not acoplamiento.duda
    assert "? " in salida
