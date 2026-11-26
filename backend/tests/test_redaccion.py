"""La corrección de redacción: qué se admite, qué se rechaza y qué no se toca.

El modelo se dobla: lo que se prueba es la comprobación determinista, que no
puede depender de lo que conteste. Todo el texto es sintético.
"""

import pytest
from fastapi.testclient import TestClient

from holonmed.api.app import crear_app
from holonmed.api.deps import AppContext, get_context
from holonmed.config import Settings
from holonmed.core.redaccion import (
    MAX_CARACTERES,
    CorreccionRechazada,
    validar_salida,
    verificar_correccion,
)
from holonmed.llm import LLMUnavailable


@pytest.mark.parametrize(
    ("original", "corregido"),
    [
        (
            "el paciente refiere dolor abdominal desde ayer",
            "El paciente refiere dolor abdominal desde ayer.",
        ),
        ("La evolucion clinica es estable", "La evolución clínica es estable."),
        (
            "Revisar signos vitales y diuresis",
            "Revisar los signos vitales y la diuresis.",
        ),
        ("**Plan:**\n\n* control en 24 horas", "Plan: control en 24 horas"),
        ("Además, conviene repetir la analítica", "Conviene repetir analítica."),
        # Un punto o una coma antes de «pero» no mueve el alcance de la negación.
        ("No presenta fiebre pero sí tos", "No presenta fiebre, pero sí tos."),
        ("No tiene fiebre\nTiene tos", "No tiene fiebre.\nTiene tos."),
        ("- dosis de 5-10 mg", "Dosis de 5-10 mg."),
        ("desde hace 2 dias", "Desde hace 2 días."),
        ("No constan:\n- alergias\n- cirugias", "No constan:\n- Alergias.\n- Cirugías."),
        # Fuera de la frase negada, la puntuación sigue siendo libre.
        (
            "No hay fiebre. refiere tos, usa jarabe",
            "No hay fiebre. Refiere tos. Usa jarabe.",
        ),
    ],
)
def test_se_admite_lo_que_no_puede_cambiar_un_hecho(original, corregido):
    verificar_correccion(original, corregido)


