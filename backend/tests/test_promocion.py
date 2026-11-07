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


# --- Ciclo 12: La tupla como control de flujo -------------------------------


FARINGITIS_CON_CODIGOS = """---
titulo: Faringitis estreptocócica
condicion:
  nombre: Faringitis estreptocócica
  prevalencia: 0.15
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
    lr: 2.0
    codigos: {snomed: "162397003"}
  - nombre: Adenopatía cervical anterior dolorosa
    rol: prueba_sensible
    lr: 2.5
    lr_negativo: 0.6
    fuente: "Ebell MH et al, JAMA 2000"
    codigos: {snomed: "30746006"}
  - nombre: Exudado amigdalino
    rol: prueba_especifica
    lr: 3.4
    fuente: "Ebell MH et al, JAMA 2000"
    codigos: {snomed: "40095002", loinc: "6557-3"}
---

PROTOCOLO
"""


def test_sensible_negativa_manda_a_la_abduccion_y_no_propone_especifica():
    """SnNOut como control de flujo: con la prueba sensible negativa se
    descarta esa línea, no se pide la específica y se vuelve a la abducción."""
    skill = Skill("faringitis", FARINGITIS_CON_CODIGOS)
    infones = [
        infon("Odinofagia"),
        infon("Adenopatía cervical anterior dolorosa", Polaridad.AUSENTE),
    ]
    r = EvaluadorDePromocion().evaluar(skill, infones, inferencia(40))

    assert not r.promueve
    assert r.vuelve_a_abduccion is True
    assert r.sensible_negativa == ["Adenopatía cervical anterior dolorosa"]
    assert r.propuestas == []
    assert any("vuelve a la abducción" in t for t in r.traza)


def test_sensible_negativa_bloquea_aunque_otra_sensible_sea_positiva():
    """Si un protocolo declara dos pruebas sensibles y exige 1, que una dé
    positiva no salva la línea si otra prueba sensible documentada dio negativa."""
    skill = Skill(
        "tromboembolismo",
        """---
titulo: Tromboembolismo pulmonar
promocion:
  exige: {manifestacion: 1, prueba_sensible: 1, prueba_especifica: 1}
signos:
  - nombre: Disnea súbita
    rol: manifestacion
  - nombre: Taquicardia sinusal
    rol: prueba_sensible
  - nombre: Dímero D elevado
    rol: prueba_sensible
  - nombre: Defecto de repleción en angio-TC pulmonar
    rol: prueba_especifica
    codigos: {loinc: "30621-7"}
---

P
""",
    )
    infones = [
        infon("Disnea súbita"),
        infon("Taquicardia sinusal", Polaridad.PRESENTE),
        infon("Dímero D elevado", Polaridad.AUSENTE),
        infon("Defecto de repleción en angio-TC pulmonar", Polaridad.PRESENTE),
    ]
    r = EvaluadorDePromocion().evaluar(skill, infones)

    assert not r.promueve
    assert r.vuelve_a_abduccion is True
    assert r.sensible_negativa == ["Dímero D elevado"]
    assert r.propuestas == []


def test_sensible_positiva_sin_especifica_propone_la_especifica_por_la_compuerta():
    """Con la sensible positiva y sin específica medida, se propone como
    borrador de orden con `solicitante = promocion` y código LOINC preferido."""
    skill = Skill("faringitis", FARINGITIS_CON_CODIGOS)
    infones = [
        infon("Odinofagia"),
        infon("Adenopatía cervical anterior dolorosa", Polaridad.PRESENTE),
    ]
    r = EvaluadorDePromocion().evaluar(skill, infones, inferencia(60))

    assert not r.promueve
    assert r.vuelve_a_abduccion is False
    assert len(r.propuestas) == 1

    propuesta = r.propuestas[0]
    assert propuesta.termino == "Exudado amigdalino"
    assert propuesta.sistema == "snomed"
    assert propuesta.codigo == "40095002"
    assert propuesta.rol == "prueba_especifica"
    assert propuesta.solicitante == "promocion"
    assert "Adenopatía cervical anterior dolorosa" in propuesta.motivo
    assert any("se propone pedir" in t for t in r.traza)


def test_especifica_ya_medida_en_negativo_no_se_vuelve_a_proponer():
    """Si la prueba específica ya se midió y salió negativa, falta satisfacerla,
    pero no se vuelve a proponer pedir una prueba que ya consta en el tic."""
    skill = Skill("faringitis", FARINGITIS_CON_CODIGOS)
    infones = [
        infon("Odinofagia"),
        infon("Adenopatía cervical anterior dolorosa", Polaridad.PRESENTE),
        infon("Exudado amigdalino", Polaridad.AUSENTE),
    ]
    r = EvaluadorDePromocion().evaluar(skill, infones, inferencia(35))

    assert not r.promueve
    assert r.faltan == {"prueba_especifica": 1}
    assert r.propuestas == []


