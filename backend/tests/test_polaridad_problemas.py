"""Lo negado no es un problema, y negarlo después no lo resuelve.

Un infón «Sin ictericia» está VALIDADO —es evidencia, y resta— pero su
término es «Ictericia». Toda consulta que filtre sólo por estado, o que lea
el término sin la polaridad, afirma lo que la nota negó.

Todo el texto es sintético.
"""

import pytest
from fastapi.testclient import TestClient

from holonmed.api.app import crear_app
from holonmed.api.deps import AppContext, get_context
from holonmed.api.routes.chat import _contexto_de_hallazgos
from holonmed.config import Settings
from holonmed.core.sintesis import formatear_fondo, sintetizar
from holonmed.models import EstadoInfon, Infon, Polaridad, ResultadoTic, TipoNota

PACIENTE = "sintetico"


def _infon(termino, presente=True, cita="", codigo=None, estado=EstadoInfon.VALIDADO):
    return Infon(
        texto_origen=cita or (termino if presente else f"Sin {termino.lower()}"),
        termino_propuesto=termino.lower(),
        termino=termino,
        polaridad=Polaridad.PRESENTE if presente else Polaridad.AUSENTE,
        codigo=codigo or f"T:{termino}",
        sistema="holonmed",
        estado=estado,
        confianza=95.0,
    )


@pytest.fixture
def contexto(tmp_path):
    ctx = AppContext(Settings(db_path=tmp_path / "p.db", autocargar_semilla=False))
    yield ctx
    ctx.database.cerrar()


@pytest.fixture
def cliente(contexto):
    app = crear_app(contexto.settings)
    app.dependency_overrides[get_context] = lambda: contexto
    with TestClient(app) as cliente:
        yield cliente


def _guardar(ctx, *infones, episodio=None, tipo=TipoNota.EVOLUCION):
    tic_id = ctx.tics.guardar(
        ResultadoTic(
            paciente_id=PACIENTE,
            episodio_id=episodio,
            tipo=tipo,
            texto_original="; ".join(i.texto_origen for i in infones) or "nota",
            skill_activa="general_triage",
            infones=list(infones),
        )
    )
    assert tic_id is not None
    return tic_id


def _terminos(ctx):
    return [p["termino"] for p in ctx.tics.lista_problemas(PACIENTE)]


# --- La lista ----------------------------------------------------------


def test_un_hallazgo_negado_no_abre_un_problema(contexto):
    _guardar(contexto, _infon("Ictericia", presente=False))

    assert _terminos(contexto) == []


def test_una_ausencia_posterior_no_resuelve_ni_cuenta_como_aparicion(contexto):
    presente = _infon("Fiebre")
    _guardar(contexto, presente)
    ausente = _infon("Fiebre", presente=False)
    _guardar(contexto, ausente)

    (problema,) = contexto.tics.lista_problemas(PACIENTE)

    assert problema["apariciones"] == 1
    assert problema["primera"] == problema["ultima"] == presente.timestamp
    assert problema["consta_ausente"] == ausente.timestamp


def test_la_ausencia_anterior_o_ya_superada_no_marca_el_problema(contexto):
    _guardar(contexto, _infon("Fiebre", presente=False))
    _guardar(contexto, _infon("Fiebre"))
    assert contexto.tics.lista_problemas(PACIENTE)[0]["consta_ausente"] is None

    _guardar(contexto, _infon("Fiebre", presente=False))
    _guardar(contexto, _infon("Fiebre"))
    assert contexto.tics.lista_problemas(PACIENTE)[0]["consta_ausente"] is None


def test_la_contradiccion_dentro_de_una_misma_nota_se_muestra(contexto):
    """El orden de los infones de un tic es el de extracción, no el clínico."""
    ausente = _infon("Fiebre", presente=False)
    _guardar(contexto, ausente, _infon("Fiebre"))

    (problema,) = contexto.tics.lista_problemas(PACIENTE)
    assert problema["consta_ausente"] == ausente.timestamp


@pytest.mark.parametrize("estado", [EstadoInfon.ALERTA, EstadoInfon.RUIDO])
def test_una_ausencia_sin_validar_no_marca_nada(contexto, estado):
    _guardar(contexto, _infon("Fiebre"))
    _guardar(contexto, _infon("Fiebre", presente=False, estado=estado))

    assert contexto.tics.lista_problemas(PACIENTE)[0]["consta_ausente"] is None


def test_la_ausencia_sigue_en_la_historia(contexto):
    _guardar(contexto, _infon("Fiebre"))
    tic = _guardar(contexto, _infon("Fiebre", presente=False))

    polaridades = {i.polaridad for i in contexto.tics.linea_tiempo(PACIENTE)}
    assert polaridades == {Polaridad.PRESENTE, Polaridad.AUSENTE}
    assert contexto.tics.tic_completo(tic)["infones"][0]["polaridad"] == "ausente"


# --- Rutas -------------------------------------------------------------


def test_problemas_y_triaje_ignoran_lo_negado(contexto, cliente):
    # Control: presente, este término sí agrupa. Sin él, un triaje vacío
    # no probaría nada.
    control = contexto.pipeline.skills.triaje_agrupar([{"termino": "Dolor epigástrico"}])
    assert control

    _guardar(contexto, _infon("Dolor epigástrico", presente=False))

    assert cliente.get(f"/api/pacientes/{PACIENTE}/problemas").json() == []
    assert cliente.get(f"/api/pacientes/{PACIENTE}/triage").json() == []


