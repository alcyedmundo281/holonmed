"""Propiedades del Coeficiente de Acoplamiento (Φ).

Estos tests no comprueban implementación: comprueban que la geometría
produce la semiótica que se le pide. Cada uno corresponde a una afirmación
del diseño, y si alguno cae, lo que falla es la teoría, no el código.
"""

import math

import pytest

from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.core.bayes import AntigenPresentingCell
from holonmed.core.skills import Skill
from holonmed.models import (
    EstadoDimension,
    EstadoInfon,
    Infon,
    Polaridad,
    VeredictoSemiotico,
)

PROTOCOLO = """---
titulo: Protocolo de prueba
condicion:
  nombre: Pancreatitis aguda
modelo_bayesiano:
  probabilidad_base: 0.05
  factores_riesgo:
    alcohol: 2.8
signos:
  - nombre: Hiperlipasemia
    rol: prueba_especifica
    lr: 26.6
    lr_negativo: 0.1
    fuente: JAMA Rational Clinical Examination
  - nombre: Hiperamilasemia
    rol: prueba_especifica
    lr: 12.5
    lr_negativo: 0.3
    fuente: JAMA Rational Clinical Examination
  - nombre: Dolor epigastrico
    rol: manifestacion
    lr: 2.1
    lr_negativo: 0.2
    fuente: GetTheDiagnosis.org
  - nombre: Vomitos
    rol: apoyo
    lr: 1.6
    fuente: GetTheDiagnosis.org
---

Cuerpo del protocolo.
"""

# El mismo protocolo, con los likelihood ratios desnudos: sin una sola
# fuente que los sostenga. Estructuralmente idéntico, epistémicamente vacío.
PROTOCOLO_SIN_FUENTES = PROTOCOLO.replace(
    "    fuente: JAMA Rational Clinical Examination\n", ""
).replace("    fuente: GetTheDiagnosis.org\n", "")


@pytest.fixture
def skill() -> Skill:
    return Skill("prueba", PROTOCOLO)


@pytest.fixture
def medidor() -> MedidorDeAcoplamiento:
    return MedidorDeAcoplamiento()


def infon(
    termino: str,
    presente: bool = True,
    confianza: float = 95.0,
    metodo: str = "hint_exacto",
    **extra,
) -> Infon:
    return Infon(
        texto_origen=termino,
        termino_propuesto=termino,
        termino=termino,
        polaridad=Polaridad.PRESENTE if presente else Polaridad.AUSENTE,
        estado=EstadoInfon.VALIDADO,
        confianza=confianza,
        razon_auditoria=f"[{metodo}] auditado",
        **extra,
    )


# --- Los tres polos ---------------------------------------------------


def test_caso_de_libro_tiende_a_la_armonia(medidor, skill):
    """Todos los signos del protocolo presentes: el vector real ≡ el ideal."""
    infones = [
        infon("Hiperlipasemia"),
        infon("Hiperamilasemia"),
        infon("Dolor epigastrico"),
        infon("Vomitos"),
    ]
    res = medidor.medir(skill, infones)

    assert res is not None
    assert res.coseno == pytest.approx(1.0, abs=1e-6)
    assert res.phi >= 0.60
    assert res.veredicto is VeredictoSemiotico.ARMONIA
    assert not res.duda


def test_contexto_que_contradice_tiende_a_la_desarmonia(medidor, skill):
    """Las mismas dimensiones, con el registro diciendo lo contrario.

    Es el polo Φ = −1: la hipótesis conserva intacto su orden interno y aun
    así el paciente la contradice punto por punto.
    """
    infones = [
        infon("Hiperlipasemia", presente=False),
        infon("Hiperamilasemia", presente=False),
        infon("Dolor epigastrico", presente=False),
    ]
    res = medidor.medir(skill, infones)

    assert res is not None
    assert res.coseno < -0.60
    assert res.veredicto is VeredictoSemiotico.DESARMONIA
    assert res.duda
    assert all(
        c.estado is EstadoDimension.CONTRADICE
        for c in res.componentes
        if c.infon is not None
    )


