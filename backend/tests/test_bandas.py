"""Pruebas del Ciclo 11 — Las bandas: el valor deja de ser binario.

Verifica el contrato acordado con `medsemiotics-db`:
1. Lectura `disjunto`: intervalos semiabiertos `[desde, hasta)`, sin solapar,
   y huecos reales (como HEART 4–6) que nunca se interpolan.
2. Lectura `acumulativo`: cortes anidados de un solo lado (`≥ 10%`, `≥ 20%`,
   `≥ 40%`), donde aplica únicamente el más estricto que el valor satisface.
3. El mismo analito en dos protocolos distintos empuja las dos hipótesis en
   sentidos opuestos sin ningún «rango normal» global.
4. Eje `umbral_condicion`: gradúa la definición de la condición y rechaza
   seleccionar tramo por el valor del paciente.
5. Tramos sin límites numéricos (criterios compuestos en prosa o estratos de
   `poblacion`) y discrepancias de unidad se informan en la traza y nunca se
   aplican ni se descartan en silencio.
6. Validación determinista en `Skill.problemas()`.
"""

import pytest

from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.core.bayes import AntigenPresentingCell
from holonmed.core.skills import Skill
from holonmed.models import EstadoDimension, EstadoInfon, Infon, Polaridad

PROTOCOLO_HIPERKALEMIA = """---
titulo: Hiperkalemia sintética
condicion:
  nombre: Hiperkalemia
  codigos: { holonmed: "HM:9001" }
modelo_bayesiano:
  probabilidad_base: 0.20
  factores_riesgo: {}
signos:
  - nombre: Potasio sérico
    codigos: { holonmed: "HM:0760" }
    rol: prueba_especifica
    graduacion:
      parametro: Potasio sérico
      unidad: mEq/L
      lectura: disjunto
    tramos:
      - umbral: "potasio < 3.5 mEq/L"
        hasta: 3.5
        lr: 0.05
        fuente: "Serie sintética A 2024"
      - umbral: "potasio 5.5 a 6.0 mEq/L"
        desde: 5.5
        hasta: 6.0
        lr: 3.1
        fuente: "Serie sintética A 2024"
      - umbral: "potasio ≥ 6.0 mEq/L"
        desde: 6.0
        lr: 9.4
        fuente: "Serie sintética A 2024"
---

# PROTOCOLO
"""

PROTOCOLO_HIPOKALEMIA = """---
titulo: Hipokalemia sintética
condicion:
  nombre: Hipokalemia
  codigos: { holonmed: "HM:9002" }
modelo_bayesiano:
  probabilidad_base: 0.20
  factores_riesgo: {}
signos:
  - nombre: Potasio sérico
    codigos: { holonmed: "HM:0760" }
    rol: prueba_especifica
    graduacion:
      parametro: Potasio sérico
      unidad: mEq/L
      lectura: disjunto
    tramos:
      - umbral: "potasio < 3.0 mEq/L"
        hasta: 3.0
        lr: 8.5
        fuente: "Serie sintética B 2024"
      - umbral: "potasio 3.0 a 3.5 mEq/L"
        desde: 3.0
        hasta: 3.5
        lr: 2.8
        fuente: "Serie sintética B 2024"
      - umbral: "potasio ≥ 5.5 mEq/L"
        desde: 5.5
        lr: 0.08
        fuente: "Serie sintética B 2024"
---

# PROTOCOLO
"""

PROTOCOLO_MONONUCLEOSIS_ACUMULATIVO = """---
titulo: Mononucleosis infecciosa sintética
condicion:
  nombre: Mononucleosis infecciosa
  codigos: { holonmed: "HM:6003" }
modelo_bayesiano:
  probabilidad_base: 0.10
  factores_riesgo: {}
signos:
  - nombre: Linfocitosis atípica
    codigos: { holonmed: "HM:3004" }
    rol: prueba_especifica
    graduacion:
      parametro: Linfocitos atípicos
      unidad: "%"
      lectura: acumulativo
    tramos:
      - umbral: "linfocitos atípicos ≥ 10%"
        desde: 10
        lr_positivo: 11.4
        fuente: "Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266."
      - umbral: "linfocitos atípicos ≥ 20%"
        desde: 20
        lr_positivo: 26.0
        fuente: "Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266."
      - umbral: "linfocitos atípicos ≥ 40%"
        desde: 40
        lr_positivo: 50.0
        fuente: "Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266."
      - umbral: "linfocitos > 50% y atípicos > 10%"
        lr_positivo: 54.0
        fuente: "Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266."
---

# PROTOCOLO
"""