def _abrir_con_base(ctx, cliente, *infones):
    respuesta = cliente.post("/api/episodios", json={"paciente_id": PACIENTE})
    episodio = respuesta.json()["episodio_id"]
    _guardar(ctx, *infones, episodio=episodio, tipo=TipoNota.BASE)
    return episodio


def test_la_nota_impresa_escribe_lo_negado_como_ausencia(contexto, cliente):
    episodio = _abrir_con_base(
        contexto,
        cliente,
        _infon("Fiebre"),
        # La cita no trae la negación: la nota no puede depender de ella.
        _infon("Ictericia", presente=False, cita="ictericia"),
    )

    fondo = cliente.get(f"/api/episodios/{episodio}/fondo").json()
    assert [b["problema"] for b in fondo["bloques"]] == ["Fiebre"]
    assert fondo["negativos"] == ["Ictericia («ictericia»)"]
    assert fondo["sin_sintetizar"] == []

    nota = cliente.post(f"/api/episodios/{episodio}/imprimir?firmante=Firma%20X")
    assert nota.status_code == 201
    texto = nota.json()["texto"]
    assert "Problema: Ictericia" not in texto
    assert "Ausencias documentadas (no son problemas): Ictericia" in texto
    assert "apareció «Fiebre»" in texto


def test_tras_imprimir_una_ausencia_no_se_anuncia_como_resuelta(contexto, cliente):
    episodio = _abrir_con_base(
        contexto, cliente, _infon("Fiebre"), _infon("Ictericia", presente=False)
    )
    url = f"/api/episodios/{episodio}/imprimir?firmante=Firma%20X"
    assert cliente.post(url).status_code == 201
    _guardar(contexto, _infon("Fiebre", presente=False), episodio=episodio)

    fondo = cliente.get(f"/api/episodios/{episodio}/fondo").json()

    assert fondo["impresion"]["motivos"] == []
    (bloque,) = fondo["bloques"]
    assert bloque["problema"] == "Fiebre"
    assert bloque["ausente"] == ["Fiebre («Sin fiebre»)"]
    # La narrativa no declara «O:», así que la cita queda sin clasificar.
    assert bloque["sin_clasificar"] == ["Fiebre"]
    assert bloque["objetivo"] == []


def test_el_resumen_vivo_no_afirma_lo_negado(contexto):
    _guardar(contexto, _infon("Ictericia", presente=False, cita="ictericia"))

    resumen = contexto.pacientes.obtener(PACIENTE).resumen_vivo

    assert resumen == "Ausencias documentadas (no son problemas): Ictericia («ictericia»)"


def test_una_ausencia_derivada_no_sale_como_derivado():
    infon = _infon("Pancreatitis aguda", presente=False).model_copy(
        update={"procedencia": "derivado"}
    )

    fondo = sintetizar([infon], ["Pancreatitis aguda"])

    assert fondo.bloques[0].derivado == ()
    assert "Consta ausente: Pancreatitis aguda" in formatear_fondo(fondo)


# --- Otras lecturas de `infon` -----------------------------------------


def _concepto(ctx, codigo, termino):
    cx = ctx.database.conexion()
    cursor = cx.execute(
        "INSERT INTO concepto (codigo, sistema, termino) VALUES (?, 'holonmed', ?)",
        (codigo, termino),
    )
    cx.commit()
    return cursor.lastrowid


def test_cohorte_y_grafo_no_incluyen_lo_negado(contexto):
    cid = _concepto(contexto, "T:ICT", "Ictericia")
    ligado = {"concepto_id": cid}
    _guardar(contexto, _infon("Ictericia", presente=False).model_copy(update=ligado))

    assert contexto.grafo.cohorte("T:ICT", "holonmed") == []
    assert contexto.grafo.vecindad(PACIENTE) == {"nodos": [], "aristas": []}

    # Control: presente entra, y el conteo es sólo de lo presente.
    _guardar(contexto, _infon("Ictericia").model_copy(update=ligado))

    assert contexto.grafo.cohorte("T:ICT", "holonmed")[0]["hallazgos"] == 1
    assert contexto.grafo.vecindad(PACIENTE)["nodos"][0]["peso"] == 1


def test_lo_negado_en_el_historial_no_es_un_factor_a_priori(contexto):
    _guardar(contexto, _infon("Alcoholismo", presente=False))
    holon = contexto.pacientes.obtener_o_efimero(PACIENTE)
    holon.linea_tiempo = contexto.tics.linea_tiempo(PACIENTE)

    assert "alcoholismo" not in holon.metadatos_para_bayes()["antecedentes"]


def test_el_contexto_del_chat_separa_las_ausencias():
    texto = _contexto_de_hallazgos(
        [_infon("Fiebre"), _infon("Ictericia", presente=False)]
    )
    presentes, ausentes = texto.split("\n")

    assert presentes == "HALLAZGOS VALIDADOS PREVIOS: Fiebre"
    assert ausentes.startswith("AUSENCIAS DOCUMENTADAS")
    assert "Ictericia" in ausentes


def test_el_contexto_del_chat_sin_nada_lo_dice():
    assert _contexto_de_hallazgos([]) == "Sin hallazgos previos registrados."
