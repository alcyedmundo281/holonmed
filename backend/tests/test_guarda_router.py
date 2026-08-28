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
    IndexFalso,
    LLMFalso,
    entorno,
)

from holonmed.models import HolonPaciente, ResultadoTic

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

    assert resultado.skill_activa == "otro_protocolo"   # no se cambia nada
    assert resultado.triaje_en_candidatas is False       # y se registra


async def test_un_triaje_que_el_grafo_si_propuso_no_dispara_la_guarda(entorno, tmp_path):  # noqa: F811
    """El caso normal: la guarda calla cuando el prompt eligió a cuento."""
    (tmp_path / "general_triage.md").write_text(
        SKILL_CON_AMBITO.format(ambito="386661006"), encoding="utf-8"
    )
    pipeline = entorno(LLMFalso(), IndexFalso(score=95.0, exacto=True))
    resultado = await pipeline.ejecutar("Temperatura 38.5", HolonPaciente(paciente_id="t"))

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
