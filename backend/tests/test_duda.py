"""La duda leída: de qué clase es y qué reabre.

`Acoplamiento.duda` existía y nadie la consumía. Estos tests fijan lo que
hace el módulo que la lee: que distingue las tres clases de duda, que las
lee de la lectura que el protocolo permite, y que no inventa una vuelta a
la abducción donde no la hay.
"""

import pytest
from test_acoplamiento import PROTOCOLO
from test_veredicto import APENDICITIS

from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.core.duda import ReabridorDeIndagacion
from holonmed.core.skills import Skill
from holonmed.models import (
    CausaDeLaDuda,
    EstadoInfon,
    Infon,
    Polaridad,
    TrayectoriaDeLaCreencia,
)

# Hallazgos que ninguno de los dos protocolos declara: sirven para subir
# el resto no simbolizado sin tocar ninguna dimensión.
AJENOS = [
    "Hematuria", "Cefalea", "Disuria", "Prurito", "Acufenos", "Epistaxis",
    "Artralgia", "Mialgia", "Tinnitus", "Vertigo", "Astenia", "Anosmia",
    "Alopecia", "Xerostomia", "Bradicardia", "Hipoacusia",
]

# Un protocolo calibrado para que la escala de comparación importe: con
# un signo a favor y otro documentado en contra, y dos dimensiones
# grandes sin mirar, la dirección queda en 0.2533 y la cobertura en
# 0.2108. Cuál de las dos lastra más depende de en qué escala se
# comparen, y ésa es la pregunta que este protocolo existe para hacer.
PROTOCOLO_DE_ESCALA = """---
titulo: Protocolo de escala
signos:
  - nombre: Signo A
    lr: 2.0
    lr_negativo: 0.5
    fuente: y
  - nombre: Signo B
    lr: 1.5
    lr_negativo: 0.5
    fuente: y
  - nombre: Signo C
    lr: 3.0
    fuente: y
  - nombre: Signo D
    lr: 3.0
    fuente: y
---

Cuerpo.
"""


@pytest.fixture
def skill() -> Skill:
    return Skill("pancreatitis", PROTOCOLO)


@pytest.fixture
def categorico() -> Skill:
    """Apendicitis: declara categorías y ni un solo likelihood ratio."""
    return Skill("apendicitis", APENDICITIS)


@pytest.fixture
def medidor() -> MedidorDeAcoplamiento:
    return MedidorDeAcoplamiento()


@pytest.fixture
def reabridor() -> ReabridorDeIndagacion:
    return ReabridorDeIndagacion()


def infon(termino: str, presente: bool = True) -> Infon:
    return Infon(
        texto_origen=termino,
        termino_propuesto=termino,
        termino=termino,
        polaridad=Polaridad.PRESENTE if presente else Polaridad.AUSENTE,
        estado=EstadoInfon.VALIDADO,
        confianza=95.0,
        razon_auditoria="[hint_exacto] auditado",
    )


def ajenos(n: int) -> list[Infon]:
    return [infon(t) for t in AJENOS[:n]]


# --- Cuándo NO se reabre nada ----------------------------------------


def test_una_creencia_operable_no_reabre_nada(medidor, reabridor, skill):
    """Sin duda no hay reapertura, y no un objeto vacío que interrogar."""
    acoplamiento = medidor.medir(
        skill,
        [infon("Hiperlipasemia"), infon("Hiperamilasemia"),
         infon("Dolor epigastrico"), infon("Vomitos")],
    )

    assert not acoplamiento.duda
    assert reabridor.reabrir(acoplamiento) is None


def test_sin_acoplamiento_no_hay_duda_que_leer(reabridor):
    """Φ no medible no es Φ bajo: no se puede preguntar si la creencia falla."""
    assert reabridor.reabrir(None) is None


# --- Las tres clases de duda -----------------------------------------


