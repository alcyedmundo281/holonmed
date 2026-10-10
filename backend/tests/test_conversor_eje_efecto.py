"""El eje `efecto` en el conversor, comprobado SIN el índice.

Por qué existe este archivo aparte de `test_ciclo5_parkinson_extremo_a_extremo`:
aquéllas convierten desde un clon real de `medsemiotics-db` y **se saltan allí
donde no esté**: CI lo clona, pero una máquina cualquiera no. Son la prueba de
aceptación del ciclo y valen lo que valen, pero mientras sean las únicas, todo
lo que el ciclo garantiza depende de tener la fuente delante.

Éstas construyen un índice sintético en memoria y corren en cualquier parte.
No sustituyen a las de aceptación: cubren las reglas, no el trayecto.

LA REGLA QUE MÁS SE PRUEBA AQUÍ
-------------------------------
Cuando el conversor no puede honrar el efecto declarado, la arista **no entra
en el bloque estructurado**. La tentación es degradarla a `apoya`, y eso no es
conservador: `veredicto.py` cuenta los signos con `efecto == "apoya"`, así que
una advertencia degradada pasa a **sumar a favor** de la enfermedad contra la
que avisaba. Invierte el signo del hallazgo.

No emitirla deja exactamente el comportamiento anterior al ciclo —el hallazgo
sigue en la prosa del cuerpo, que el modelo lee— y además es lo que el diseño
ya había decidido para la fiebre: un hallazgo validado que ningún signo declara
cae en `resto_no_simbolizado`, baja Φ y aparece en `indagacion`, sin que el
sistema afirme un poder discriminativo que no consta.
"""

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from holonmed.core import skills as modulo_skills  # noqa: E402
from holonmed.core.skills import Skill  # noqa: E402
from holonmed.core.veredicto import EvaluadorDeVeredicto  # noqa: E402
from holonmed.models import EstadoInfon, Infon, Polaridad  # noqa: E402

convertir_condicion = pytest.importorskip("convertir_condicion")


# ── un índice sintético, que no necesita clon ────────────────────────────────

CONCEPTOS = {
    "HM:0711": {"termino": "Anemia", "codigos": {"icd10": "D64.9"}},
    "HM:0101": {"termino": "Fiebre", "codigos": {}},
    "HM:0900": {"termino": "Apendicectomía previa", "codigos": {}},
    "HM:0201": {"termino": "Dolor en fosa ilíaca derecha", "codigos": {}},
}


REFERENCIAS = {
    "pmid:26474316": {
        "autores": ["Postuma RB", "Berg D"],
        "publicacion": "Mov Disord",
        "anio": 2015,
        "volumen": "30",
        "paginas": "1591-601",
        "identificadores": {"pmid": "26474316", "doi": "10.1002/mds.26424"},
        "verificacion": {"pubmed": True},
    }
}


def indice():
    return convertir_condicion.Indice(
        ruta=Path("/no/existe"),
        conceptos=dict(CONCEPTOS),
        condiciones={},
        referencias=dict(REFERENCIAS),
        archivos={},
        commit="0" * 7,
        limpio=True,
    )


def convertir_balance(condicion: dict):
    informe = convertir_condicion.Informe()
    bloque = convertir_condicion.nucleo_y_balance(condicion, indice(), informe)
    texto = bloque.texto() if bloque else ""
    return texto, [f"{donde}: {texto}" for donde, texto in informe.pendientes]


def convertir_signos(condicion: dict):
    """Devuelve (texto del bloque, lista de pendientes)."""
    informe = convertir_condicion.Informe()
    bloque, _ = convertir_condicion.signos(condicion, indice(), informe)
    return bloque.texto(), [f"{donde}: {texto}" for donde, texto in informe.pendientes]


def infon(termino: str, polaridad: Polaridad = Polaridad.PRESENTE) -> Infon:
    return Infon(
        texto_origen=termino,
        termino_propuesto=termino,
        termino=termino,
        polaridad=polaridad,
        estado=EstadoInfon.VALIDADO,
    )


# ── lo que SÍ se emite ───────────────────────────────────────────────────────


