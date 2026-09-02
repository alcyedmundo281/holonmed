"""Propiedades del Coeficiente de Acoplamiento (Φ).

Estos tests no comprueban implementación: comprueban que la geometría
produce la semiótica que se le pide. Cada uno corresponde a una afirmación
del diseño, y si alguno cae, lo que falla es la teoría, no el código.
"""

import inspect
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


# --- Los tres factores del coseno ------------------------------------


def test_los_tres_factores_reconstruyen_el_coseno(medidor, skill):
    """La identidad, afirmada sobre el número publicado y no sobre la cuenta.

    `cos = dirección · √cobertura · √explicación` no es una aproximación:
    es el mismo coseno escrito sin cancelar. Si alguien cambia la
    definición de un factor, el producto deja de cerrar.

    La tolerancia es 1e-3 y no 1e-4 A PROPÓSITO: los tres factores se
    exponen redondeados a cuatro decimales, así que rehacer el producto
    desde ellos arrastra hasta tres cuantos de redondeo. Apretarla dejaría
    la aserción en el filo, que ya nos pasó una vez.
    """
    escenarios = [
        [infon("Hiperlipasemia"), infon("Dolor epigastrico")],
        [infon("Hiperlipasemia"), infon("Hiperamilasemia", presente=False)],
        # con resto: es donde la identidad de dos factores se rompía
        [infon("Hiperlipasemia"), infon("Hematuria")],
        [infon("Hiperlipasemia"), infon("Hematuria"), infon("Soplo sistolico")],
    ]

    for infones in escenarios:
        res = medidor.medir(skill, infones)
        producto = res.direccion * math.sqrt(res.cobertura * res.explicacion)
        assert producto == pytest.approx(res.coseno, abs=1e-3), infones


def test_el_resto_sale_por_la_explicacion_y_nunca_por_la_cobertura(medidor, skill):
    """Los dos lados de la identidad miden cosas distintas y no se mezclan.

    La cobertura es del lado `h`: cuánto de lo que la hipótesis AFIRMA se
    ha mirado. Un hallazgo que el protocolo no contempla no es superficie
    de la hipótesis, así que no puede moverla — pero tampoco desaparece:
    cae del lado `e`, en la explicación.

    Meter el resto en el denominador de la cobertura haría que un paciente
    complejo bajara la cobertura de una hipótesis bien examinada, que es
    una afirmación falsa sobre cuánto se la ha puesto a prueba.
    """
    base = [infon("Hiperlipasemia"), infon("Dolor epigastrico")]

    solo = medidor.medir(skill, base)
    con_resto = medidor.medir(skill, base + [infon("Hematuria")])

    assert con_resto.cobertura == solo.cobertura
    assert con_resto.explicacion < solo.explicacion
    assert con_resto.direccion == solo.direccion
    assert con_resto.coseno < solo.coseno


def test_los_factores_distinguen_no_mirado_de_puesto_a_prueba(medidor, skill):
    """El coseno fundido presenta igual dos estados que piden conductas opuestas.

    Mirar poco y que nada contradiga da un coseno alto. Mirarlo todo y que
    la hipótesis aguante da otro. Partido, el primero es dirección alta con
    cobertura baja —*nada la contradice todavía*— y el segundo dirección
    alta con cobertura alta —*se ha puesto a prueba y aguanta*—.
    """
    poco_mirado = medidor.medir(skill, [infon("Hiperlipasemia")])
    todo_mirado = medidor.medir(
        skill,
        [
            infon("Hiperlipasemia"),
            infon("Hiperamilasemia"),
            infon("Dolor epigastrico"),
            infon("Vomitos"),
        ],
    )

    assert poco_mirado.direccion == pytest.approx(todo_mirado.direccion, abs=1e-4)
    assert poco_mirado.cobertura < todo_mirado.cobertura


