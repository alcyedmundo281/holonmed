"""La tupla: cuándo un hallazgo deja de ser problema y pasa a ser diagnóstico.

Pruebas de propiedad, no de implementación: afirman lo que la regla promete
—que los tres elementos tienen que estar y que sin ellos el hallazgo se queda
en la lista de problemas— sin mirar cómo se cuenta por dentro.
"""

import pytest

from holonmed.core.promocion import EvaluadorDePromocion
from holonmed.core.skills import Skill
from holonmed.models import EstadoInfon, InferenciaBayesiana, Infon, Polaridad

FARINGITIS = """---
titulo: Faringitis estreptocócica
condicion:
  nombre: Faringitis estreptocócica
promocion:
  exige: {manifestacion: 1, prueba_sensible: 1, prueba_especifica: 1}
  umbral_postest: 0.90
  motivo: >-
    política del servicio: por debajo del 90% se sigue estudiando en vez de
    tratar, porque el tratamiento no es inocuo y el cuadro no es urgente
  fuente: "Centor RM et al"
signos:
  - nombre: Odinofagia
    rol: manifestacion
  - nombre: Adenopatía cervical anterior dolorosa
    rol: prueba_sensible
    lr_negativo: 0.6
    fuente: "Ebell MH et al, JAMA 2000"
  - nombre: Exudado amigdalino
    rol: prueba_especifica
    lr: 3.4
    fuente: "Ebell MH et al, JAMA 2000"
---

PROTOCOLO
"""


@pytest.fixture
def skill():
    return Skill("faringitis", FARINGITIS)


def infon(termino, polaridad=Polaridad.PRESENTE, estado=EstadoInfon.VALIDADO):
    return Infon(
        texto_origen=termino,
        termino_propuesto=termino,
        termino=termino,
        polaridad=polaridad,
        estado=estado,
        confianza=95.0,
        razon_auditoria="[lexico] emparejado",
    )


def inferencia(porcentaje):
    return InferenciaBayesiana(
        diagnostico="Faringitis estreptocócica",
        probabilidad_porcentaje=porcentaje,
        probabilidad_previa=0.1,
    )


TUPLA = ["Odinofagia", "Adenopatía cervical anterior dolorosa", "Exudado amigdalino"]


# --- La tupla ---------------------------------------------------------------


def test_con_los_tres_elementos_y_el_umbral_promueve(skill):
    r = EvaluadorDePromocion().evaluar(skill, [infon(t) for t in TUPLA], inferencia(94))
    assert r.promueve
    assert r.cumplido == {
        "manifestacion": 1,
        "prueba_sensible": 1,
        "prueba_especifica": 1,
    }


@pytest.mark.parametrize("falta", TUPLA)
def test_sin_uno_de_los_tres_el_hallazgo_se_queda_como_problema(skill, falta):
    """La regla clínica del principio: la explicación única supera a la
    múltiple, y una tupla incompleta no promueve aunque la probabilidad sobre."""
    presentes = [infon(t) for t in TUPLA if t != falta]
    r = EvaluadorDePromocion().evaluar(skill, presentes, inferencia(99))

    assert not r.promueve
    assert r.se_queda_como_problema
    assert r.faltan, "no promueve y no dice qué falta"
    assert any("queda como PROBLEMA" in t for t in r.traza)


def test_una_prueba_sensible_NEGATIVA_impide_promover(skill):
    """El corazón clínico de la tupla: SnNOut usado como compuerta.

    Exigir la sensible «en positivo» no es redundante con exigir la
    específica — significa que una sensible documentada NEGATIVA bloquea la
    promoción, por alta que sea la probabilidad. Sin esta regla, la
    específica sola bastaría y la sensible sería decorativa.
    """
    infones = [
        infon("Odinofagia"),
        infon("Adenopatía cervical anterior dolorosa", Polaridad.AUSENTE),
        infon("Exudado amigdalino"),
    ]
    r = EvaluadorDePromocion().evaluar(skill, infones, inferencia(99))

    assert not r.promueve
    assert r.faltan == {"prueba_sensible": 1}


def test_una_ausencia_documentada_satisface_si_el_signo_dispara_por_ausencia():
    """«Positiva» es la polaridad que sostiene la hipótesis, no «presente»."""
    skill = Skill(
        "x",
        """---
titulo: X
promocion:
  exige: {manifestacion: 1}
signos:
  - nombre: Dolor al caminar
    rol: manifestacion
    dispara_si: ausente
---

P
""",
    )
    r = EvaluadorDePromocion().evaluar(
        skill, [infon("Dolor al caminar", Polaridad.AUSENTE)]
    )
    assert r.promueve