def test_una_bandera_respaldada_entra_como_bandera_roja():
    texto, pendientes = convertir_signos(
        {
            "signos_de_alarma": [
                {"concepto": "HM:0711", "sostiene": "consenso_con_afirmacion"}
            ]
        }
    )
    assert "nombre: Anemia" in texto
    assert "efecto: bandera_roja" in texto
    assert not any("Anemia" in p for p in pendientes)


def test_una_arista_corriente_no_cambia():
    """La compatibilidad hacia atrás, en pequeño: sin `efecto` declarado, el
    bloque sale como salía. Es `apoya` por el esquema, no por respaldo."""
    texto, _ = convertir_signos({"signos": [{"concepto": "HM:0711", "rol": "apoyo"}]})
    assert "nombre: Anemia" in texto
    assert "efecto:" not in texto
    assert "dispara_si:" not in texto


def test_una_bandera_por_ausencia_conserva_su_polaridad():
    texto, _ = convertir_signos(
        {
            "signos_de_alarma": [
                {
                    "concepto": "HM:0201",
                    "sostiene": "discriminacion_medida",
                    "dispara_si": "ausente",
                }
            ]
        }
    )
    assert "efecto: bandera_roja" in texto
    assert "dispara_si: ausente" in texto


def test_una_exclusion_por_mecanismo_con_motivo_se_emite():
    texto, _ = convertir_signos(
        {
            "signos": [
                {
                    "concepto": "HM:0900",
                    "efecto": "excluye",
                    "sostiene": "mecanismo",
                    "motivo": "sin apéndice no puede haber apendicitis",
                }
            ]
        }
    )
    assert "efecto: excluye" in texto


# ── lo que NO se emite, y las dos mitades de cada negativa ───────────────────


@pytest.mark.parametrize(
    "arista, fragmento",
    [
        # una lista de alarma no autoriza una bandera (parsimonia)
        ({"concepto": "HM:0101", "sostiene": "consenso_de_lista"}, "no lo autoriza"),
        # ni siquiera declarar nada
        ({"concepto": "HM:0101"}, "no lo autoriza"),
    ],
)
def test_una_bandera_sin_respaldo_no_entra_al_bloque(arista, fragmento):
    """Las DOS mitades: no se emite Y se enumera.

    Y la tercera, que es la que importa: tampoco entra como `apoya`. Degradarla
    la convertiría en un criterio a favor del diagnóstico contra el que avisa.
    """
    texto, pendientes = convertir_signos({"signos_de_alarma": [arista]})

    assert "Fiebre" not in texto, "se emitió una bandera que no está respaldada"
    assert "efecto: apoya" not in texto
    assert any(fragmento in p for p in pendientes), pendientes


def test_una_exclusion_por_mecanismo_sin_motivo_no_entra_al_bloque():
    """El caso peor del degradado: una exclusión absoluta convertida en apoyo."""
    texto, pendientes = convertir_signos(
        {
            "signos": [
                {
                    "concepto": "HM:0900",
                    "efecto": "excluye",
                    "sostiene": "mecanismo",
                }
            ]
        }
    )
    assert "Apendicectomía" not in texto
    assert "efecto:" not in texto
    assert any("motivo" in p for p in pendientes), pendientes


def test_un_efecto_desconocido_no_entra_al_bloque():
    texto, pendientes = convertir_signos(
        {"signos": [{"concepto": "HM:0711", "efecto": "bandera_amarilla"}]}
    )
    assert "Anemia" not in texto
    assert any("bandera_amarilla" in p for p in pendientes), pendientes


def test_un_dispara_si_desconocido_no_entra_al_bloque():
    """Emitirlo como «presente» podría invertir cuándo dispara la bandera."""
    texto, pendientes = convertir_signos(
        {
            "signos_de_alarma": [
                {
                    "concepto": "HM:0201",
                    "sostiene": "discriminacion_medida",
                    "dispara_si": "quizas",
                }
            ]
        }
    )
    assert "Dolor" not in texto
    assert any("quizas" in p for p in pendientes), pendientes


