"""La guarda del router: el grafo comprueba al prompt de triaje.

Vive aparte de `test_pipeline.py` a propósito. Es un asunto propio —y su
commit propio—, y compartir el final de un fichero con otro asunto hace que
ninguno de los dos se pueda revertir solo.

Reutiliza los dobles de `test_pipeline`: el LLM y el índice falsos son los
mismos, y duplicarlos sería tener dos definiciones de lo mismo que un día
dejarían de coincidir.
"""

# `entorno` se importa para que pytest la resuelva aquí; los parámetros de
# los tests que la piden vuelven a ligar el nombre, y de ahí los F811. Es el
# precio de reutilizar la fixture en vez de duplicarla.
from test_pipeline import (  # noqa: F401
    TERMINO_SIN_HINT,
    IndexFalso,
    LLMFalso,
    entorno,
    extraccion_de,
)

from holonmed.models import HolonPaciente, ResultadoTic, SinCandidatas

# --- La guarda del router: el tercer estado del eje del triaje -------------
#
# `triaje_coincide is False` dice que el grafo prefirió OTRA de las que
# propuso. Que el grafo no propusiera siquiera la que el triaje eligió es
# otra cosa, y peor, y hasta ahora se contaban igual. Sólo se mide: el
# protocolo que se usa no cambia.


# El protocolo de prueba en formato moderno: `ambito_grafo` vive en el
# frontmatter, y es lo que decide qué candidatas propone el grafo. El SKILL
# de arriba, en formato JSON heredado, no lo declara — por eso estos dos
# tests traen el suyo en vez de reutilizarlo.
SKILL_CON_AMBITO = """---
titulo: Condición de prueba
version: "1.0.0"
ambito_grafo: ["{ambito}"]
condicion:
  nombre: Condición de prueba
modelo_bayesiano:
  probabilidad_base: 0.1
signos:
  - nombre: Fiebre
    codigos: {{ snomed: "386661006" }}
    lr: 3.0
    fuente: "doble de prueba"
criterios_laboratorio:
  reglas:
    - parametro: Temperatura
      corte_superior: 38.0
      termino_si_alto: Fiebre
---

# Protocolo de prueba
"""


async def test_el_triaje_eligiendo_fuera_del_grafo_queda_registrado(entorno, tmp_path):  # noqa: F811
    """El prompt eligió un protocolo que el paciente no sugiere.

    Es lo que pasó con un informe de ACV y un catálogo sin neurología: el
    router respondió `sindrome_coronario_agudo`, y el grafo del paciente no
    lo había propuesto. Con `triaje_coincide` solo, eso se lee igual que una
    discrepancia entre dos hipótesis que ambas venían a cuento.

    Aquí el grafo del paciente cubre `general_triage` y NO `otro_protocolo`,
    y el triaje usa el segundo. Se comprueba que quede registrado y que el
    protocolo activo NO cambie: esto sólo mide.
    """
    (tmp_path / "general_triage.md").write_text(
        SKILL_CON_AMBITO.format(ambito="386661006"), encoding="utf-8"
    )
    (tmp_path / "otro_protocolo.md").write_text(
        SKILL_CON_AMBITO.format(ambito="999999"), encoding="utf-8"
    )
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5",
        HolonPaciente(paciente_id="t"),
        skill_forzada="otro_protocolo",
    )

    assert resultado.skill_activa == "otro_protocolo"  # no se cambia nada
    assert resultado.triaje_en_candidatas is False  # y se registra


async def test_un_triaje_que_el_grafo_si_propuso_no_dispara_la_guarda(entorno, tmp_path):  # noqa: F811
    """El caso normal: la guarda calla cuando el prompt eligió a cuento."""
    (tmp_path / "general_triage.md").write_text(
        SKILL_CON_AMBITO.format(ambito="386661006"), encoding="utf-8"
    )
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )

    assert resultado.triaje_en_candidatas is True


def test_el_tercer_estado_es_distinto_de_discrepar():
    """Los tres valores dicen tres cosas y ninguno es el defecto del otro.

    `None` es «el grafo no propuso ninguna candidata», no «el triaje eligió
    fuera». Colapsarlos contaría como fallo del prompt un tic donde nadie le
    llevó la contraria — el mismo razonamiento que ya protege a
    `triaje_coincide` en `acuerdo_del_triaje()`.
    """
    r = ResultadoTic(paciente_id="t", texto_original="x", skill_activa="a")
    assert r.triaje_en_candidatas is None


# --- Las tres salidas mudas, cada una con su nombre ------------------------
#
# Salían por dos `return` y llegaban como el mismo `None`. No son la misma
# situación: la primera es un fallo de validación, la segunda del
# vocabulario, y la tercera no es un fallo sino un encargo.


def test_el_aviso_nombra_lo_que_eligio_el_triaje_y_no_la_ganadora():
    """Con `abduccion_decide` el protocolo activo ya es la ganadora del grafo.
    Decir «FUERA DEL GRAFO: <la ganadora>» desacreditaba justo a la hipótesis
    que el grafo sí sostiene, y escondía cuál fue la elección del triaje."""
    from holonmed.cli import _lineas_competencia
    from holonmed.models import CandidataAbductiva

    r = ResultadoTic(
        paciente_id="t",
        texto_original="…",
        skill_activa="ganadora_del_grafo",
        skill_triaje="elegida_por_el_triaje",
        triaje_en_candidatas=False,
        triaje_coincide=False,
        ganadora_abductiva="ganadora_del_grafo",
        competencia=[CandidataAbductiva(skill="ganadora_del_grafo")],
    )
    texto = "\n".join(_lineas_competencia(r))

    assert "FUERA DEL GRAFO: elegida_por_el_triaje" in texto
    assert "el triaje usó elegida_por_el_triaje" in texto
    assert "FUERA DEL GRAFO: ganadora_del_grafo" not in texto