def test_lo_mirado_disiente_es_duda_de_direccion(medidor, reabridor, skill):
    """La lipasa documentada como ausente contradice lo que el protocolo exige.

    Es la duda que no se arregla mirando más: cada dato que confirme lo ya
    visto la hunde más. La dirección se compara con su signo y no en valor
    absoluto, precisamente para que una dirección negativa —el registro
    contradiciendo— gane a cualquier cobertura o explicación, que viven
    en [0, 1].
    """
    acoplamiento = medidor.medir(skill, [infon("Hiperlipasemia", presente=False)])
    reapertura = reabridor.reabrir(acoplamiento)

    assert reapertura is not None
    assert reapertura.causa is CausaDeLaDuda.DIRECCION
    assert acoplamiento.direccion < 0
    assert "contradice" in reapertura.motivo


def test_casi_nada_puesto_a_prueba_es_duda_de_cobertura(medidor, reabridor, skill):
    """Un solo vómito —LR 1.6— sobre un protocolo de cuatro dimensiones.

    Lo mirado concuerda (dirección 1.00) y no hay nada sin explicar
    (explicación 1.00): lo único que falla es que no se ha mirado casi
    nada. Ésta es la duda que `indagacion` sabe resolver.
    """
    acoplamiento = medidor.medir(skill, [infon("Vomitos")])
    reapertura = reabridor.reabrir(acoplamiento)

    assert reapertura is not None
    assert reapertura.causa is CausaDeLaDuda.COBERTURA
    assert acoplamiento.direccion == pytest.approx(1.0)
    assert acoplamiento.explicacion == pytest.approx(1.0)
    assert "indagando" in reapertura.motivo


def test_no_explicar_al_paciente_es_duda_de_explicacion(medidor, reabridor, skill):
    """La lipasa consta y concuerda, y hay dieciséis hallazgos sin explicar.

    Es el polo que Φ define como Φ = 0 —argumento internamente ordenado
    pero aislado— y la forma que toma el sesgo de anclaje: la hipótesis
    puede ser cierta y no ser la pregunta. Se resuelve volviendo a la
    abducción, no mirando más dentro de esta hipótesis.
    """
    acoplamiento = medidor.medir(skill, [infon("Hiperlipasemia")] + ajenos(16))
    reapertura = reabridor.reabrir(acoplamiento)

    assert reapertura is not None
    assert reapertura.causa is CausaDeLaDuda.EXPLICACION
    # La dirección no falla y la cobertura tampoco es lo peor: lo que
    # lastra es el lado del paciente.
    assert acoplamiento.direccion == pytest.approx(1.0)
    assert acoplamiento.explicacion < acoplamiento.cobertura


def test_las_tres_clases_no_se_confunden(medidor, reabridor, skill):
    """Los tres casos dan tres causas distintas, y ése es el punto.

    Si el módulo devolviera siempre la misma causa los tres tests de
    arriba seguirían pasando de uno en uno. Se afirma aquí que las tres
    son distintas entre sí.
    """
    causas = {
        reabridor.reabrir(medidor.medir(skill, caso)).causa
        for caso in (
            [infon("Hiperlipasemia", presente=False)],
            [infon("Vomitos")],
            [infon("Hiperlipasemia")] + ajenos(16),
        )
    }
    assert causas == {
        CausaDeLaDuda.DIRECCION,
        CausaDeLaDuda.COBERTURA,
        CausaDeLaDuda.EXPLICACION,
    }


# --- La lectura categórica -------------------------------------------