def test_el_odds_ratio_nunca_sale_como_cociente():
    """Un OR no es una propiedad del hallazgo y el motor lo multiplicaría."""
    texto, _ = convertir_signos(
        {
            "signos_de_alarma": [
                {
                    "concepto": "HM:0711",
                    "sostiene": "consenso_con_afirmacion",
                    "odds_ratio": {"valor": 2.7, "ic95": [1.4, 5.1]},
                }
            ]
        }
    )
    assert "lr:" not in texto
    assert "lr_negativo:" not in texto
    assert "2.7" not in texto


# ── la consecuencia clínica, extremo a extremo pero sin índice ───────────────


def test_una_bandera_sin_respaldo_no_cuenta_en_ninguna_direccion():
    """Lo que de verdad se está protegiendo, medido donde se decide.

    Antes de esto la fiebre degradada llegaba a `veredicto.py` como apoyo y
    sumaba hacia el nivel de certeza. Ahora no cuenta ni a favor ni en contra:
    el hallazgo se ve —sigue en la prosa, y Φ lo recoge como resto no
    simbolizado— pero no empuja el criterio.
    """
    texto, _ = convertir_signos(
        {
            "signos_de_alarma": [
                {"concepto": "HM:0711", "sostiene": "consenso_con_afirmacion"},
                {"concepto": "HM:0101", "sostiene": "consenso_de_lista"},
            ]
        }
    )
    skill = Skill("x", f"---\ntitulo: Prueba\n{texto}\n---\n\nPROTOCOLO\n")

    veredicto = EvaluadorDeVeredicto().evaluar(skill, [infon("Anemia"), infon("Fiebre")])
    assert veredicto is not None
    assert veredicto.banderas_rojas == ["Anemia"]
    assert veredicto.apoyos == [], "la fiebre degradada volvió a contar a favor"


# ── que las tablas no diverjan entre los dos archivos ────────────────────────


def test_las_taxonomias_del_eje_no_divergen():
    """El script no importa el paquete, así que las repite. Que coincidan no
    puede quedar en que alguien se acuerde."""
    assert convertir_condicion.EFECTOS == modulo_skills.EFECTOS
    assert convertir_condicion.POLARIDADES == modulo_skills.POLARIDADES
    assert convertir_condicion.CAMPOS_NIVEL == modulo_skills._CAMPOS_NIVEL


def test_cada_clave_conocida_se_emite_o_se_declara_no_emitida():
    """Meter una clave en la lista blanca sin emitirla la pasa de «denunciada»
    a SILENCIOSAMENTE PERDIDA, que es peor que no conocerla."""
    import inspect

    fuente = "".join(
        inspect.getsource(f)
        for f in (
            convertir_condicion.signos,
            convertir_condicion._decidir_efecto,
            convertir_condicion.nucleo_y_balance,
            convertir_condicion._comentar_contexto,
            convertir_condicion._fuente,
        )
    )
    sin_cubrir = {
        c
        for c in convertir_condicion.CLAVES_ARISTA
        if c not in convertir_condicion.CONOCIDAS_NO_EMITIDAS and f'"{c}"' not in fuente
    }
    assert not sin_cubrir, (
        f"claves en CLAVES_ARISTA que nadie emite ni declara no emitidas: "
        f"{sorted(sin_cubrir)}"
    )


# ── el balance, del lado del parseador ───────────────────────────────────────

PLANTILLA_BALANCE = """---
titulo: Prueba
signos:
  - nombre: Anemia
balance:
{cuerpo}
---

PROTOCOLO
"""


def test_los_niveles_conservan_el_orden_declarado():
    """El motor se queda con el PRIMERO que se satisface, así que invertirlos
    rebajaría el grado de certeza en silencio."""
    skill = Skill(
        "x",
        PLANTILLA_BALANCE.format(
            cuerpo=(
                '  fuente: "Postuma RB et al"\n'
                "  establecida: {apoyos_minimos: 2, banderas_maximas: 0}\n"
                "  probable:    {contrapeso: 1, banderas_maximas: 2}\n"
            )
        ),
    )
    assert [n.nombre for n in skill.balance.niveles] == ["establecida", "probable"]