def test_hipotesis_ajena_al_caso_da_inercia(medidor, skill):
    """Φ = 0: ortogonalidad. Ni contribuye ni daña, es irrelevante."""
    res = medidor.medir(skill, [infon("Cefalea"), infon("Artralgia")])

    assert res is not None
    assert res.coseno == pytest.approx(0.0, abs=1e-9)
    assert res.veredicto is VeredictoSemiotico.INERCIA
    assert set(res.resto_no_simbolizado) == {"Cefalea", "Artralgia"}


def test_sin_evidencia_alguna_phi_es_cero_por_inercia(medidor, skill):
    """La ausencia de datos no es contradicción: es un vector nulo."""
    res = medidor.medir(skill, [])

    assert res is not None
    assert res.phi == 0.0
    assert res.veredicto is VeredictoSemiotico.INERCIA
    assert any("inercia" in t.lower() for t in res.traza)


# --- El resto no simbolizado -----------------------------------------


def test_el_resto_no_simbolizado_baja_phi_sin_castigo_ad_hoc(medidor, skill):
    """Los hallazgos no explicados abren dimensiones ortogonales.

    No hay penalización escrita en ninguna parte: la geometría sola hace
    que una hipótesis que deja media historia sin explicar se desacople.
    """
    base = [infon("Hiperlipasemia")]
    con_resto = base + [
        infon("Hematuria"),
        infon("Soplo sistolico"),
        infon("Edema de miembros inferiores"),
    ]

    solo = medidor.medir(skill, base)
    con = medidor.medir(skill, con_resto)

    assert con.coseno < solo.coseno
    assert len(con.resto_no_simbolizado) == 3
    assert any("Resto no simbolizado" in q for q in con.indagacion)


def test_una_ausencia_ajena_al_protocolo_no_es_resto(medidor, skill):
    """Documentar que algo no está es buena praxis, no fricción."""
    res = medidor.medir(skill, [infon("Hiperlipasemia"), infon("Fiebre", presente=False)])

    assert res.resto_no_simbolizado == []
    assert res.coseno == medidor.medir(skill, [infon("Hiperlipasemia")]).coseno


def test_el_diagnostico_derivado_no_cuenta_como_resto(medidor, skill):
    """El trastorno que acuña el clasificador es la hipótesis, no evidencia contra ella."""
    derivado = infon(
        "Pancreatitis aguda",
        derivado_de=["Hiperlipasemia", "Dolor epigastrico"],
        criterio="Criterios de Atlanta 2012",
    )
    res = medidor.medir(skill, [infon("Hiperlipasemia"), derivado])

    assert res.resto_no_simbolizado == []


# --- La guarda anti-pseudociencia ------------------------------------


def test_argumento_sin_fuentes_colapsa_a_irrelevante(medidor):
    """Un razonamiento internamente perfecto sobre LR inventados vale 0.

    El coseno sigue siendo 1 —la coherencia interna está intacta— y aun así
    Φ = 0: no se le declara falso, se le declara irrelevante. La
    elaboración no compra armonía.
    """
    sin_fuentes = Skill("sin_fuentes", PROTOCOLO_SIN_FUENTES)
    infones = [
        infon("Hiperlipasemia"),
        infon("Hiperamilasemia"),
        infon("Dolor epigastrico"),
        infon("Vomitos"),
    ]
    res = medidor.medir(sin_fuentes, infones)
    con_fuentes = medidor.medir(Skill("con_fuentes", PROTOCOLO), infones)

    # La coherencia interna es idéntica: mismo caso, misma geometría.
    assert res.coseno == pytest.approx(con_fuentes.coseno, abs=1e-9)
    assert res.coseno == pytest.approx(1.0, abs=1e-6)
    # Y aun así el resultado es irrelevancia, no armonía.
    assert res.anclaje == 0.0
    assert res.phi == 0.0
    assert res.veredicto is VeredictoSemiotico.INERCIA
    assert res.anclaje_detalle["fuente"] == 0.0
    assert con_fuentes.veredicto is VeredictoSemiotico.ARMONIA