def test_un_protocolo_categorico_no_finge_factores_ponderados(medidor):
    """Sin LR declarados no hay cobertura que preguntar: es None, no 0.

    Un cero diría que ninguna dimensión se ha mirado, que es una
    afirmación sobre el caso. `None` dice que la lectura ponderada no
    aplica a este protocolo, que es lo cierto. Es la misma distinción por
    la que `medir` devuelve None en vez de un Φ de 0.
    """
    categorico = Skill(
        "categorico",
        "---\ntitulo: X\nsignos:\n  - nombre: Hiperlipasemia\n    fuente: y\n---\n\nP\n",
    )
    res = medidor.medir(categorico, [infon("Hiperlipasemia")])

    assert res is not None, "un protocolo sólo-categorías sigue siendo medible"
    assert res.phi_categorico is not None
    assert res.direccion is None
    assert res.cobertura is None
    assert res.explicacion is None
    # Pero la lectura categórica sí tiene los suyos: la ausencia es de la
    # lectura ponderada, no del caso.
    assert res.cobertura_categorica is not None


def _categorico(nombre, cuantos, lr=None, citado=True):
    """Un protocolo de `cuantos` signos, con o sin cociente y con o sin cita."""
    cuerpo = "\n".join(
        f"  - nombre: Signo {i}"
        + ("\n    fuente: y" if citado else "")
        + (f"\n    lr: {lr}" if lr else "")
        for i in range(cuantos)
    )
    return Skill(nombre, f"---\ntitulo: {nombre}\nsignos:\n{cuerpo}\n---\n\nP\n")


def test_los_factores_categoricos_reconstruyen_su_coseno(medidor):
    """El producto da `coseno_categorico`, no `phi_categorico`.

    La diferencia no es un detalle de implementación: `phi_categorico` lleva
    α dentro, y α es la calidad documental del protocolo. Ordenar candidatas
    por él ordenaría por cuán bien citado está el índice, que es justo el
    error que la regla de selección existe para evitar.
    """
    skill = _categorico("cuatro", 4)
    escenarios = [
        [infon("Signo 0")],
        [infon("Signo 0"), infon("Signo 1"), infon("Signo 2", presente=False)],
        [infon("Signo 0"), infon("Hematuria")],  # con resto
        [infon("Signo 0"), infon("Hematuria"), infon("Soplo sistolico")],
    ]

    for infones in escenarios:
        res = medidor.medir(skill, infones)
        producto = res.direccion_categorica * math.sqrt(
            res.cobertura_categorica * res.explicacion_categorica
        )
        assert producto == pytest.approx(res.coseno_categorico, abs=1e-3), infones


def test_la_categorica_lee_en_la_misma_escala_que_la_ponderada(medidor):
    """La categórica ES la ponderada con todos los pesos iguales.

    El coseno es invariante de escala, así que con pesos uniformes la
    escala se cancela y las dos lecturas dan el mismo número. Eso es lo que
    permite que una candidata categórica y una ponderada compitan sin
    traducción — sin esto, compararlas sería comparar unidades distintas.

    La asimetría que queda es fiel y no un defecto: un criterio categórico
    no puede concentrar su peso en un signo, así que nunca alcanzará el
    coseno de una ponderada cuyo signo estrella consta. Es la cobertura
    haciendo su trabajo.
    """
    visto = [infon("Signo 0")]  # uno de cinco, en los tres

    uniforme = medidor.medir(_categorico("uniforme", 5, lr=2.0), visto)
    assert uniforme.coseno == pytest.approx(uniforme.coseno_categorico, abs=1e-4)

    # El mismo caso sin declarar cocientes: la lectura ponderada no existe,
    # y la categórica da exactamente lo que daba la uniforme.
    puro = medidor.medir(_categorico("puro", 5), visto)
    assert puro.coseno_categorico == pytest.approx(uniforme.coseno_categorico, abs=1e-4)

    # Y con un LR estrella, la ponderada se despega hacia arriba.
    estrella = Skill(
        "estrella",
        "---\ntitulo: estrella\nsignos:\n"
        "  - nombre: Signo 0\n    lr: 26.6\n    fuente: y\n"
        + "".join(
            f"  - nombre: Signo {i}\n    lr: 2.0\n    fuente: y\n" for i in range(1, 5)
        )
        + "---\n\nP\n",
    )
    assert medidor.medir(estrella, visto).coseno > uniforme.coseno


