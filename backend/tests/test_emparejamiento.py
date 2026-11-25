"""El emparejamiento término ↔ signo, que es un parámetro de seguridad.

Lo comparten Bayes, el veredicto declarado, la promoción y Φ. Aquí se fija qué
NO puede heredar un likelihood ratio y que los cuatro lo apliquen igual.
Todo el texto es sintético.
"""

from pathlib import Path

import pytest

from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.core.bayes import AntigenPresentingCell, emparejar_termino
from holonmed.core.promocion import EvaluadorDePromocion
from holonmed.core.skills import Skill
from holonmed.core.veredicto import EvaluadorDeVeredicto
from holonmed.models import EstadoInfon, Infon, Polaridad

SKILLS = Path(__file__).resolve().parents[1] / "skills"
GENERICO = "Dolor torácico"
ESPECIFICO = "Dolor torácico irradiado a ambos brazos"


def infon(termino, presente=True, confianza=80.0, codigo=None, timestamp=None):
    extra = {"timestamp": timestamp} if timestamp else {}
    return Infon(
        texto_origen="…",
        termino_propuesto=termino,
        termino=termino,
        polaridad=Polaridad.PRESENTE if presente else Polaridad.AUSENTE,
        estado=EstadoInfon.VALIDADO,
        confianza=confianza,
        codigo=codigo,
        sistema="holonmed" if codigo else None,
        **extra,
    )


@pytest.fixture
def sca():
    ruta = SKILLS / "sindrome_coronario_agudo.md"
    return Skill(ruta.stem, ruta.read_text(encoding="utf-8"))


def bayes(skill, infones):
    return AntigenPresentingCell().calcular({}, skill.para_bayes(), infones)


# --- La función ------------------------------------------------------------


@pytest.mark.parametrize(
    "termino, clave",
    [
        # Un genérico no hereda lo de un específico.
        (GENERICO, ESPECIFICO),
        ("Dolor", "Dolor torácico posicional"),
        ("Adenopatías", "Adenopatías referidas por el paciente"),
        ("Síncope", "Primer síncope a los 35 años o más"),
        ("Hiperlipasemia", "Hiperlipasemia (>3x)"),
        # Unas letras compartidas no son una relación entre hallazgos.
        ("Tos", "Vómitos"),
        ("Vómitos", "Tos"),
        ("Cuestionario AUDIT-C positivo", "Cuestionario AUDIT"),
        # Contener el nombre de un hallazgo no es ser un caso de él.
        ("Sensación de frío previa al síncope", "Síncope"),
        ("Antecedente de disnea", "Disnea"),
        ("Sin disnea", "Disnea"),
        # Nada no es todo.
        ("", "Disnea"),
        ("   ", "Disnea"),
    ],
)
def test_lo_que_no_empareja(termino, clave):
    assert emparejar_termino(termino, {clave.lower(): 1}) is None


@pytest.mark.parametrize(
    "termino, clave",
    [
        ("Disnea", "Disnea"),
        ("  DISNEA ", "Disnea"),
        ("Odinofagia intensa", "Odinofagia"),
        ("Hiperlipasemia (>3x), confirmada", "Hiperlipasemia (>3x)"),
    ],
)
def test_lo_que_si_empareja(termino, clave):
    assert emparejar_termino(termino, {clave.lower(): 1}) == clave.lower()


def test_gana_la_clave_mas_especifica():
    mapa = {"dolor": 1, "dolor torácico": 2}
    assert emparejar_termino("Dolor torácico opresivo", mapa) == "dolor torácico"


# --- El caso reportado -----------------------------------------------------


def test_el_dolor_toracico_generico_no_hereda_el_lr_de_la_irradiacion(sca):
    solo = bayes(sca, [infon(GENERICO, codigo="HM:0206")])
    assert solo.evidencia_utilizada == []
    assert solo.probabilidad_porcentaje == 10.0


def test_la_misma_observacion_no_cuenta_dos_veces_en_el_caso_reportado(sca):
    resultado = bayes(
        sca,
        [
            infon(GENERICO, codigo="HM:0206"),
            infon(ESPECIFICO, codigo="HM:3014"),
            infon("Descenso del segmento ST", codigo="HM:3015"),
        ],
    )
    assert len(resultado.evidencia_utilizada) == 2
    # odds 1/9 × 2.6 × 5.3
    assert resultado.probabilidad_porcentaje == 60.49


# --- Un signo, una vez -----------------------------------------------------


def test_bayes_cuenta_un_signo_una_sola_vez_y_lo_dice(sca):
    una = bayes(sca, [infon(ESPECIFICO)])
    dos = bayes(sca, [infon(ESPECIFICO), infon(ESPECIFICO + " desde hace 40 minutos")])
    assert dos.probabilidad_porcentaje == una.probabilidad_porcentaje
    assert len(dos.evidencia_utilizada) == 1
    assert any("se cuenta UNA vez" in linea for linea in dos.traza_logica)


def test_ante_una_contradiccion_bayes_toma_la_mas_reciente_como_phi():
    skill = Skill("pancreatitis", PROTOCOLO)
    infones = [
        infon("Lipasa alta", timestamp="2026-01-01T00:00:00+00:00", confianza=99.0),
        infon("Lipasa alta", presente=False, timestamp="2026-01-02T00:00:00+00:00"),
    ]
    resultado = bayes(skill, infones)
    assert len(resultado.evidencia_utilizada) == 1
    assert "[ausente]" in resultado.evidencia_utilizada[0]
    assert any("contradic" in linea for linea in resultado.traza_logica)


