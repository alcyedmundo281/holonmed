"""Tests del almacén SQLite y del grafo ontológico.

Se ejercitan sobre una base temporal real, no sobre dobles: el valor de
estas piezas está justo en el SQL, así que simularlo no probaría nada.
"""

import pytest

from holonmed.core.terminology import TerminologyIndex, VocabularyLoader
from holonmed.db import Database, GraphRepo, PacienteRepo, TicRepo, normalizar
from holonmed.models import EstadoInfon, Infon, ResultadoTic

VOCABULARIO = {
    "conceptos": [
        {"codigo": "T:0", "termino": "Hallazgo clínico"},
        {"codigo": "T:1", "termino": "Alteración analítica", "padre": "T:0"},
        {"codigo": "T:2", "termino": "Alteración enzimática", "padre": "T:1"},
        {
            "codigo": "T:3",
            "termino": "Hiperlipasemia",
            "padre": "T:2",
            "sinonimos": ["lipasa elevada", "lipasa alta"],
            "icd10": "K85.9",
        },
        {"codigo": "T:4", "termino": "Hiperamilasemia", "padre": "T:2"},
        {"codigo": "T:5", "termino": "Fiebre", "padre": "T:0", "sinonimos": ["hipertermia"]},
    ]
}


@pytest.fixture
def entorno(tmp_path):
    import json

    ruta_vocab = tmp_path / "vocab.json"
    ruta_vocab.write_text(json.dumps(VOCABULARIO), encoding="utf-8")

    db = Database(tmp_path / "prueba.db")
    VocabularyLoader(db).cargar_semilla(ruta_vocab)
    grafo = GraphRepo(db)
    return db, grafo, TerminologyIndex(db, grafo)


# --- Normalización ----------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Hipocalcemia", "hipocalcemia"),
        ("  FIEBRE  ", "fiebre"),
        ("Dolor Epigástrico", "dolor epigastrico"),
        ("Vómitos", "vomitos"),
    ],
)
def test_normalizar(entrada, esperado):
    assert normalizar(entrada) == esperado


# --- Índice terminológico ---------------------------------------------


def test_el_vocabulario_se_carga(entorno):
    _, _, index = entorno
    assert index.disponible()
    assert index.sistemas_cargados() == {"holonmed": 6}


def test_la_carga_es_idempotente(entorno, tmp_path):
    import json

    db, grafo, index = entorno
    ruta = tmp_path / "otra.json"
    ruta.write_text(json.dumps(VOCABULARIO), encoding="utf-8")
    VocabularyLoader(db).cargar_semilla(ruta)
    # Reejecutar no debe duplicar conceptos ni sinónimos.
    assert index.sistemas_cargados() == {"holonmed": 6}


def test_busqueda_exacta_ignora_acentos_y_mayusculas(entorno):
    _, _, index = entorno
    for variante in ["Hiperlipasemia", "hiperlipasemia", "  HIPERLIPASEMIA "]:
        assert index.buscar_exacto(variante).codigo == "T:3"


def test_un_sinonimo_lleva_al_termino_preferente(entorno):
    _, _, index = entorno
    match = index.buscar_exacto("lipasa elevada")
    assert match.codigo == "T:3"
    assert match.termino == "Hiperlipasemia"  # se devuelve el preferente


def test_la_recuperacion_difusa_tolera_erratas(entorno):
    _, _, index = entorno
    candidatos = index.buscar_candidatos("lipasa elevad")
    assert candidatos
    assert candidatos[0].codigo == "T:3"


def test_un_termino_inexistente_no_devuelve_nada(entorno):
    _, _, index = entorno
    assert index.buscar_candidatos("zzzz qqqq xxxx") == []


def test_el_texto_libre_no_rompe_la_consulta_fts(entorno):
    """FTS5 tiene sintaxis propia y el texto viene de un LLM."""
    _, _, index = entorno
    for peligroso in ['fiebre "OR" NEAR', "lipasa*", "-fiebre", '""', "AND OR NOT"]:
        index.buscar_candidatos(peligroso)  # no debe lanzar


def test_los_metadatos_traen_cie10_y_linaje(entorno):
    _, _, index = entorno
    concepto = index.buscar_exacto("Hiperlipasemia")
    cie10, linaje = index.metadatos(concepto.concepto_id)
    assert cie10 == "K85.9"
    assert linaje == "Alteración enzimática"


# --- Grafo ------------------------------------------------------------


def test_los_ancestros_salen_ordenados_por_cercania(entorno):
    _, grafo, index = entorno
    concepto = index.buscar_exacto("Hiperlipasemia")
    ancestros = [a["termino"] for a in grafo.ancestros(concepto.concepto_id)]
    assert ancestros == ["Alteración enzimática", "Alteración analítica", "Hallazgo clínico"]


def test_un_concepto_raiz_no_tiene_ancestros(entorno):
    _, grafo, index = entorno
    raiz = index.buscar_exacto("Hallazgo clínico")
    assert grafo.ancestros(raiz.concepto_id) == []


def test_materializar_el_cierre_es_idempotente(entorno):
    _, grafo, index = entorno
    concepto = index.buscar_exacto("Hiperlipasemia")
    primera = grafo.materializar_ancestros(concepto.concepto_id)
    segunda = grafo.materializar_ancestros(concepto.concepto_id)
    assert primera == 3
    assert segunda == 0  # ya estaba, no se reescribe