def _infon(
    termino: str,
    valor: float | None = None,
    unidad: str | None = None,
    poblacion: str | None = None,
    polaridad: Polaridad = Polaridad.PRESENTE,
) -> Infon:
    return Infon(
        texto_origen=f"{termino}: {valor or ''}",
        termino_propuesto=termino,
        termino=termino,
        polaridad=polaridad,
        valor=valor,
        unidad=unidad,
        poblacion=poblacion,
        estado=EstadoInfon.VALIDADO,
        confianza=95.0,
        score_ontologico=100.0,
        score_logico=90.0,
        razon_auditoria="[hint_exacto] ok",
    )


def test_distintos_valores_producen_lr_distintos_y_los_extremos_son_semiabiertos():
    """`[desde, hasta)` incluye `desde` y excluye `hasta`: 6.0 entra en el
    segundo tramo (`≥ 6.0`), nunca en `[5.5, 6.0)`."""
    skill = Skill("hiperkalemia", PROTOCOLO_HIPERKALEMIA)
    assert skill.problemas() == []

    apc = AntigenPresentingCell()
    inf_56 = apc.calcular(
        {}, skill.para_bayes(), [_infon("Potasio sérico", 5.6, "mEq/L")]
    )
    inf_60 = apc.calcular(
        {}, skill.para_bayes(), [_infon("Potasio sérico", 6.0, "mEq/L")]
    )

    assert inf_56 is not None and inf_60 is not None
    assert any("LR 3.1" in e for e in inf_56.evidencia_utilizada)
    assert any("LR 9.4" in e for e in inf_60.evidencia_utilizada)
    assert inf_60.probabilidad_porcentaje > inf_56.probabilidad_porcentaje


def test_el_mismo_analito_empuja_dos_hipotesis_en_sentidos_opuestos():
    """Un potasio de 5.8 mEq/L confirma hiperkalemia y contradice hipokalemia
    sin que ninguna necesite una tabla global de rango normal."""
    hiper = Skill("hiperkalemia", PROTOCOLO_HIPERKALEMIA)
    hipo = Skill("hipokalemia", PROTOCOLO_HIPOKALEMIA)
    hallazgo = [_infon("Potasio sérico", 5.8, "mEq/L")]

    apc = AntigenPresentingCell()
    medidor = MedidorDeAcoplamiento()

    res_hiper = apc.calcular({}, hiper.para_bayes(), hallazgo)
    res_hipo = apc.calcular({}, hipo.para_bayes(), hallazgo)
    acop_hiper = medidor.medir(hiper, hallazgo, res_hiper)
    acop_hipo = medidor.medir(hipo, hallazgo, res_hipo)

    assert res_hiper is not None and res_hipo is not None
    assert res_hiper.probabilidad_porcentaje > res_hiper.probabilidad_previa
    assert res_hipo.probabilidad_porcentaje < res_hipo.probabilidad_previa

    assert acop_hiper is not None and acop_hipo is not None
    assert acop_hiper.phi > 0
    assert acop_hipo.phi < 0
    assert acop_hiper.phi_categorico is not None and acop_hiper.phi_categorico > 0
    assert acop_hipo.phi_categorico is not None and acop_hipo.phi_categorico < 0


def test_un_valor_en_un_hueco_no_aplica_ninguna_banda_y_lo_dice_en_la_traza():
    """Entre 3.5 y 5.5 la hipótesis no declara cociente: 4.2 no interpola ni
    mueve la probabilidad, y la traza deja constancia."""
    hiper = Skill("hiperkalemia", PROTOCOLO_HIPERKALEMIA)
    hallazgo = [_infon("Potasio sérico", 4.2, "mEq/L")]

    res = AntigenPresentingCell().calcular({}, hiper.para_bayes(), hallazgo)
    acop = MedidorDeAcoplamiento().medir(hiper, hallazgo, res)

    assert res is not None
    assert res.evidencia_utilizada == []
    assert res.probabilidad_porcentaje == res.probabilidad_previa
    assert any("4.2 mEq/L no cae en ningún tramo" in t for t in res.traza_logica)

    assert acop is not None
    assert acop.componentes[0].estado is EstadoDimension.SIN_MEDIR
    assert acop.phi == 0.0
    assert any("4.2 mEq/L no cae en ningún tramo" in t for t in acop.traza)