def test_nada_validado_dice_que_fue_la_lectura_inicial_si_luego_se_valido():
    """La causa se fija al competir, sobre la lectura inicial. Con
    `abduccion_decide` la segunda pasada puede validar lo que la primera
    rechazó; entonces «no se validó ni un hallazgo» sería falso sobre el tic
    entero, que sí tiene evidencia validada entrando a Bayes."""
    from holonmed.cli import _lineas_sin_candidatas
    from holonmed.models import EstadoInfon, Infon

    sin_nada = ResultadoTic(
        paciente_id="t",
        texto_original="…",
        skill_activa="x",
        sin_candidatas=SinCandidatas.NADA_VALIDADO,
    )
    assert "NO SE VALIDÓ NI UN HALLAZGO" in "\n".join(_lineas_sin_candidatas(sin_nada))

    con_segunda_pasada = ResultadoTic(
        paciente_id="t",
        texto_original="…",
        skill_activa="x",
        sin_candidatas=SinCandidatas.NADA_VALIDADO,
        infones=[
            Infon(
                texto_origen="…",
                termino_propuesto="Fiebre",
                termino="Fiebre",
                estado=EstadoInfon.VALIDADO,
            )
        ],
    )
    texto = "\n".join(_lineas_sin_candidatas(con_segunda_pasada))

    assert "LA LECTURA INICIAL NO VALIDÓ" in texto
    assert "la segunda pasada" in texto
    assert "sí validó 1 hallazgo(s)" in texto
    assert "NO SE VALIDÓ NI UN HALLAZGO" not in texto


async def test_un_tic_que_no_valida_nada_lo_dice(entorno, tmp_path):  # noqa: F811
    """La alarma del tic, y la más fuerte de las tres.

    Φ=0 sale también con un protocolo sin cocientes o con uno irrelevante;
    «no se validó ni un hallazgo» no sale por ninguna otra razón. Hasta
    ahora había que deducirlo contando infones a ojo mientras el tic seguía
    a Bayes y a Φ como si tuviera de qué partir.
    """
    (tmp_path / "general_triage.md").write_text(
        SKILL_CON_AMBITO.format(ambito="386661006"), encoding="utf-8"
    )
    # Un término sin hint ni regla de laboratorio, con un score por debajo del
    # umbral de alerta: nada llega a VALIDADO. «Temperatura 38.5» no sirve
    # para esto, porque la regla de laboratorio del protocolo lo valida sin
    # pasar por el LLM ni por el índice.
    pipeline = entorno(
        LLMFalso(extraccion_de(TERMINO_SIN_HINT, "orina oscura")),
        IndexFalso(score=10.0, exacto=False),
    )
    resultado = await pipeline.ejecutar(
        "Orina oscura desde ayer", HolonPaciente(paciente_id="t")
    )

    assert not resultado.infones_validados
    assert resultado.sin_candidatas is SinCandidatas.NADA_VALIDADO


async def test_validado_sin_codigo_culpa_al_vocabulario(entorno, tmp_path):  # noqa: F811
    """Hay hallazgos y el grafo no tiene por dónde empezar.

    No es que el catálogo se quede corto: es que lo validado no está
    codificado. Se arregla por el vocabulario, y colapsado con la tercera
    mandaría a escribir un protocolo que no falta.
    """
    (tmp_path / "general_triage.md").write_text(
        SKILL_CON_AMBITO.format(ambito="386661006"), encoding="utf-8"
    )

    class SinCobertura(IndexFalso):
        def cobertura_de_grafo(self, concepto_ids):
            return set()

    pipeline = entorno(LLMFalso(), SinCobertura(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )

    assert resultado.infones_validados
    assert resultado.sin_candidatas is SinCandidatas.SIN_CODIFICAR


async def test_lo_que_el_catalogo_no_cubre_es_un_encargo(entorno, tmp_path):  # noqa: F811
    """La útil de las tres, y la única que no es un diagnóstico del sistema.

    Es la que el ACV habría dado si la validación hubiera funcionado: este
    paciente tiene hallazgos que tu catálogo no cubre, y aquí están. No
    basta con nombrar la causa —hay que nombrar los conceptos—, porque sin
    ellos la señal dice que falta un protocolo y no cuál.
    """
    (tmp_path / "general_triage.md").write_text(
        SKILL_CON_AMBITO.format(ambito="999999"), encoding="utf-8"
    )
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )

    assert resultado.infones_validados
    assert resultado.sin_candidatas is SinCandidatas.CATALOGO_NO_CUBRE
    assert resultado.conceptos_no_cubiertos == ["Fiebre"]


async def test_con_candidatas_no_hay_causa_que_dar(entorno, tmp_path):  # noqa: F811
    """`None` es «sí propuso», no un cuarto estado mudo."""
    (tmp_path / "general_triage.md").write_text(
        SKILL_CON_AMBITO.format(ambito="386661006"), encoding="utf-8"
    )
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar(
        "Temperatura 38.5", HolonPaciente(paciente_id="t")
    )

    assert resultado.sin_candidatas is None