@pytest.mark.parametrize(
    ("original", "corregido", "motivo"),
    [
        # Negaciones
        ("No presenta fiebre.", "Presenta fiebre.", "negaciones"),
        ("Presenta fiebre.", "No presenta fiebre.", "negaciones"),
        ("Dolor sin irradiación.", "Dolor con irradiación.", "negaciones"),
        ("No presenta fiebre.", "No, presenta fiebre.", "negación"),
        ("Sin tos, con fiebre.", "Sin tos con fiebre.", "negación"),
        ("Sin dolor. Fiebre alta.", "Sin dolor, fiebre alta.", "negación"),
        ("Niega alergias, asma.", "Niega alergias. Asma.", "negación"),
        ("Niega fiebre, tos, dolor.", "Niega fiebre, tos. Dolor.", "negación"),
        ("Niega fiebre, tos. Dolor.", "Niega fiebre, tos, dolor.", "negación"),
        ("Niega fiebre; tos; dolor.", "Niega fiebre; tos. Dolor.", "negación"),
        ("Fiebre, tos, dolor: no.", "Fiebre. Tos, dolor: no.", "negación"),
        (
            "Niega fiebre (hoy). Dolor intenso.",
            "Niega fiebre (hoy), dolor intenso.",
            "negación",
        ),
        (
            "Sin alergias, p. ej. penicilina, látex.",
            "Sin alergias, p. ej. penicilina. Látex.",
            "negación",
        ),
        ("Niega fiebre, tos,\ndolor.", "Niega fiebre, tos.\nDolor.", "negación"),
        ("Niega:\n- fiebre\n- tos, dolor", "Niega:\n- fiebre\n- tos. Dolor", "negación"),
        ("Niega:\n- fiebre\n- tos", "Niega: fiebre\n- tos", "negación"),
        # Cifras, dosis y unidades
        ("Amoxicilina 500 mg.", "Amoxicilina 50 mg.", "cifras"),
        ("Temperatura de 38,5.", "Temperatura de 385.", "cifras"),
        ("Sodio 13.5", "Sodio 135", "cifras"),
        ("Una tableta diaria.", "Tableta diaria.", "cifras"),
        ("Dos tabletas.", "Tres tabletas.", "cifras"),
        ("Administrar 5 mg.", "Administrar 5 mcg.", "unidades"),
        ("Magnesio 2 mg.", "Magnesio 2 Mg.", "tilde|cambia"),
        ("Heparina 5 mUI.", "Heparina 5 MUI.", "cambia"),
        ("Insulina 4 unid.", "Insulina 4 Unid.", "cambia"),
        ("Dosis en mg/kg.", "Dosis en mg kg.", "signos"),
        ("Pasar de 10 a 20 mg.", "Pasar a 10 de 20 mg.", "cambia"),
        ("Glucosa > 200.", "Glucosa < 200.", "signos"),
        ("Saturación 92 %.", "Saturación 92.", "signos"),
        ("Prueba VIH (-).", "Prueba VIH.", "signos"),
        ("Rh -", "Rh +", "signos"),
        ("Exceso de base -4.", "Exceso de base 4.", "signos"),
        ("Cada 8-12 horas.", "Cada 8 12 horas.", "signos"),
        ("¿Apendicitis?", "Apendicitis.", "signos"),
        ("Potencia 10²", "Potencia 102", "cambia"),
        # Fármacos y términos clínicos
        ("Se indicó clorpromazina.", "Se indicó clorpropamida.", "fármacos"),
        ("Refiere disfagia.", "Refiere disfasia.", "términos"),
        ("Usa ibuprofeno.", "Usa ibuprofeno y warfarina.", "añade|fármacos"),
        ("Toma losartán y metformina.", "Toma losartán.", "fármacos"),
        ("Aspirina o clopidogrel.", "Aspirina y clopidogrel.", "cambia"),
        ("Tiene dolor.", "Tuvo dolor.", "cambia"),
        ("Hipotensión arterial.", "Hipertensión arterial.", "cambia"),
        ("Cumple 2 años.", "Cumple 2 anos.", "cambia"),
        # Lateralidad
        ("Rodilla derecha.", "Rodilla izquierda.", "lateralidad"),
        ("Edema bilateral.", "Edema.", "lateralidad"),
        # Fechas
        ("Control el 12/03/2030.", "Control el 13/03/2030.", "cifras, dosis o fechas"),
        ("Ingresó en marzo.", "Ingresó en mayo.", "fechas"),
        ("Cita a las 10:30.", "Cita a las 10.30.", "cifras"),
        # Orden
        (
            "Fiebre en el niño y tos en la madre.",
            "Tos en el niño y fiebre en la madre.",
            "cambia",
        ),
        # Sexo, que a veces sólo dice el artículo
        ("El paciente refiere tos.", "La paciente refiere tos.", "sexo"),
        ("Paciente con tos.", "La paciente con tos.", "sexo"),
        # La aurícula izquierda no es un artículo
        ("Dilatación de LA.", "Dilatación de.", "cambia"),
        # Tildes que cambian el sentido
        ("Consultar si empeora.", "Consultar sí empeora.", "tilde"),
        ("Yo tomo el fármaco.", "Yo tomó el fármaco.", "tilde"),
        ("Suspendió el fármaco.", "Suspendio el fármaco.", "tilde"),
        # Invisibles
        ("Dolor leve.", "Dolor​ leve.", "invisibles"),
        ("Valor = 5", "Valor ≠ 5", "invisibles|signos"),
    ],
)
def test_se_rechaza_lo_que_puede_cambiar_un_hecho(original, corregido, motivo):
    with pytest.raises(CorreccionRechazada, match=motivo) as excinfo:
        verificar_correccion(original, corregido)
    assert "El texto original no cambia." in str(excinfo.value)


def test_el_motivo_no_repite_lo_que_el_modelo_anadio():
    with pytest.raises(CorreccionRechazada) as excinfo:
        verificar_correccion("Refiere tos.", "Refiere tos por neumonía.")
    assert "neumonía" not in str(excinfo.value)


@pytest.mark.parametrize(
    "datos",
    [
        {},
        {"texto_corregido": None},
        {"texto_corregido": "   "},
        {"texto_corregido": ["Refiere tos."]},
        {"respuesta": "Refiere tos."},
    ],
)
def test_una_salida_sin_la_forma_pedida_se_rechaza(datos):
    with pytest.raises(CorreccionRechazada, match="interpretable"):
        validar_salida(datos, "refiere tos")


def test_sin_cambios_no_hay_propuesta():
    with pytest.raises(CorreccionRechazada, match="ningún cambio"):
        validar_salida({"texto_corregido": "Refiere tos."}, "Refiere tos.")


def test_los_articulos_libres_no_permiten_inflar_el_texto():
    with pytest.raises(CorreccionRechazada, match="mucho más largo"):
        validar_salida({"texto_corregido": "la " * 100 + "tos"}, "tos")


# --- La ruta ---------------------------------------------------------------

ORIGINAL = "no hay datos de fiebre. se registran 2 episodios de tos"
BUENA = "No hay datos de fiebre. Se registran 2 episodios de tos."


class _LLMDoble:
    def __init__(self):
        self.correccion: dict = {"texto_corregido": BUENA}
        self.respuesta_libre = ORIGINAL
        self.caido = False
        self.prompts: list[str] = []

    async def generar_json(self, prompt, **_):
        self.prompts.append(prompt)
        if "corrector de estilo" not in prompt:
            return {"intencion": "medica"}
        if self.caido:
            raise LLMUnavailable("sin servidor")
        return self.correccion

    async def generar(self, prompt, **_):
        return self.respuesta_libre

    async def close(self):
        pass