def test_el_coseno_categorico_no_lo_mueve_la_bibliografia(medidor):
    """`coseno_categorico` es la clave de orden porque α no lo toca.

    Dos protocolos idénticos salvo por las citas acoplan igual con el mismo
    paciente. Lo que cambia es cuánto se puede confiar en el argumento, y
    eso vive en α — separado, no mezclado en la clave de orden.
    """
    visto = [infon("Signo 0"), infon("Signo 1")]

    con = medidor.medir(_categorico("citado", 3), visto)
    sin = medidor.medir(_categorico("sin_citar", 3, citado=False), visto)

    assert con.coseno_categorico == pytest.approx(sin.coseno_categorico, abs=1e-4)
    assert con.phi_categorico > sin.phi_categorico
    assert sin.anclaje == 0.0


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


def delta_bayesiano(inferencia) -> float:
    """ln(odds posterior / odds previo) reconstruido desde la inferencia."""
    previa = inferencia.probabilidad_previa / 100
    final = inferencia.probabilidad_porcentaje / 100
    return math.log((final / (1 - final)) / (previa / (1 - previa)))


def test_phi_y_bayes_leen_el_mismo_vector(skill):
    """Σeᵢ = ln(odds posterior / odds previo) sobre el subespacio declarado.

    Ésta es la identidad que sostiene todo el diseño: Bayes lee la magnitud
    del vector de evidencia y Φ lee su dirección. Si el emparejamiento de
    los dos módulos divergiera, se rompería aquí antes que en ningún otro
    sitio.
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

    assert acoplamiento.peso_evidencia_declarado == pytest.approx(
        delta_bayesiano(inferencia), abs=1e-3
    )


def test_la_identidad_sobrevive_al_resto_no_simbolizado(skill):
    """La identidad vive en el subespacio declarado, y el residuo queda fuera.

    Éste es el test que faltaba. El caso sin resto no distingue entre sumar
    sobre las dimensiones declaradas y sumar sobre el vector completo,
    porque coinciden. En cuanto hay residuo dejan de coincidir, y sin este
    test un cambio futuro en la escala del residuo erosionaría la identidad
    en silencio.
    """
    infones = [
        infon("Hiperlipasemia"),
        infon("Dolor epigastrico"),
        infon("Hematuria"),
        infon("Soplo sistolico"),
    ]
    inferencia = AntigenPresentingCell().calcular(
        {"edad": 50, "antecedentes": ""}, skill.para_bayes(), infones
    )
    ac = MedidorDeAcoplamiento().medir(skill, infones, inferencia)
    delta = delta_bayesiano(inferencia)

    # Sobre lo declarado, la identidad se cumple.
    assert ac.peso_evidencia_declarado == pytest.approx(delta, abs=1e-3)

    # Sobre el vector completo NO, y eso es correcto: el peso del residuo es
    # una convención de este módulo con la que Bayes nunca operó. Se afirma
    # la divergencia para que nadie "arregle" el módulo hasta hacerla
    # desaparecer creyendo que corrige un fallo.
    suma_total = sum(c.observado for c in ac.componentes)
    assert suma_total > delta
    assert ac.resto_no_simbolizado


def test_la_identidad_exige_el_mismo_conjunto_de_infones(skill):
    """Segunda condición, y el pipeline la incumple a propósito.

    Bayes recibe el tic de hoy; Φ recibe además la línea de tiempo del
    holón, porque medir el acoplamiento contra medio paciente no mediría
    nada. Con historial previo la identidad deja de valer numéricamente, y
    conviene que eso esté escrito y no descubierto.
    """
    hoy = [infon("Dolor epigastrico")]
    historial = [infon("Hiperlipasemia")]

    inferencia = AntigenPresentingCell().calcular(
        {"edad": 50, "antecedentes": ""}, skill.para_bayes(), hoy
    )
    ac = MedidorDeAcoplamiento().medir(skill, historial + hoy, inferencia)

    assert ac.peso_evidencia_declarado > delta_bayesiano(inferencia)


def test_la_identidad_exige_un_infon_por_dimension(skill):
    """Tercera condición: dos infones sobre un mismo signo.

    Bayes multiplica el LR dos veces; este módulo lo cuenta una. La
    discrepancia no favorece a Bayes —contar dos veces la misma prueba es
    doble contabilidad de la evidencia— pero corregirlo es cambiar el motor
    bayesiano, no medir el acoplamiento. Queda fijado como comportamiento
    conocido.
    """
    infones = [infon("Hiperlipasemia"), infon("Hiperlipasemia", confianza=90.0)]

    inferencia = AntigenPresentingCell().calcular(
        {"edad": 50, "antecedentes": ""}, skill.para_bayes(), infones
    )
    ac = MedidorDeAcoplamiento().medir(skill, infones, inferencia)

    # Tolerancia relativa y no absoluta: el delta se reconstruye desde una
    # probabilidad redondeada a dos decimales, y con dos LR de 26.6 el
    # posterior roza el techo, donde los odds son muy sensibles a ese
    # redondeo. Lo que se afirma es el factor de 2, no el cuarto decimal.
    assert delta_bayesiano(inferencia) == pytest.approx(
        2 * ac.peso_evidencia_declarado, rel=1e-3
    )


def test_el_peso_declarado_excluye_el_residuo_por_construccion(skill):
    """La invariante tiene un nombre en el código, no sólo en la documentación."""
    ac = MedidorDeAcoplamiento().medir(
        skill, [infon("Hiperlipasemia"), infon("Hematuria")]
    )

    residuo = [c for c in ac.componentes if c.estado is EstadoDimension.NO_SIMBOLIZADO]
    assert residuo and all(c.observado for c in residuo)
    assert ac.peso_evidencia_declarado == pytest.approx(
        sum(c.observado for c in ac.componentes) - sum(c.observado for c in residuo)
    )


def test_probabilidad_alta_con_resto_sin_explicar_no_se_declara_operable(medidor, skill):
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
        [infon("Hiperlipasemia")] + [infon(f"Hallazgo ajeno {n}") for n in range(6)],
    )

    assert solo.coseno > con_dos.coseno > con_seis.coseno
    assert con_seis.veredicto in {
        VeredictoSemiotico.ACOPLAMIENTO_PARCIAL,
        VeredictoSemiotico.INERCIA,
    }
    # El umbral no es decorativo: escalando el residuo a la mediana del
    # protocolo —la primera versión de este módulo— cuatro hallazgos sin
    # explicar dejaban el coseno en 0.55, y la hipótesis se presentaba como
    # razonablemente acoplada. Es la regresión concreta que este número
    # impide, y por eso está escrito.
    cuatro_ajenos = medidor.medir(
        skill,
        [infon("Hiperlipasemia")] + [infon(f"Ajeno {n}") for n in range(4)],
    )
    assert cuatro_ajenos.coseno < 0.45


def test_un_hallazgo_no_explicado_pesa_como_los_que_si_se_explican(medidor, skill):
    """La regla de escala del residuo, enunciada como propiedad.

    Es la formulación en una línea de la sección 5 de la especificación:
    por cada hallazgo que la hipótesis explica con peso w, uno que no
    explica le cuesta otro tanto. Anclarla al protocolo en vez de al caso
    —como hacía la primera versión— deja que una prueba de LR enorme
    compre armonía casi ilimitada.
    """
    res = medidor.medir(skill, [infon("Hiperlipasemia"), infon("Hematuria")])

    explicada = next(c for c in res.componentes if c.dimension == "Hiperlipasemia")
    residuo = next(
        c for c in res.componentes if c.estado is EstadoDimension.NO_SIMBOLIZADO
    )
    assert residuo.observado == pytest.approx(abs(explicada.observado), abs=1e-4)

    # Con dos dimensiones explicadas de peso distinto, el residuo toma la
    # media cuadrática de ambas: ni la más fuerte ni la más débil.
    dos = medidor.medir(
        skill,
        [infon("Hiperlipasemia"), infon("Vomitos"), infon("Hematuria")],
    )
    pesos = [
        abs(c.observado)
        for c in dos.componentes
        if c.observado and c.estado is not EstadoDimension.NO_SIMBOLIZADO
    ]
    esperado = math.sqrt(sum(w**2 for w in pesos) / len(pesos))
    residuo_dos = next(
        c for c in dos.componentes if c.estado is EstadoDimension.NO_SIMBOLIZADO
    )
    assert residuo_dos.observado == pytest.approx(esperado, abs=1e-4)
    assert min(pesos) < residuo_dos.observado < max(pesos)


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


# --- La duda ----------------------------------------------------------


def test_la_duda_no_puede_contradecir_a_su_propia_banda(medidor, skill):
    """El invariante: `duda` y `veredicto` leen el mismo número.

    Antes no lo hacían. `duda` leía `phi` y las bandas leían el categórico
    cuando la ponderada no existía, así que un protocolo de categorías
    podía informar ARMONIA y duda a la vez. Se afirma como invariante y no
    como caso, porque el fallo no estaba en un valor sino en que dos
    lecturas del mismo objeto usaban vectores distintos.
    """
    sin_duda = {VeredictoSemiotico.ARMONIA, VeredictoSemiotico.ACOPLAMIENTO_PARCIAL}
    escenarios = [
        [],
        [infon("Hiperlipasemia")],
        [infon("Hiperlipasemia"), infon("Dolor epigastrico")],
        [infon("Hiperlipasemia", presente=False)],
        [infon("Cefalea")],
        [infon("Hiperlipasemia"), infon("Hematuria"), infon("Soplo sistolico")],
    ]
    for infones in escenarios:
        res = medidor.medir(skill, infones)
        assert res.duda is (res.veredicto not in sin_duda), (
            f"{infones}: banda {res.veredicto.value} con duda={res.duda}"
        )


def test_la_duda_usa_el_mismo_umbral_que_la_banda():
    """El 0.20 está escrito dos veces, y este test es lo que las ata.

    `models` no importa de `core` para no cerrar un ciclo, así que la
    constante no se puede compartir. Lo que impide que se separen en
    silencio es esta comparación.
    """
    from holonmed.core.acoplamiento import UMBRAL_ACOPLAMIENTO
    from holonmed.models import Acoplamiento

    fuente = inspect.getsource(Acoplamiento.duda.fget)
    assert f"< {UMBRAL_ACOPLAMIENTO}" in fuente


def test_con_las_dos_lecturas_manda_la_ponderada(medidor, skill):
    """El categórico es el suplente, no el preferido.

    Un solo vómito —LR 1.6, el signo que menos discrimina del protocolo—
    da Φ ponderado 0.1092 y Φ categórico 0.4915: la lectura de ±1 cuenta
    ese vómito igual que una lipasa con LR de 26.6, y por eso infla. Donde
    hay cocientes publicados la ponderada es la medida y la categórica una
    aproximación que existe para cuando no los hay.

    El caso está elegido porque las dos lecturas **discrepan sobre la
    duda**: preferir el categórico la apagaría.
    """
    res = medidor.medir(skill, [infon("Vomitos")])

    assert res.cobertura is not None  # la ponderada existe
    assert res.phi_categorico > 0.20  # y el categórico diría que no hay duda
    assert res.phi_legible == res.phi
    assert res.duda