def test_la_causa_se_lee_del_categorico_cuando_no_hay_ni_un_LR(
    medidor, reabridor, categorico
):
    """En un protocolo de categorías los factores ponderados no existen.

    `direccion`, `cobertura` y `explicacion` valen None porque no hay
    vector ponderado, y un factor None no compite. Si el módulo leyera
    sólo esos tres, la duda de la mayoría del índice se quedaría sin
    causa que nombrar.
    """
    acoplamiento = medidor.medir(
        categorico,
        [infon("Fiebre"), infon("Leucocitosis", presente=False),
         infon("Signo de Blumberg", presente=False)],
    )
    reapertura = reabridor.reabrir(acoplamiento)

    assert acoplamiento.cobertura is None       # la ponderada no existe
    assert acoplamiento.direccion_categorica is not None
    assert reapertura is not None
    assert reapertura.causa is not None
    assert any("Lectura categórica" in t for t in reapertura.traza)


# --- La vuelta a la abducción ----------------------------------------


def test_la_alternativa_sale_de_la_competencia(medidor, reabridor, skill):
    """La vuelta a la abducción no se recalcula: ya corrió en la etapa 3b."""
    acoplamiento = medidor.medir(skill, [infon("Vomitos")])
    reapertura = reabridor.reabrir(acoplamiento, ganadora_abductiva="Colecistitis")

    assert reapertura.alternativa == "Colecistitis"
    assert any("Colecistitis" in t for t in reapertura.traza)


def test_no_hay_alternativa_si_la_abduccion_prefiere_la_misma(
    medidor, reabridor, skill
):
    """Proponer la hipótesis que ya se estaba usando no es volver a nada."""
    acoplamiento = medidor.medir(skill, [infon("Vomitos")])
    reapertura = reabridor.reabrir(
        acoplamiento, ganadora_abductiva=acoplamiento.hipotesis
    )

    assert reapertura.alternativa is None


def test_sin_competencia_la_reapertura_sigue_diciendo_hacia_donde(
    medidor, reabridor, skill
):
    """Sin candidata alternativa la duda no se queda muda: quedan las preguntas.

    Es la mitad del diseño que no depende del grafo: aunque no haya otra
    hipótesis que ofrecer, `indagacion` ya sabe cuál es la afirmación más
    fuerte de ésta que nadie ha comprobado.
    """
    acoplamiento = medidor.medir(skill, [infon("Vomitos")])
    reapertura = reabridor.reabrir(acoplamiento)

    assert reapertura.alternativa is None
    assert reapertura.preguntas == acoplamiento.indagacion
    assert reapertura.preguntas


def test_la_reapertura_informa_el_phi_que_disparo(medidor, reabridor, skill):
    """El número que se publica es el mismo que decidió que había duda."""
    acoplamiento = medidor.medir(skill, [infon("Vomitos")])
    reapertura = reabridor.reabrir(acoplamiento)

    assert reapertura.phi == pytest.approx(acoplamiento.phi_legible, abs=1e-4)
    assert reapertura.hipotesis == acoplamiento.hipotesis


def test_los_factores_se_comparan_en_la_escala_en_que_entran_al_producto(
    medidor, reabridor
):
    """La cobertura y la explicación entran bajo raíz, y la dirección no.

    `cos = dirección · √cobertura · √explicación`, así que preguntar cuál
    lastra más sólo significa algo si cada uno se mide por lo que
    multiplica. Comparar los tres números crudos es comparar una fracción
    contra su propia raíz.

    Este caso lo distingue: dirección 0.2533 y cobertura 0.2108. En crudo
    la cobertura parece la peor; en la escala del producto tira 0.4591 y
    la dirección 0.2533, de modo que la peor es la dirección. Y no es un
    tecnicismo: son dos consejos clínicos opuestos —«mira más» frente a
    «esto no encaja, cambia de hipótesis»—.
    """
    protocolo = Skill("escala", PROTOCOLO_DE_ESCALA)
    acoplamiento = medidor.medir(
        protocolo, [infon("Signo A"), infon("Signo B", presente=False)]
    )
    reapertura = reabridor.reabrir(acoplamiento)

    assert acoplamiento.duda
    # En crudo la cobertura es el número menor…
    assert acoplamiento.cobertura < acoplamiento.direccion
    # …y aun así la causa es la dirección, porque √0.2108 > 0.2533.
    assert reapertura.causa is CausaDeLaDuda.DIRECCION