def test_hallazgo_serendipico_no_cuenta_en_la_tupla_ni_dispara_propuesta():
    """Igual que en el Ciclo 10: un hallazgo marcado con `abre_problema=True`
    abre una línea nueva y no cuenta como evidencia de la hipótesis activa."""
    skill = Skill("faringitis", FARINGITIS_CON_CODIGOS)
    serendipico = infon("Adenopatía cervical anterior dolorosa")
    serendipico.abre_problema = True

    r = EvaluadorDePromocion().evaluar(
        skill, [infon("Odinofagia"), serendipico], inferencia(60)
    )
    assert r.cumplido["prueba_sensible"] == 0
    assert r.propuestas == []


def test_las_propuestas_pasan_por_la_compuerta_proponer_autorizar_y_persisten(tmp_path):
    """La promoción propone borradores (`OrdenPropuesta` con `Solicitante.PROMOCION`)
    y jamás crea una `Orden` sin firma humana (`prescriptor`)."""
    from holonmed.core.promocion import a_propuestas_orden
    from holonmed.db.store import Database
    from holonmed.facturacion.modelos import Solicitante
    from holonmed.facturacion.repositorio import OrdenRepo

    skill = Skill("faringitis", FARINGITIS_CON_CODIGOS)
    veredicto = EvaluadorDePromocion().evaluar(
        skill,
        [
            infon("Odinofagia"),
            infon("Adenopatía cervical anterior dolorosa", Polaridad.PRESENTE),
        ],
        inferencia(60),
    )

    db = Database(tmp_path / "ordenes.db")
    repo = OrdenRepo(db)

    borradores = a_propuestas_orden(veredicto)
    assert len(borradores) == 1
    assert borradores[0].solicitante is Solicitante.PROMOCION
    # Evaluar y proponer NO escribe ninguna orden en la base de datos:
    assert repo.listar("pac-1") == []

    # Con firma humana nombrada se convierte en Orden y conserva solicitante y motivo:
    orden = borradores[0].a_orden(paciente_id="pac-1", prescriptor="Dra. Vega")
    creada = repo.crear(orden)
    assert creada is not None

    leidas = repo.listar("pac-1")
    assert len(leidas) == 1
    assert leidas[0].solicitante is Solicitante.PROMOCION
    assert leidas[0].prescriptor == "Dra. Vega"
    assert "Adenopatía cervical anterior dolorosa" in leidas[0].motivo


@pytest.mark.asyncio
async def test_pipeline_y_tic_repo_persisten_la_promocion_extremo_a_extremo(tmp_path):
    """El pipeline evalúa la tupla en la etapa 9, la vuelca en `ResultadoTic.promocion`
    y `TicRepo` la persiste y la reconstruye desde SQLite."""
    from test_pipeline import IndexFalso, LLMFalso

    from holonmed.config import Settings
    from holonmed.core.pipeline import CrystallizationPipeline
    from holonmed.core.skills import SkillManager
    from holonmed.core.validator import OntologyValidator
    from holonmed.core.verifier import ClinicalVerifier
    from holonmed.db.store import Database, GraphRepo, TicRepo
    from holonmed.models import HolonPaciente

    (tmp_path / "faringitis.md").write_text(FARINGITIS_CON_CODIGOS, encoding="utf-8")
    settings = Settings(skills_dir=tmp_path, docs_dir=tmp_path / "docs")

    llm = LLMFalso(
        extraccion={
            "resumen": "Odinofagia y adenopatía cervical dolorosa.",
            "infones": [
                {
                    "texto_origen": "dolor al tragar",
                    "termino_clinico": "Odinofagia",
                },
                {
                    "texto_origen": "ganglios cervicales dolorosos",
                    "termino_clinico": "Adenopatía cervical anterior dolorosa",
                },
            ],
        }
    )
    index = IndexFalso(score=95.0, termino="Odinofagia", codigo="162397003", exacto=False)
    pipeline = CrystallizationPipeline(
        llm=llm,
        skills=SkillManager(settings),
        validador=OntologyValidator(index, llm, settings),
        verificador=ClinicalVerifier(llm, settings),
        settings=settings,
    )

    paciente = HolonPaciente(paciente_id="pac-sintetico-1", nombre="Paciente Sintético")
    resultado = await pipeline.ejecutar(
        "Paciente con dolor al tragar y ganglios cervicales dolorosos.",
        paciente,
        skill_forzada="faringitis",
    )

    assert resultado.promocion is not None
    assert resultado.promocion.promueve is False
    assert resultado.promocion.vuelve_a_abduccion is False
    assert resultado.promocion.terminos["prueba_sensible"] == [
        "Adenopatía cervical anterior dolorosa"
    ]
    assert len(resultado.promocion.propuestas) == 1
    assert resultado.promocion.propuestas[0].termino == "Exudado amigdalino"
    assert resultado.promocion.propuestas[0].solicitante == "promocion"

    db = Database(tmp_path / "holonmed.db")
    tics = TicRepo(db, GraphRepo(db))
    tic_id = tics.guardar(resultado)
    assert tic_id is not None

    guardado = tics.tic_completo(tic_id)
    assert guardado is not None
    assert guardado["promocion"] is not None
    assert guardado["promocion"]["promueve"] is False
    assert guardado["promocion"]["propuestas"][0]["termino"] == "Exudado amigdalino"
    assert guardado["promocion"]["propuestas"][0]["solicitante"] == "promocion"
