"""Tests del clasificador diagnóstico y de la polaridad.

Lo que se protege aquí es la distinción entre tres cosas que es fácil
confundir y peligroso mezclar:

  presente   evidencia a favor    -> LR+
  ausente    evidencia en contra  -> LR-
  sin datos  un vacío             -> se pregunta, no se asume

Confundir las dos últimas convierte un silencio en una prueba negativa, y
una prueba negativa descarta diagnósticos.
"""

import pytest

from holonmed.core.clasificacion import Clasificador, EstadoCriterio
from holonmed.core.skills import Skill
from holonmed.models import EstadoInfon, Infon, Polaridad

SKILL = """---
titulo: Protocolo de prueba
version: "1.0.0"

signos:
  - nombre: Dolor epigástrico
    codigos: { holonmed: "HM:0202" }
    rol: manifestacion
    lr: 2.1
    lr_negativo: 0.2
    fuente: Estudio de prueba
  - nombre: Hiperlipasemia (>3x)
    codigos: { holonmed: "HM:0732" }
    rol: prueba_especifica
    lr: 26.6
    lr_negativo: 0.1
    fuente: Estudio de prueba
  - nombre: Hallazgos de imagen compatibles
    codigos: { holonmed: "HM:0901" }
    rol: imagen
    lr: 9.0
    fuente: Estudio de prueba

modelo_bayesiano:
  probabilidad_base: 0.05

clasificacion:
  nombre: Criterios de prueba
  fuente: "Panel de consenso ficticio, 2026"
  requiere: 2
  criterios:
    - nombre: Dolor abdominal característico
      rol: manifestacion
      satisface_si: ["HM:0202"]
    - nombre: Enzimas más de 3 veces el límite
      rol: prueba_especifica
      satisface_si: ["HM:0732"]
    - nombre: Hallazgos de imagen compatibles
      rol: imagen
      satisface_si: ["HM:0901"]
  produce:
    termino: Pancreatitis aguda
    codigos: { holonmed: "HM:1002" }
    semantica: trastorno
---

# PROTOCOLO DE PRUEBA
"""


@pytest.fixture
def skill():
    return Skill("prueba", SKILL)


def infon(
    termino,
    codigo,
    polaridad=Polaridad.PRESENTE,
    estado=EstadoInfon.VALIDADO,
    confianza=90.0,
):
    return Infon(
        texto_origen="cita",
        termino_propuesto=termino,
        termino=termino,
        codigo=codigo,
        sistema="holonmed",
        polaridad=polaridad,
        estado=estado,
        confianza=confianza,
    )


# --- Cumplimiento de criterios ----------------------------------------


def test_dos_de_tres_acuna_el_trastorno(skill):
    resultado = Clasificador().evaluar(
        skill,
        [
            infon("Dolor epigástrico", "HM:0202"),
            infon("Hiperlipasemia (>3x)", "HM:0732"),
        ],
    )
    assert resultado.cumple
    assert resultado.satisfechos == 2
    assert resultado.trastorno is not None
    assert resultado.trastorno.termino == "Pancreatitis aguda"
    assert resultado.trastorno.codigo == "HM:1002"


def test_un_solo_criterio_no_basta(skill):
    resultado = Clasificador().evaluar(skill, [infon("Dolor epigástrico", "HM:0202")])
    assert not resultado.cumple
    assert resultado.trastorno is None


def test_el_trastorno_deriva_de_los_hallazgos_que_lo_sostienen(skill):
    """Su procedencia no es una cita de la nota sino la evidencia que lo
    satisface. Es lo que permite desplegarlo y ver por qué existe."""
    resultado = Clasificador().evaluar(
        skill,
        [
            infon("Dolor epigástrico", "HM:0202"),
            infon("Hiperlipasemia (>3x)", "HM:0732"),
        ],
    )
    assert set(resultado.trastorno.derivado_de) == {
        "Dolor epigástrico",
        "Hiperlipasemia (>3x)",
    }
    assert resultado.trastorno.criterio == "Criterios de prueba"
    assert "Panel de consenso ficticio" in resultado.trastorno.razon_auditoria