# --- dΦ/dt: la trayectoria de la creencia -----------------------------


def test_sin_medida_anterior_no_hay_trayectoria(medidor, reabridor, skill):
    """`None`, y no un tercer valor que dijera «estable».

    Es la misma distinción que `medir` hace al devolver None en vez de un
    Φ de 0: decir «estable» sobre un primer tic afirmaría una trayectoria
    que nadie ha medido.
    """
    reapertura = reabridor.reabrir(medidor.medir(skill, [infon("Vomitos")]))

    assert reapertura.trayectoria is None
    assert reapertura.phi_previo is None
    assert any("No hay medida anterior" in t for t in reapertura.traza)


def test_una_creencia_que_funcionaba_y_cayo_se_rompio(medidor, reabridor, skill):
    """La duda peirceana propiamente dicha: la experiencia desbarató la regla.

    Lo que la disparó está en los hallazgos nuevos, y ésa es la
    diferencia práctica: hay algo que mirar en este tic.
    """
    reapertura = reabridor.reabrir(
        medidor.medir(skill, [infon("Vomitos")]), phi_previo=0.83
    )

    assert reapertura.trayectoria is TrayectoriaDeLaCreencia.SE_ROMPIO
    assert reapertura.phi_previo == pytest.approx(0.83)
    assert any("se rompió" in t for t in reapertura.traza)


def test_una_hipotesis_que_ya_estaba_baja_nunca_arraigo(medidor, reabridor, skill):
    """No se ha roto nada: la indagación no se reabre, sigue abierta."""
    reapertura = reabridor.reabrir(
        medidor.medir(skill, [infon("Vomitos")]), phi_previo=0.05
    )

    assert reapertura.trayectoria is TrayectoriaDeLaCreencia.NUNCA_ARRAIGO
    assert any("nunca llegó a sostenerse" in t for t in reapertura.traza)


def test_la_trayectoria_corta_por_el_mismo_umbral_que_la_duda(medidor, reabridor, skill):
    """Justo encima y justo debajo del mínimo, que es donde vive la distinción.

    El estado que se quiere nombrar es «cruzó la raya», así que tiene que
    ser la misma raya. Con dos umbrales distintos habría una franja en la
    que una creencia se rompe sin haber estado nunca por encima.
    """
    from holonmed.core.acoplamiento import UMBRAL_ACOPLAMIENTO

    acoplamiento = medidor.medir(skill, [infon("Vomitos")])
    justo_encima = reabridor.reabrir(acoplamiento, phi_previo=UMBRAL_ACOPLAMIENTO)
    justo_debajo = reabridor.reabrir(
        acoplamiento, phi_previo=UMBRAL_ACOPLAMIENTO - 0.0001
    )

    assert justo_encima.trayectoria is TrayectoriaDeLaCreencia.SE_ROMPIO
    assert justo_debajo.trayectoria is TrayectoriaDeLaCreencia.NUNCA_ARRAIGO


def test_la_trayectoria_no_cambia_la_causa_ni_las_preguntas(medidor, reabridor, skill):
    """dΦ/dt informa; no reinterpreta lo que el tic de hoy mide.

    La causa sale de los tres factores de este acoplamiento y las
    preguntas de su indagación. Que la creencia venga de arriba o de
    abajo añade una lectura, no altera las otras — igual que la cobertura
    se informa y no se aplica.
    """
    acoplamiento = medidor.medir(skill, [infon("Vomitos")])
    sin_historia = reabridor.reabrir(acoplamiento)
    rota = reabridor.reabrir(acoplamiento, phi_previo=0.83)

    assert rota.causa is sin_historia.causa
    assert rota.preguntas == sin_historia.preguntas
    assert rota.phi == sin_historia.phi