# --- El umbral, con sus tres estados ----------------------------------------


def test_por_debajo_del_umbral_no_promueve_y_dice_que_es_por_el_umbral(skill):
    r = EvaluadorDePromocion().evaluar(skill, [infon(t) for t in TUPLA], inferencia(71))
    assert not r.promueve
    assert not r.faltan, "la tupla estaba completa: el motivo es el umbral"
    assert r.umbral_cumplido is False


def test_sin_probabilidad_el_umbral_no_se_declara_incumplido(skill):
    """`None` y no `False`: no es que la evidencia se quedara corta, es que
    no hay probabilidad con la que comparar.

    La misma distinción que `SIN_MEDIR` en Φ y `triaje_coincide` a NULL en el
    tic — «no es ausencia, es vacío»—, y se rompe igual si alguien la colapsa.
    """
    r = EvaluadorDePromocion().evaluar(skill, [infon(t) for t in TUPLA], None)

    assert r.umbral_cumplido is None
    assert not r.promueve, "sin probabilidad no se promueve, pero no por incumplir"
    assert any("sin probabilidad" in t for t in r.traza)


def test_sin_umbral_declarado_basta_la_tupla():
    skill = Skill(
        "x",
        """---
titulo: X
promocion:
  exige: {manifestacion: 1}
signos:
  - nombre: Odinofagia
    rol: manifestacion
---

P
""",
    )
    r = EvaluadorDePromocion().evaluar(skill, [infon("Odinofagia")], None)
    assert r.promueve
    assert r.umbral_cumplido is None


# --- Qué evidencia cuenta ---------------------------------------------------


def test_solo_cuenta_la_evidencia_validada(skill):
    """Un hallazgo en ALERTA se le muestra al clínico y no promueve nada."""
    infones = [infon(t, estado=EstadoInfon.ALERTA) for t in TUPLA]
    r = EvaluadorDePromocion().evaluar(skill, infones, inferencia(99))
    assert not r.promueve
    assert r.cumplido == {
        "manifestacion": 0,
        "prueba_sensible": 0,
        "prueba_especifica": 0,
    }


def test_un_signo_cuenta_una_vez_aunque_lo_toquen_dos_infones(skill):
    """La misma regla que Φ y el veredicto declarado."""
    infones = [infon("Odinofagia"), infon("Odinofagia intensa")]
    r = EvaluadorDePromocion().evaluar(skill, infones, inferencia(99))
    assert r.cumplido["manifestacion"] == 1


# --- Que no haya regla no es que la regla falle -----------------------------


def test_un_protocolo_sin_promocion_devuelve_None():
    """None dice «nadie ha declarado qué haría falta»; un veredicto que no
    promueve dice «la tupla no se completó». Son cosas distintas."""
    skill = Skill("x", "---\ntitulo: X\nsignos:\n  - nombre: Fiebre\n---\n\nP\n")
    assert EvaluadorDePromocion().evaluar(skill, [infon("Fiebre")]) is None


# --- El esquema se denuncia a sí mismo --------------------------------------


def test_un_rol_desconocido_en_la_tupla_se_denuncia():
    """Exigir un rol que nadie puede satisfacer haría la promoción imposible
    sin decir por qué. Lista blanca, como `efecto` y `dispara_si`."""
    skill = Skill(
        "x",
        """---
titulo: X
promocion:
  exige: {prueba_magica: 1}
signos:
  - nombre: Fiebre
---

P
""",
    )
    assert any("prueba_magica" in p for p in skill.problemas())
    assert "prueba_magica" not in skill.promocion.exige


def test_un_umbral_sin_motivo_se_denuncia():
    """Cuánta certeza exigir antes de actuar es una POLÍTICA, y ninguna
    revista la publica: no puede llevar cita, así que lleva motivo.

    Es el precedente de `sostiene: mecanismo` en el índice, que exige `motivo`
    justamente porque no hay PMID que decir que un paciente sin apéndice no
    puede tener apendicitis.
    """
    skill = Skill(
        "x",
        """---
titulo: X
promocion:
  umbral_postest: 0.9
signos:
  - nombre: Fiebre
---

P
""",
    )
    assert any("sin `motivo`" in p for p in skill.problemas())


def test_un_umbral_fuera_de_rango_no_se_acepta():
    skill = Skill(
        "x",
        """---
titulo: X
promocion:
  umbral_postest: 90
  motivo: se quiso escribir 0.90
signos:
  - nombre: Fiebre
---

P
""",
    )
    assert skill.promocion.umbral_postest is None
    assert any("fuera de (0, 1]" in p for p in skill.problemas())