def test_los_descendientes_incluyen_toda_la_rama(entorno):
    db, grafo, index = entorno
    for termino in ["Hiperlipasemia", "Hiperamilasemia", "Fiebre"]:
        grafo.materializar_ancestros(index.buscar_exacto(termino).concepto_id)

    bajo_enzimas = grafo.descendientes_de("T:2", "holonmed")
    assert index.buscar_exacto("Hiperlipasemia").concepto_id in bajo_enzimas
    assert index.buscar_exacto("Hiperamilasemia").concepto_id in bajo_enzimas
    assert index.buscar_exacto("Fiebre").concepto_id not in bajo_enzimas


# --- Persistencia clínica ---------------------------------------------


def _infon(termino, concepto_id, estado=EstadoInfon.VALIDADO, codigo="T:3"):
    return Infon(
        texto_origen="cita",
        termino_propuesto=termino,
        termino=termino,
        codigo=codigo,
        sistema="holonmed",
        concepto_id=concepto_id,
        estado=estado,
        confianza=90.0,
    )


def test_un_tic_se_guarda_con_todos_sus_infones(entorno):
    db, grafo, index = entorno
    tics = TicRepo(db, grafo)
    cid = index.buscar_exacto("Hiperlipasemia").concepto_id

    resultado = ResultadoTic(paciente_id="p1", texto_original="…", skill_activa="prueba")
    resultado.infones = [
        _infon("Hiperlipasemia", cid),
        _infon("Ruido", None, EstadoInfon.RUIDO, None),
    ]
    tic_id = tics.guardar(resultado)

    assert tic_id
    completo = tics.tic_completo(tic_id)
    # Los descartados también se guardan: sin ellos no se puede auditar
    # si el validador está rechazando de más.
    assert len(completo["infones"]) == 2


def test_la_linea_de_tiempo_solo_trae_validados(entorno):
    db, grafo, index = entorno
    tics = TicRepo(db, grafo)
    cid = index.buscar_exacto("Hiperlipasemia").concepto_id

    resultado = ResultadoTic(paciente_id="p1", texto_original="…", skill_activa="prueba")
    resultado.infones = [
        _infon("Hiperlipasemia", cid),
        _infon("Ruido", None, EstadoInfon.RUIDO, None),
    ]
    tics.guardar(resultado)

    linea = tics.linea_tiempo("p1")
    assert len(linea) == 1
    assert linea[0].termino == "Hiperlipasemia"


def test_guardar_un_tic_materializa_el_cierre(entorno):
    """El cierre se construye solo, al usar el concepto por primera vez."""
    db, grafo, index = entorno
    tics = TicRepo(db, grafo)
    cid = index.buscar_exacto("Hiperlipasemia").concepto_id

    assert db.estadisticas()["ancestros_materializados"] == 0

    resultado = ResultadoTic(paciente_id="p1", texto_original="…", skill_activa="prueba")
    resultado.infones = [_infon("Hiperlipasemia", cid)]
    tics.guardar(resultado)

    assert db.estadisticas()["ancestros_materializados"] == 3


def test_la_cohorte_encuentra_por_ancestro(entorno):
    """La consulta que justifica el grafo: buscar por rama, no por término."""
    db, grafo, index = entorno
    tics = TicRepo(db, grafo)

    for paciente, termino in [("p1", "Hiperlipasemia"), ("p2", "Hiperamilasemia"), ("p3", "Fiebre")]:
        cid = index.buscar_exacto(termino).concepto_id
        r = ResultadoTic(paciente_id=paciente, texto_original="…", skill_activa="prueba")
        r.infones = [_infon(termino, cid)]
        tics.guardar(r)

    # Nadie escribió "alteración enzimática" en ninguna nota; el grafo lo deduce.
    cohorte = {f["id"] for f in grafo.cohorte("T:2", "holonmed")}
    assert cohorte == {"p1", "p2"}


def test_la_lista_de_problemas_deduplica_y_fecha(entorno):
    db, grafo, index = entorno
    tics = TicRepo(db, grafo)
    cid = index.buscar_exacto("Fiebre").concepto_id

    for _ in range(3):
        r = ResultadoTic(paciente_id="p1", texto_original="…", skill_activa="prueba")
        r.infones = [_infon("Fiebre", cid, codigo="T:5")]
        tics.guardar(r)

    problemas = tics.lista_problemas("p1")
    assert len(problemas) == 1
    assert problemas[0]["apariciones"] == 3
    assert problemas[0]["primera"] <= problemas[0]["ultima"]


def test_un_paciente_efimero_no_pierde_su_tic(entorno):
    """Procesar sin dar de alta al paciente debe funcionar igual."""
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    r = ResultadoTic(paciente_id="nunca-creado", texto_original="…", skill_activa="prueba")
    r.infones = [_infon("Algo", None, EstadoInfon.RUIDO, None)]
    assert tics.guardar(r) is not None


def test_solo_se_actualizan_campos_de_la_lista_blanca(entorno):
    """`campo` puede venir de la salida de un LLM."""
    db, _, _ = entorno
    repo = PacienteRepo(db)
    repo.crear({"id": "p1", "nombre": "Prueba"})

    assert repo.actualizar("p1", "nombre", "Nuevo") is True
    assert repo.actualizar("p1", "id", "otro") is False
    assert repo.actualizar("p1", "creado", "2020") is False
    assert repo.obtener("p1").nombre == "Nuevo"