def test_una_clave_que_no_es_nivel_no_se_interpreta_como_nivel():
    """`poblacion: {...}` es un diccionario y colaba por el filtro anterior. Un
    nivel de más hace el criterio MÁS permisivo."""
    skill = Skill(
        "x",
        PLANTILLA_BALANCE.format(
            cuerpo=(
                '  fuente: "Postuma RB et al"\n'
                "  poblacion: {edad_minima: 50}\n"
                "  establecida: {apoyos_minimos: 2, banderas_maximas: 0}\n"
            )
        ),
    )
    assert [n.nombre for n in skill.balance.niveles] == ["establecida"]
    assert any("poblacion" in p for p in skill.problemas())


# ── el balance, del lado del conversor ───────────────────────────────────────
#
# Estas tres faltaban y lo dijo una mutación: devolver la negación abierta a la
# emisión del balance no tiraba ni una prueba. El arreglo estaba escrito y sin
# comprobar, que es la misma clase de verde que este proyecto persigue.


def test_el_conversor_no_emite_como_nivel_lo_que_no_lo_es():
    texto, pendientes = convertir_balance(
        {
            "balance": {
                "ref": "pmid:26474316",
                "poblacion": {"edad_minima": 50},
                "establecida": {"apoyos_minimos": 2, "banderas_maximas": 0},
            }
        }
    )
    assert "establecida:" in texto
    assert "poblacion" not in texto, "una clave que no es nivel salió como nivel"
    assert any("poblacion" in p for p in pendientes), pendientes


def test_el_conversor_traduce_ref_a_fuente_en_prosa():
    """El índice guarda el identificador; la skill guarda la cita legible."""
    texto, _ = convertir_balance(
        {
            "balance": {
                "ref": "pmid:26474316",
                "establecida": {"apoyos_minimos": 2, "banderas_maximas": 0},
            }
        }
    )
    assert "Postuma" in texto
    assert "\n  ref:" not in texto


def test_un_nucleo_roto_se_lleva_el_balance():
    """Emitir el balance sin su núcleo no es conservador: es más permisivo."""
    texto, pendientes = convertir_balance(
        {
            "nucleo": {"requiere": ["HM:9999"], "ref": "pmid:26474316"},
            "balance": {
                "ref": "pmid:26474316",
                "establecida": {"apoyos_minimos": 2, "banderas_maximas": 0},
            },
        }
    )
    assert "nucleo:" not in texto
    assert "balance:" not in texto, "el balance sobrevivió a su núcleo"
    assert any("no resuelve" in p for p in pendientes), pendientes


def test_un_balance_sin_fuente_se_denuncia():
    """Los enteros los fija el panel que redacta el criterio, no el sistema."""
    skill = Skill(
        "x",
        PLANTILLA_BALANCE.format(
            cuerpo=("  establecida: {apoyos_minimos: 2, banderas_maximas: 0}\n")
        ),
    )
    assert skill.balance.declarado
    assert any("sin `fuente`" in p for p in skill.problemas())


# ── varias aristas para el mismo hallazgo ────────────────────────────────────


def _arista(concepto: str, **lr) -> dict:
    return {"concepto": concepto, "rol": "apoyo", "estado_lr": "medido", **lr}


def test_dos_aristas_con_el_mismo_lr_no_se_trasladan_ni_se_cuentan_dos_veces():
    """Una arista por población: emitirlas duplicaría la evidencia, y elegir una
    sería decidir en silencio cuál es la población del usuario."""
    texto, pendientes = convertir_signos(
        {
            "signos": [
                _arista("HM:0101", lr_positivo={"valor": 3.0}, poblacion="niños"),
                _arista("HM:0101", lr_positivo={"valor": 4.7}, poblacion="gestantes"),
            ]
        }
    )
    assert texto.count("nombre: Fiebre") == 1
    assert "\n    lr:" not in texto
    assert "candidata 1: LR+ 3.0" in texto and "candidata 2: LR+ 4.7" in texto
    assert any("aristas con cociente para el mismo hallazgo" in p for p in pendientes)


