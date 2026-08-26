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

    residuo = [
        c for c in ac.componentes if c.estado is EstadoDimension.NO_SIMBOLIZADO
    ]
    assert residuo and all(c.observado for c in residuo)
    assert ac.peso_evidencia_declarado == pytest.approx(
        sum(c.observado for c in ac.componentes) - sum(c.observado for c in residuo)
    )


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


# --- Los tres factores de cos(h,e) -----------------------------------


def test_los_tres_factores_reconstruyen_el_coseno_derivandolos_a_mano(medidor, skill):
    """Deriva los tres factores desde los LR del protocolo, no desde `componentes`.

    La derivación se escribe entera aquí —con los cocientes del
    frontmatter y nada más— en vez de recorrer `acoplamiento.componentes`.
    La diferencia no es de estilo. Un test que lee `componentes` recorre la
    misma ruta que la implementación con otra redacción, y pasaría igual si
    el vector que se descompone no fuera el que Φ usa. Coincidiendo las
    tres columnas se afirman dos cosas a la vez: que la identidad es
    cierta, y que el vector descompuesto es el que produjo `coseno`.
    """
    lipasa, amilasa, dolor, vomitos = (
        math.log(26.6),
        math.log(12.5),
        math.log(2.1),
        math.log(1.6),
    )

    # Dos dimensiones declaradas constan; dos nadie las miró. Y un hallazgo
    # validado que el protocolo no explica, que es lo que separa la
    # identidad de tres factores de la de dos.
    res = medidor.medir(
        skill,
        [infon("Hiperlipasemia"), infon("Dolor epigastrico"), infon("Hematuria")],
    )

    medido = lipasa**2 + dolor**2
    declarado = medido + amilasa**2 + vomitos**2
    # El resto pesa la media cuadrática de lo que este caso sí explicó.
    peso_resto = math.sqrt(medido / 2)

    assert res.direccion == pytest.approx(1.0, abs=1e-4)
    assert res.cobertura == pytest.approx(medido / declarado, abs=1e-4)
    assert res.explicacion == pytest.approx(
        medido / (medido + peso_resto**2), abs=1e-4
    )

    reconstruido = (
        res.direccion * math.sqrt(res.cobertura) * math.sqrt(res.explicacion)
    )
    assert reconstruido == pytest.approx(res.coseno, abs=1e-4)


def test_dos_factores_no_bastan_en_cuanto_hay_resto(medidor, skill):
    """La identidad de dos factores yerra, y por eso el tercero existe.

    `cos = dirección · √cobertura` se comprobó en su día contra tres casos
    que no tenían resto no simbolizado, donde las dos identidades
    coinciden. Se afirma aquí la divergencia para que nadie vuelva a
    quitarla creyendo que simplifica.
    """
    sin_resto = medidor.medir(
        skill, [infon("Hiperlipasemia"), infon("Dolor epigastrico")]
    )
    con_resto = medidor.medir(
        skill,
        [infon("Hiperlipasemia"), infon("Dolor epigastrico"), infon("Hematuria")],
    )

    dos = sin_resto.direccion * math.sqrt(sin_resto.cobertura)
    assert dos == pytest.approx(sin_resto.coseno, abs=1e-4)

    # Con resto, los dos factores dan el mismo número de antes —no ven el
    # residuo— y el coseno real ha bajado.
    dos_con_resto = con_resto.direccion * math.sqrt(con_resto.cobertura)
    assert dos_con_resto == pytest.approx(dos, abs=1e-4)
    assert con_resto.coseno < sin_resto.coseno - 0.1


def test_un_hallazgo_ajeno_baja_la_explicacion_y_deja_la_cobertura_intacta(
    medidor, skill
):
    """La propiedad, sin mirar dentro de la fórmula.

    Un hallazgo que la hipótesis no explica es del lado del paciente: no
    cambia cuánto de la hipótesis se ha mirado. Afirmarlo como propiedad
    —y no comparando contra la fórmula— es lo que hace que quitar el
    residuo del denominador tumbe el test.
    """
    base = [infon("Hiperlipasemia"), infon("Dolor epigastrico")]
    sin = medidor.medir(skill, base)
    con = medidor.medir(skill, base + [infon("Hematuria")])

    assert con.explicacion < sin.explicacion
    assert con.cobertura == pytest.approx(sin.cobertura, abs=1e-4)
    assert con.direccion == pytest.approx(sin.direccion, abs=1e-4)


def test_una_dimension_sin_mirar_baja_la_cobertura_y_deja_la_explicacion_intacta(
    medidor, skill
):
    """La simétrica: lo no mirado es del lado de la hipótesis."""
    poco = medidor.medir(skill, [infon("Hiperlipasemia")])
    mas = medidor.medir(skill, [infon("Hiperlipasemia"), infon("Hiperamilasemia")])

    assert mas.cobertura > poco.cobertura
    assert mas.explicacion == pytest.approx(poco.explicacion, abs=1e-4)


def test_los_factores_son_None_y_no_cero_cuando_no_hay_con_que_preguntarlos(
    medidor, skill
):
    """Un 0 afirmaría algo sobre el caso; None dice que no hay pregunta.

    Es la misma distinción que `medir` hace al devolver None en vez de un
    Φ de 0, y la que `SIN_MEDIR` hace un nivel más abajo. Sin ninguna
    dimensión medida no hay ángulo entre h y e: la dirección no es 0, no
    existe. La cobertura sí es 0, y es una afirmación cierta —no se ha
    mirado nada de lo que la hipótesis exige—, de modo que 0 y None no se
    reparten por comodidad sino por lo que cada uno dice.
    """
    vacio = medidor.medir(skill, [])
    assert vacio.direccion is None
    assert vacio.cobertura == 0.0
    assert vacio.explicacion is None

    # Con sólo un hallazgo ajeno hay paciente pero no hay nada de la
    # hipótesis medido: sigue sin haber ángulo, y ya hay algo que explicar.
    ajeno = medidor.medir(skill, [infon("Hematuria")])
    assert ajeno.direccion is None
    assert ajeno.cobertura == 0.0
    assert ajeno.explicacion == 0.0