def test_lectura_acumulativa_aplica_solo_el_corte_mas_estricto_y_avisa_del_compuesto():
    """En `HM:6003`, 25% supera `≥ 10%` (LR 11.4) y `≥ 20%` (LR 26), pero no
    `≥ 40%` (LR 50). Se aplica únicamente 26 (no 11.4, ni 11.4 × 26), y el
    cuarto tramo compuesto sin `desde` se declara no evaluado en la traza."""
    skill = Skill("mono", PROTOCOLO_MONONUCLEOSIS_ACUMULATIVO)
    assert skill.problemas() == []

    hallazgo = [_infon("Linfocitosis atípica", 25.0, "%")]
    res = AntigenPresentingCell().calcular({}, skill.para_bayes(), hallazgo)

    assert res is not None
    assert len(res.evidencia_utilizada) == 1
    assert "LR 26.0" in res.evidencia_utilizada[0]
    assert "linfocitos atípicos ≥ 20%" in res.evidencia_utilizada[0]
    assert any(
        "sin límites numéricos" in t and "linfocitos > 50%" in t for t in res.traza_logica
    )


def test_umbral_condicion_rechaza_evaluar_el_valor_del_paciente():
    """En el aneurisma de aorta (`HM:6006`), los tramos gradúan el tamaño del
    aneurisma buscado (`umbral_condicion`), no la cifra del paciente."""
    contenido = """---
titulo: AAA
modelo_bayesiano:
  probabilidad_base: 0.05
signos:
  - nombre: Pulsación aórtica ensanchada
    codigos: { holonmed: "HM:3012" }
    graduacion:
      parametro: Diámetro aórtico máximo
      unidad: cm
      lectura: acumulativo
    tramos:
      - umbral_condicion: "aneurisma ≥ 3.0 cm"
        desde: 3.0
        lr: 12.0
        fuente: "Lederle 1999"
      - umbral_condicion: "aneurisma ≥ 4.0 cm"
        desde: 4.0
        lr: 15.6
        fuente: "Lederle 1999"
---
# PROTOCOLO
"""
    skill = Skill("aaa", contenido)
    assert skill.problemas() == []

    hallazgo = [_infon("Pulsación aórtica ensanchada", 4.5, "cm")]
    res = AntigenPresentingCell().calcular({}, skill.para_bayes(), hallazgo)

    assert res is not None
    assert res.evidencia_utilizada == []
    assert any("umbral_condicion" in t for t in res.traza_logica)


def test_tramo_con_poblacion_exige_conocer_la_poblacion_del_paciente():
    """Si un tramo lleva `poblacion` y el hallazgo no dice en qué población
    está el paciente, el motor se detiene y lo explica en la traza."""
    contenido = """---
titulo: TVP
modelo_bayesiano:
  probabilidad_base: 0.15
signos:
  - nombre: Dímero D elevado
    codigos: { holonmed: "HM:0687" }
    tramos:
      - poblacion: "sospecha baja, ensayo alta sensibilidad"
        lr_negativo: 0.10
        fuente: "Goodacre 2005"
      - poblacion: "sospecha moderada, ensayo alta sensibilidad"
        lr_negativo: 0.05
        fuente: "Goodacre 2005"
---
# PROTOCOLO
"""
    skill = Skill("tvp", contenido)
    assert skill.problemas() == []

    sin_pob = [_infon("Dímero D elevado", polaridad=Polaridad.AUSENTE)]
    res_sin = AntigenPresentingCell().calcular({}, skill.para_bayes(), sin_pob)
    assert res_sin is not None
    assert res_sin.evidencia_utilizada == []
    assert any("estratificados por población" in t for t in res_sin.traza_logica)

    con_pob = [
        _infon(
            "Dímero D elevado",
            poblacion="sospecha moderada, ensayo alta sensibilidad",
            polaridad=Polaridad.AUSENTE,
        )
    ]
    res_con = AntigenPresentingCell().calcular({}, skill.para_bayes(), con_pob)
    assert res_con is not None
    assert len(res_con.evidencia_utilizada) == 1
    assert "LR 0.05" in res_con.evidencia_utilizada[0]


def test_unidad_incompatible_se_rechaza_en_vez_de_suponer_conversion():
    skill = Skill("hiperkalemia", PROTOCOLO_HIPERKALEMIA)
    hallazgo = [_infon("Potasio sérico", 5.8, "mg/dL")]

    res = AntigenPresentingCell().calcular({}, skill.para_bayes(), hallazgo)
    assert res is not None
    assert res.evidencia_utilizada == []
    assert any("incompatible" in t for t in res.traza_logica)