def test_el_lr_positivo_en_una_arista_y_el_negativo_en_otra_no_chocan():
    texto, pendientes = convertir_signos(
        {
            "signos": [
                _arista("HM:0101", lr_positivo={"valor": 26.3, "ref": "pmid:26474316"}),
                _arista("HM:0101", lr_negativo={"valor": 0.4, "ref": "pmid:26474316"}),
            ]
        }
    )
    assert "lr: 26.3" in texto and "lr_negativo: 0.4" in texto
    assert not any("mismo hallazgo" in p for p in pendientes)


# ── prevalencia sin ningún cociente ──────────────────────────────────────────


def test_una_prevalencia_sin_ningun_lr_no_activa_el_modelo_bayesiano():
    informe = convertir_condicion.Informe()
    bloque = convertir_condicion.bayes(
        {"probabilidad_base": {"valor": 0.2}}, indice(), informe
    )
    assert "probabilidad_base: 0.0" in bloque.texto()
    assert any("ningún signo con LR" in t for _, t in informe.pendientes)


def test_con_algun_lr_la_prevalencia_del_indice_se_conserva():
    informe = convertir_condicion.Informe()
    informe.signos_con_lr = 1
    bloque = convertir_condicion.bayes(
        {"probabilidad_base": {"valor": 0.2}}, indice(), informe
    )
    assert "probabilidad_base: 0.2" in bloque.texto()


# ── lo que el motor no puede honrar no entra en el bloque estructurado ──────


def test_una_exclusion_con_advertencia_no_entra_como_veto():
    """`excluye` es un veto absoluto; la excepción de la advertencia sólo
    viviría en un comentario y el motor no puede aplicarla."""
    texto, pendientes = convertir_signos(
        {
            "signos": [
                {
                    "concepto": "HM:0900",
                    "efecto": "excluye",
                    "sostiene": "mecanismo",
                    "motivo": "anatomía",
                    "advertencia": "existe la excepción heterotópica",
                }
            ]
        }
    )
    assert "excluye" not in texto
    assert any("advertencia" in p for p in pendientes)


def test_un_lr_publicado_para_un_umbral_no_se_traslada():
    """El motor no evalúa el valor medido: el número se aplicaría a cualquier
    mención de la prueba."""
    texto, pendientes = convertir_signos(
        {
            "signos": [
                _arista(
                    "HM:0101",
                    lr_positivo={"valor": 2.3, "umbral": "hCG > 1500 mIU/mL"},
                    lr_negativo={"valor": 0.91, "umbral": "hCG > 1500 mIU/mL"},
                )
            ]
        }
    )
    assert "\n    lr:" not in texto and "lr_negativo:" not in texto
    assert "LR+ 2.3 para hCG > 1500 mIU/mL" in texto
    assert any("umbral" in p for p in pendientes)


def test_una_exclusion_sostenida_por_un_cociente_medido_es_evidencia_no_veto():
    """Un LR de 0.2 reduce la probabilidad; no la anula. Emitido como `excluye`
    se leería como veto absoluto; como `apoya`, contaría a favor lo que resta."""
    texto, pendientes = convertir_signos(
        {
            "signos": [
                {
                    "concepto": "HM:0101",
                    "estado_lr": "medido",
                    "efecto": "excluye",
                    "sostiene": "discriminacion_medida",
                    "dispara_si": "ausente",
                    "lr_negativo": {"valor": 0.1, "ref": "pmid:26474316"},
                }
            ]
        }
    )
    assert "efecto: evidencia" in texto
    assert "excluye" not in texto and "efecto: apoya" not in texto
    assert "lr_negativo: 0.1" in texto
    # `dispara_si` no significa nada para una evidencia: no se arrastra.
    assert "dispara_si" not in texto
    assert not pendientes


def test_una_exclusion_medida_sin_ningun_cociente_utilizable_no_entra():
    texto, pendientes = convertir_signos(
        {
            "signos": [
                {
                    "concepto": "HM:0101",
                    "efecto": "excluye",
                    "sostiene": "discriminacion_medida",
                    "lr_negativo": {"rango": [0.1, 0.3]},
                }
            ]
        }
    )
    assert "Fiebre" not in texto
    assert any("sin ningún cociente utilizable" in p for p in pendientes)