def test_normalizacion_difusa_atenua_phi(medidor, skill):
    """Un término anclado a ojo pesa menos que un código revisado."""
    firme = medidor.medir(skill, [infon("Hiperlipasemia", metodo="hint_exacto")])
    flojo = medidor.medir(
        skill, [infon("Hiperlipasemia", metodo="fuzzy", confianza=62.0)]
    )

    assert flojo.anclaje < firme.anclaje
    assert flojo.phi < firme.phi
    assert flojo.coseno == pytest.approx(firme.coseno, abs=1e-9)


def test_los_infones_no_validados_no_entran_en_el_vector(medidor, skill):
    """Sólo evidencia auditada acopla. Una alerta se muestra, no se computa."""
    alerta = infon("Hiperlipasemia")
    alerta.estado = EstadoInfon.ALERTA
    res = medidor.medir(skill, [alerta])

    assert res.phi == 0.0
    assert res.veredicto is VeredictoSemiotico.INERCIA


# --- Relación con el motor bayesiano ---------------------------------


def test_phi_y_bayes_leen_el_mismo_vector(skill):
    """Σeᵢ = ln(odds posterior / odds previo).

    Ésta es la identidad que sostiene todo el diseño: Bayes lee la
    magnitud del vector de evidencia y Φ lee su dirección. Si el
    emparejamiento de los dos módulos divergiera, la identidad se rompería
    aquí antes que en ningún otro sitio.
    """
    infones = [
        infon("Hiperlipasemia"),
        infon("Dolor epigastrico"),
        infon("Hiperamilasemia", presente=False),
    ]

    inferencia = AntigenPresentingCell().calcular(
        {"edad": 50, "antecedentes": ""}, skill.para_bayes(), infones
    )
    acoplamiento = MedidorDeAcoplamiento().medir(skill, infones, inferencia)

    p_previa = inferencia.probabilidad_previa / 100
    p_final = inferencia.probabilidad_porcentaje / 100
    delta_bayes = math.log((p_final / (1 - p_final)) / (p_previa / (1 - p_previa)))

    suma_e = sum(c.observado for c in acoplamiento.componentes)
    assert suma_e == pytest.approx(delta_bayes, abs=1e-3)


def test_probabilidad_alta_con_resto_sin_explicar_no_se_declara_operable(
    medidor, skill
):
    """El caso que ningún sistema de apoyo suele mostrar.

    Una lipasa muy elevada empuja la probabilidad por encima del 50 % ella
    sola, mientras cuatro hallazgos del paciente hablan de otra cosa. La
    probabilidad no se toca —es correcta— pero la creencia no puede
    presentarse como operable.
    """
    infones = [
        infon("Hiperlipasemia"),
        infon("Hematuria"),
        infon("Soplo sistolico"),
        infon("Edema de miembros inferiores"),
        infon("Disnea paroxistica nocturna"),
    ]
    inferencia = AntigenPresentingCell().calcular(
        {"edad": 70, "antecedentes": ""}, skill.para_bayes(), infones
    )
    res = medidor.medir(skill, infones, inferencia)

    assert inferencia.probabilidad_porcentaje > 50
    assert res.phi < 0.60
    assert res.veredicto is VeredictoSemiotico.ACOPLAMIENTO_PARCIAL
    assert "resto no simbolizado" in res.cuadrante
    assert "operable" not in res.cuadrante
    assert len(res.resto_no_simbolizado) == 4


def test_una_prueba_estelar_no_compra_armonia_ilimitada(medidor, skill):
    """El resto se escala al caso, no al protocolo.

    Si el hallazgo no explicado pesara la mediana del protocolo, un LR
    enorme bastaría para tapar cualquier cantidad de historia sin
    explicar. Cada hallazgo ajeno tiene que costar tanto como los que la
    hipótesis sí explica.
    """
    solo = medidor.medir(skill, [infon("Hiperlipasemia")])
    con_dos = medidor.medir(
        skill, [infon("Hiperlipasemia"), infon("Hematuria"), infon("Soplo sistolico")]
    )
    con_seis = medidor.medir(
        skill,
        [infon("Hiperlipasemia")]
        + [infon(f"Hallazgo ajeno {n}") for n in range(6)],
    )

    assert solo.coseno > con_dos.coseno > con_seis.coseno
    assert con_seis.veredicto in {
        VeredictoSemiotico.ACOPLAMIENTO_PARCIAL,
        VeredictoSemiotico.INERCIA,
    }