def test_el_trastorno_no_es_mas_firme_que_su_evidencia_mas_floja(skill):
    """Un diagnóstico no puede tener más confianza que el hallazgo peor
    sostenido que lo apoya, por mucho que venga con criterios y cita."""
    resultado = Clasificador().evaluar(
        skill,
        [
            infon("Dolor epigástrico", "HM:0202", confianza=95.0),
            infon("Hiperlipasemia (>3x)", "HM:0732", confianza=61.0),
        ],
    )
    assert resultado.trastorno.confianza == 61.0


def test_un_hallazgo_en_alerta_no_puede_acunar_un_diagnostico(skill):
    """ALERTA significa que la auditoría no lo confirmó. No sirve de
    criterio, aunque el concepto exista."""
    resultado = Clasificador().evaluar(
        skill,
        [
            infon("Dolor epigástrico", "HM:0202"),
            infon("Hiperlipasemia (>3x)", "HM:0732", estado=EstadoInfon.ALERTA),
        ],
    )
    assert resultado.satisfechos == 1
    assert not resultado.cumple


def test_un_protocolo_sin_criterios_no_inventa_ninguno():
    sin = Skill("sin", "---\ntitulo: Sin criterios\n---\n\n# Cuerpo\n")
    assert Clasificador().evaluar(sin, []) is None


# --- La distinción que importa: ausente vs. sin datos ------------------


def test_una_ausencia_documentada_no_es_lo_mismo_que_un_vacio(skill):
    resultado = Clasificador().evaluar(
        skill,
        [
            infon("Dolor epigástrico", "HM:0202"),
            # Se buscó y no está: evidencia en contra.
            infon("Hiperlipasemia (>3x)", "HM:0732", polaridad=Polaridad.AUSENTE),
            # De la imagen no consta nada.
        ],
    )
    estados = {e.criterio.rol: e.estado for e in resultado.evaluados}
    assert estados["manifestacion"] is EstadoCriterio.SATISFECHO
    assert estados["prueba_especifica"] is EstadoCriterio.DESCARTADO
    assert estados["imagen"] is EstadoCriterio.SIN_DATOS


def test_solo_los_vacios_generan_pregunta(skill):
    """Lo descartado no se vuelve a pedir: ya se miró."""
    resultado = Clasificador().evaluar(
        skill,
        [
            infon("Dolor epigástrico", "HM:0202"),
            infon("Hiperlipasemia (>3x)", "HM:0732", polaridad=Polaridad.AUSENTE),
        ],
    )
    vacios = resultado.vacios
    assert len(vacios) == 1
    assert vacios[0].rol == "imagen"
    assert "imagen" in vacios[0].sugerencia.lower()


def test_sin_ningun_dato_se_piden_todos_los_criterios(skill):
    resultado = Clasificador().evaluar(skill, [])
    assert resultado.satisfechos == 0
    assert len(resultado.vacios) == 3
    assert resultado.alcanzable  # todavía podría cumplirse


def test_si_ya_cumple_no_pide_mas_pruebas(skill):
    """Pedir confirmación adicional cuando los criterios ya se cumplen es
    sobrediagnóstico, no rigor."""
    resultado = Clasificador().evaluar(
        skill,
        [
            infon("Dolor epigástrico", "HM:0202"),
            infon("Hiperlipasemia (>3x)", "HM:0732"),
        ],
    )
    assert resultado.cumple
    assert resultado.vacios == []


def test_deja_de_ser_alcanzable_cuando_se_descartan_demasiados(skill):
    resultado = Clasificador().evaluar(
        skill,
        [
            infon("Dolor epigástrico", "HM:0202", polaridad=Polaridad.AUSENTE),
            infon("Hiperlipasemia (>3x)", "HM:0732", polaridad=Polaridad.AUSENTE),
        ],
    )
    assert not resultado.cumple
    assert not resultado.alcanzable  # sólo queda 1 posible y hacen falta 2


# --- Polaridad en el modelo -------------------------------------------


def test_confirma_y_descarta_son_excluyentes():
    presente = infon("Fiebre", "HM:0101")
    ausente = infon("Fiebre", "HM:0101", polaridad=Polaridad.AUSENTE)
    assert presente.confirma and not presente.descarta
    assert ausente.descarta and not ausente.confirma


def test_un_infon_no_validado_ni_confirma_ni_descarta():
    for polaridad in (Polaridad.PRESENTE, Polaridad.AUSENTE):
        i = infon("Fiebre", "HM:0101", polaridad=polaridad, estado=EstadoInfon.ALERTA)
        assert not i.confirma
        assert not i.descarta