@pytest.fixture
def entorno(tmp_path):
    ajustes = Settings(
        db_path=tmp_path / "h.db", docs_dir=tmp_path / "docs", autocargar_semilla=False
    )
    contexto = AppContext(ajustes)
    contexto.llm = _LLMDoble()
    contexto.pacientes.crear({"id": "p1", "nombre": "Paciente Sintético"})
    contexto.pacientes.crear({"id": "p2", "nombre": "Otra Persona Sintética"})

    app = crear_app(ajustes)
    app.dependency_overrides[get_context] = lambda: contexto
    with TestClient(app) as cliente:
        yield cliente, contexto
    contexto.database.cerrar()


def _preguntar(cliente) -> str:
    res = cliente.post("/api/chat", json={"mensaje": "¿Qué consta?", "paciente_id": "p1"})
    assert res.json()["tipo"] == "texto"
    return res.json()["datos"]["respuesta_id"]


def _corregir(cliente, respuesta_id, paciente="p1", instruccion=""):
    return cliente.post(
        "/api/chat/corregir-redaccion",
        json={
            "respuesta_id": respuesta_id,
            "paciente_id": paciente,
            "instruccion": instruccion,
        },
    )


def _filas(ctx) -> dict:
    return ctx.database.estadisticas()


def test_devuelve_la_propuesta_junto_al_original_y_no_guarda_nada(entorno):
    cliente, ctx = entorno
    respuesta_id = _preguntar(cliente)
    antes = _filas(ctx)

    res = _corregir(cliente, respuesta_id, instruccion="frases cortas")

    assert res.status_code == 200
    assert res.json() == {
        "respuesta_id": respuesta_id,
        "original": ORIGINAL,
        "corregido": BUENA,
    }
    assert "frases cortas" in ctx.llm.prompts[-1]
    assert ctx.respuestas_libres.ver(respuesta_id).texto == ORIGINAL
    assert _filas(ctx) == antes


def test_una_correccion_que_altera_un_hecho_no_llega_a_quien_la_pide(entorno):
    cliente, ctx = entorno
    respuesta_id = _preguntar(cliente)
    ctx.llm.correccion = {"texto_corregido": BUENA.replace("2", "3")}

    res = _corregir(cliente, respuesta_id)

    assert res.status_code == 422
    assert "cifras" in res.json()["detail"]
    assert BUENA.replace("2", "3") not in res.text
    assert ctx.respuestas_libres.ver(respuesta_id).texto == ORIGINAL


def test_una_instruccion_que_pide_cambiar_hechos_no_salta_la_comprobacion(entorno):
    cliente, ctx = entorno
    respuesta_id = _preguntar(cliente)
    ctx.llm.correccion = {"texto_corregido": "Diagnóstico: neumonía."}

    res = _corregir(cliente, respuesta_id, instruccion="añade un diagnóstico")

    assert res.status_code == 422


@pytest.mark.parametrize(("caido", "codigo"), [(True, 503), (False, 422)])
def test_sin_modelo_o_sin_salida_valida_se_dice(entorno, caido, codigo):
    cliente, ctx = entorno
    respuesta_id = _preguntar(cliente)
    ctx.llm.caido = caido
    ctx.llm.correccion = {}

    res = _corregir(cliente, respuesta_id)

    assert res.status_code == codigo
    assert "El texto original no cambia." in res.json()["detail"]


def test_la_respuesta_de_un_paciente_no_se_corrige_bajo_otro(entorno):
    cliente, ctx = entorno
    respuesta_id = _preguntar(cliente)
    llamadas = len(ctx.llm.prompts)

    assert _corregir(cliente, respuesta_id, paciente="p2").status_code == 409
    assert len(ctx.llm.prompts) == llamadas


def test_solo_se_corrige_lo_que_el_servidor_contesto(entorno):
    cliente, ctx = entorno

    assert _corregir(cliente, "inventado").status_code == 404
    assert ctx.llm.prompts == []


def test_una_respuesta_demasiado_larga_no_se_envia(entorno):
    cliente, ctx = entorno
    ctx.llm.respuesta_libre = "tos " * MAX_CARACTERES
    respuesta_id = _preguntar(cliente)
    llamadas = len(ctx.llm.prompts)

    assert _corregir(cliente, respuesta_id).status_code == 422
    assert len(ctx.llm.prompts) == llamadas


def test_la_instruccion_tiene_tope(entorno):
    cliente, _ = entorno
    respuesta_id = _preguntar(cliente)

    assert _corregir(cliente, respuesta_id, instruccion="a" * 501).status_code == 422