@pytest.mark.parametrize(
    "phi,fragmento",
    [
        (0.85, "operable"),
        (0.40, "resto no simbolizado"),
        (0.05, "MAL ACOPLADA"),
    ],
)
def test_el_cuadrante_distingue_tres_grados_de_certeza(medidor, phi, fragmento):
    """Sobre el lado probable, Φ decide entre tratar, indagar y replantear."""
    from holonmed.models import InferenciaBayesiana

    inferencia = InferenciaBayesiana(
        diagnostico="X", probabilidad_porcentaje=80.0, probabilidad_previa=5.0
    )
    assert fragmento in medidor._cuadrante(phi, inferencia)


def test_phi_no_toca_la_probabilidad(medidor, skill):
    """Ejes independientes: medir el acoplamiento no reescribe la inferencia."""
    infones = [infon("Hiperlipasemia"), infon("Cefalea")]
    inferencia = AntigenPresentingCell().calcular(
        {"edad": 40, "antecedentes": ""}, skill.para_bayes(), infones
    )
    antes = inferencia.probabilidad_porcentaje

    medidor.medir(skill, infones, inferencia)

    assert inferencia.probabilidad_porcentaje == antes


# --- La duda como dirección ------------------------------------------


def test_lo_no_medido_baja_phi_sin_volverlo_negativo(medidor, skill):
    """Un caso a medio estudiar da armonía parcial, no desarmonía."""
    res = medidor.medir(skill, [infon("Vomitos")])

    assert 0 < res.coseno < 1
    assert res.veredicto in {
        VeredictoSemiotico.ACOPLAMIENTO_PARCIAL,
        VeredictoSemiotico.INERCIA,
    }


def test_la_indagacion_apunta_a_la_afirmacion_mas_fuerte_sin_comprobar(medidor, skill):
    """La duda es una dirección: primero, la prueba que más movería Φ."""
    res = medidor.medir(skill, [infon("Vomitos")])

    assert res.indagacion
    assert res.indagacion[0].startswith("Hiperlipasemia")


def test_el_registro_reciente_manda_sobre_el_antiguo(medidor, skill):
    """Una lipasa normal hoy no queda anulada por una alta de la semana pasada."""
    antiguo = infon("Hiperlipasemia", confianza=99.0)
    antiguo.timestamp = "2026-01-01T00:00:00+00:00"
    reciente = infon("Hiperlipasemia", presente=False, confianza=80.0)
    reciente.timestamp = "2026-06-01T00:00:00+00:00"

    res = medidor.medir(skill, [antiguo, reciente])
    lipasa = next(c for c in res.componentes if c.dimension == "Hiperlipasemia")

    assert lipasa.observado < 0
    assert lipasa.estado is EstadoDimension.CONTRADICE


# --- Contratos de borde ----------------------------------------------


def test_protocolo_sin_likelihood_ratios_no_finge_una_medida(medidor):
    """Sin LR no hay espacio donde medir: se devuelve None, no un Φ de 0."""
    vacio = Skill("vacio", "---\ntitulo: Sin modelo\n---\n\nTexto.\n")
    assert medidor.medir(vacio, [infon("Hiperlipasemia")]) is None


def test_phi_siempre_dentro_del_intervalo(medidor, skill):
    escenarios = [
        [],
        [infon("Hiperlipasemia")],
        [infon("Hiperlipasemia", presente=False)],
        [infon("Cefalea")],
        [infon("Hiperlipasemia"), infon("Hiperamilasemia", presente=False)],
    ]
    for infones in escenarios:
        res = medidor.medir(skill, infones)
        assert -1.0 <= res.phi <= 1.0
        assert -1.0 <= res.coseno <= 1.0
        assert 0.0 <= res.anclaje <= 1.0