# --- Código: identidad declarada, no aproximación --------------------------

PROTOCOLO = """---
titulo: Protocolo sintético
condicion: { nombre: Hipótesis sintética }
modelo_bayesiano: { probabilidad_base: 0.2 }
signos:
  - nombre: Lipasa alta
    codigos: { holonmed: "HM:T1" }
    rol: prueba_especifica
    lr: 10.0
    lr_negativo: 0.1
    fuente: sintética
  - nombre: Hiperlipasemia (>3x)
    codigos: { holonmed: "HM:T2" }
    rol: prueba_especifica
    lr: 20.0
    fuente: sintética
---
cuerpo
"""


def test_el_codigo_declarado_empareja_aunque_el_nombre_difiera():
    """El vocabulario llama «Hiperlipasemia» a HM:0732 y el protocolo
    «Hiperlipasemia (>3x)». Lo que los une es el código, no las letras."""
    skill = Skill("p", PROTOCOLO)
    assert bayes(skill, [infon("Hiperlipasemia")]).evidencia_utilizada == []
    con_codigo = bayes(skill, [infon("Hiperlipasemia", codigo="HM:T2")])
    assert len(con_codigo.evidencia_utilizada) == 1


def test_un_codigo_que_nombra_dos_signos_no_empareja_ninguno():
    skill = Skill("p", PROTOCOLO.replace("HM:T1", "HM:T2"))
    resultado = bayes(skill, [infon("Otro nombre", codigo="HM:T2")])
    assert resultado.evidencia_utilizada == []


def test_el_protocolo_real_de_pancreatitis_conserva_la_lipasa():
    ruta = SKILLS / "acute_pancreatitis.md"
    skill = Skill(ruta.stem, ruta.read_text(encoding="utf-8"))
    resultado = bayes(skill, [infon("Hiperlipasemia", codigo="HM:0732")])
    assert len(resultado.evidencia_utilizada) == 1


# --- La ausencia de lo específico no es ausencia de lo genérico ------------


def test_la_ausencia_de_un_especifico_no_aplica_el_lr_negativo_del_generico():
    skill = Skill("p", PROTOCOLO)
    resultado = bayes(skill, [infon("Lipasa alta en orina", presente=False)])
    assert resultado.evidencia_utilizada == []


# --- Los cuatro consumidores -----------------------------------------------

CONSUMIDORES = """---
titulo: Protocolo sintético
condicion: { nombre: Hipótesis sintética }
modelo_bayesiano: { probabilidad_base: 0.2 }
nucleo:
  requiere: [Dolor torácico irradiado a ambos brazos]
balance:
  probable: { apoyos_minimos: 1, banderas_maximas: 0 }
promocion:
  exige: { manifestacion: 1 }
signos:
  - nombre: Dolor torácico irradiado a ambos brazos
    rol: manifestacion
    lr: 2.6
    fuente: sintética
---
cuerpo
"""


def test_veredicto_ni_el_signo_ni_el_nucleo_los_satisface_un_generico():
    """El núcleo llamaba al emparejador al revés —el término exigido contra lo
    observado— y con él «Dolor torácico» satisfacía el requisito específico."""
    skill = Skill("p", CONSUMIDORES)
    veredicto = EvaluadorDeVeredicto().evaluar(skill, [infon(GENERICO)])
    assert veredicto.apoyos == []
    assert veredicto.nivel is None
    assert any("Núcleo no documentado" in t for t in veredicto.traza)


def test_veredicto_el_especifico_si_satisface_signo_y_nucleo():
    skill = Skill("p", CONSUMIDORES)
    veredicto = EvaluadorDeVeredicto().evaluar(skill, [infon(ESPECIFICO)])
    assert veredicto.nivel == "probable"


def test_promocion_no_la_completa_un_generico():
    skill = Skill("p", CONSUMIDORES)
    veredicto = EvaluadorDePromocion().evaluar(skill, [infon(GENERICO)])
    assert veredicto.cumplido == {"manifestacion": 0}
    assert not veredicto.promueve


def test_acoplamiento_el_generico_no_puebla_la_dimension_especifica():
    skill = Skill("p", CONSUMIDORES)
    medida = MedidorDeAcoplamiento().medir(skill, [infon(GENERICO)])
    assert medida.peso_evidencia_declarado == 0.0
    assert medida.cobertura == 0.0
    assert medida.cobertura_categorica == 0.0


EXCLUIDO_DEL_FILTRO = """---
titulo: Protocolo sintético
condicion: { nombre: Hipótesis sintética }
modelo_bayesiano: { probabilidad_base: 0.2 }
promocion:
  exige: { manifestacion: 1 }
signos:
  - nombre: Dolor torácico
    rol: manifestacion
    lr: 3.0
    fuente: sintética
  - nombre: Dolor torácico posicional
    rol: manifestacion
    efecto: evidencia
---
cuerpo
"""


def test_nombrar_exacto_un_signo_filtrado_no_cae_en_otro():
    """Cada consumidor mira un subconjunto (con LR, o sólo `apoya`). Se resuelve
    contra TODO lo declarado y después se filtra."""
    skill = Skill("p", EXCLUIDO_DEL_FILTRO)
    hallazgo = [infon("Dolor torácico posicional")]
    assert bayes(skill, hallazgo).evidencia_utilizada == []
    assert EvaluadorDePromocion().evaluar(skill, hallazgo).cumplido == {
        "manifestacion": 0
    }
    assert MedidorDeAcoplamiento().medir(skill, hallazgo).peso_evidencia_declarado == 0.0