def test_unidad_ausente_se_rechaza_en_vez_de_asumir_la_del_protocolo():
    skill = Skill("hiperkalemia", PROTOCOLO_HIPERKALEMIA)
    hallazgo = [_infon("Potasio sérico", 5.8, unidad=None)]

    res = AntigenPresentingCell().calcular({}, skill.para_bayes(), hallazgo)
    assert res is not None
    assert res.evidencia_utilizada == []
    assert any("sin unidad declarada" in t for t in res.traza_logica)


def test_auditoria_de_magnitud_descarta_cifras_o_unidades_no_respaldadas_por_cita():
    from holonmed.core.pipeline import _auditar_magnitud, _terminos_autorizados

    skill = Skill("hiperkalemia", PROTOCOLO_HIPERKALEMIA)
    assert "potasio serico" in _terminos_autorizados(skill)

    ok, _ = _auditar_magnitud(
        "Potasio sérico 5.8 mEq/L",
        "Laboratorio: Potasio sérico 5.8 mEq/L",
        5.8,
        "mEq/L",
        None,
    )
    assert ok

    ok_falso_valor, razon_val = _auditar_magnitud(
        "Potasio sérico 5.6 mEq/L",
        "Laboratorio: Potasio sérico 5.6 mEq/L",
        6.5,
        "mEq/L",
        None,
    )
    assert not ok_falso_valor
    assert "6.5" in razon_val

    ok_falsa_unidad, razon_uni = _auditar_magnitud(
        "Potasio sérico 5.6",
        "Laboratorio: Potasio sérico 5.6",
        5.6,
        "mEq/L",
        None,
    )
    assert not ok_falsa_unidad
    assert "mEq/L" in razon_uni


@pytest.mark.parametrize(
    "bloque_signo, fragmento_esperado",
    [
        (
            """
  - nombre: Potasio
    codigos: { holonmed: "HM:0760" }
    graduacion: { parametro: Potasio, unidad: mEq/L }
    tramos:
      - { desde: 5.5, lr: 3.1, fuente: "Ref" }
""",
            "graduacion.lectura",
        ),
        (
            """
  - nombre: Potasio
    codigos: { holonmed: "HM:0760" }
    graduacion: { parametro: Potasio, lectura: disjunto }
    tramos:
      - { desde: 5.5, lr: 3.1, fuente: "Ref" }
""",
            "graduacion.unidad",
        ),
        (
            """
  - nombre: Potasio
    codigos: { holonmed: "HM:0760" }
    graduacion: { parametro: Potasio, unidad: mEq/L, lectura: disjunto }
    tramos:
      - { desde: 6.0, hasta: 5.5, lr: 3.1, fuente: "Ref" }
""",
            "menor que hasta",
        ),
        (
            """
  - nombre: Potasio
    codigos: { holonmed: "HM:0760" }
    graduacion: { parametro: Potasio, unidad: mEq/L, lectura: disjunto }
    tramos:
      - { desde: 5.0, hasta: 6.2, lr: 3.1, fuente: "Ref" }
      - { desde: 6.0, hasta: 7.0, lr: 9.4, fuente: "Ref" }
""",
            "se solapan",
        ),
        (
            """
  - nombre: Potasio
    codigos: { holonmed: "HM:0760" }
    graduacion: { parametro: Potasio, unidad: mEq/L, lectura: acumulativo }
    tramos:
      - { desde: 5.0, hasta: 6.0, lr: 3.1, fuente: "Ref" }
""",
            "un solo lado",
        ),
        (
            """
  - nombre: Potasio
    codigos: { holonmed: "HM:0760" }
    graduacion: { parametro: Potasio, unidad: mEq/L, lectura: acumulativo }
    tramos:
      - { umbral: "≥ 5.0", desde: 5.0, lr: 3.1, fuente: "Ref" }
      - { umbral_condicion: "≥ 6.0", desde: 6.0, lr: 9.4, fuente: "Ref" }
""",
            "mezcla 'umbral' y 'umbral_condicion'",
        ),
        (
            """
  - nombre: Potasio
    codigos: { holonmed: "HM:0760" }
    graduacion: { parametro: Potasio, unidad: mEq/L, lectura: disjunto }
    tramos:
      - { desde: 5.5, lr: 3.1 }
""",
            "sin fuente",
        ),
    ],
)
def test_problemas_detecta_invariantes_rotas_de_tramos(
    bloque_signo: str, fragmento_esperado: str
):
    skill = Skill("rota", f"---\ntitulo: Rota\nsignos:{bloque_signo}\n---\n# P\n")
    problemas = skill.problemas()
    assert any(fragmento_esperado in p for p in problemas), problemas
