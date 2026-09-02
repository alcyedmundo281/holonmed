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
        {
            "codigo": "T:5",
            "termino": "Fiebre",
            "padre": "T:0",
            "sinonimos": ["hipertermia"],
        },
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
    assert ancestros == [
        "Alteración enzimática",
        "Alteración analítica",
        "Hallazgo clínico",
    ]


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

    for paciente, termino in [
        ("p1", "Hiperlipasemia"),
        ("p2", "Hiperamilasemia"),
        ("p3", "Fiebre"),
    ]:
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
    r = ResultadoTic(
        paciente_id="nunca-creado", texto_original="…", skill_activa="prueba"
    )
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


# --- Origen: interconexión entre actores del entorno clínico -----------


def _tic(paciente="p1", origen=None, resumen="", actor=None):
    from holonmed.models import OrigenTic

    r = ResultadoTic(
        paciente_id=paciente,
        texto_original="…",
        skill_activa="prueba",
        origen=origen or OrigenTic.CONSULTA,
        actor=actor,
        resumen=resumen,
    )
    return r


def test_el_origen_por_defecto_es_la_consulta(entorno):
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    tics.guardar(_tic())
    assert tics.historial("p1")[0]["origen"] == "consulta"


def test_cada_actor_queda_registrado_en_su_tic(entorno):
    """Un informe de laboratorio y una nota dictada alimentan la misma
    historia, pero no son la misma clase de evidencia."""
    from holonmed.models import OrigenTic

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    tics.guardar(_tic(origen=OrigenTic.CONSULTA))
    tics.guardar(_tic(origen=OrigenTic.LABORATORIO, actor="lab-central"))
    tics.guardar(_tic(origen=OrigenTic.FARMACIA, resumen="Receta: Paracetamol"))

    origenes = {f["origen"]: f["tics"] for f in tics.por_origen("p1")}
    assert origenes == {"consulta": 1, "laboratorio": 1, "farmacia": 1}


def test_el_historial_se_filtra_por_origen(entorno):
    from holonmed.models import OrigenTic

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    tics.guardar(_tic(origen=OrigenTic.CONSULTA))
    tics.guardar(_tic(origen=OrigenTic.LABORATORIO, actor="lab-central"))

    solo_lab = tics.historial("p1", origen="laboratorio")
    assert len(solo_lab) == 1
    assert solo_lab[0]["actor"] == "lab-central"
    assert len(tics.historial("p1")) == 2


def test_una_receta_queda_en_la_historia(entorno):
    """Antes una receta sólo producía un PDF y el fármaco prescrito
    desaparecía del registro."""
    from holonmed.db import DocumentoRepo
    from holonmed.models import OrigenTic

    db, grafo, _ = entorno
    tics, docs = TicRepo(db, grafo), DocumentoRepo(db)

    tic_id = tics.guardar(
        _tic(origen=OrigenTic.FARMACIA, resumen="Receta: Amoxicilina 500 mg")
    )
    docs.registrar(
        "p1",
        tipo="receta",
        archivo="receta_p1.pdf",
        datos={"items": [{"farmaco": "Amoxicilina", "concentracion": "500 mg"}]},
        tic_id=tic_id,
    )

    recetas = docs.listar("p1", tipo="receta")
    assert len(recetas) == 1
    assert recetas[0]["datos"]["items"][0]["farmaco"] == "Amoxicilina"
    # Y aparece en la línea de tiempo, no sólo como archivo suelto.
    entrada = tics.historial("p1", origen="farmacia")[0]
    assert entrada["documentos"] == 1
    assert "Amoxicilina" in entrada["resumen"]


def test_una_base_anterior_se_migra_sin_perder_datos(tmp_path):
    """`CREATE TABLE IF NOT EXISTS` no toca una tabla existente, así que
    las columnas nuevas hay que añadirlas explícitamente."""
    import sqlite3

    ruta = tmp_path / "antigua.db"
    cx = sqlite3.connect(ruta)
    cx.executescript(
        """
        CREATE TABLE paciente (id TEXT PRIMARY KEY, nombre TEXT NOT NULL,
            edad INTEGER, sexo TEXT, telefono TEXT,
            antecedentes TEXT NOT NULL DEFAULT '', creado TEXT NOT NULL);
        CREATE TABLE tic (id INTEGER PRIMARY KEY, paciente_id TEXT NOT NULL,
            timestamp TEXT NOT NULL, skill TEXT NOT NULL,
            texto_original TEXT NOT NULL, resumen TEXT NOT NULL DEFAULT '',
            inferencia TEXT);
        INSERT INTO paciente VALUES ('p1','Antiguo',NULL,NULL,NULL,'','2026-01-01');
        INSERT INTO tic VALUES (1,'p1','2026-01-01','vieja','texto','resumen',NULL);
        """
    )
    cx.commit()
    cx.close()

    db = Database(ruta)
    assert db.disponible

    columnas = {f[1] for f in db.conexion().execute("PRAGMA table_info(tic)")}
    assert {"origen", "actor"} <= columnas

    # El tic anterior sigue ahí y adopta el origen por defecto.
    fila = (
        db.conexion().execute("SELECT origen, resumen FROM tic WHERE id = 1").fetchone()
    )
    assert fila["origen"] == "consulta"
    assert fila["resumen"] == "resumen"


# --- La persistencia de la competencia y del segundo eje ---------------
#
# La §8 de VEREDICTO.md declaraba el hueco: el tic guardaba `skill TEXT`
# —el nombre, sin la versión— y ni `acoplamiento` ni `veredicto`. Con la
# competencia abductiva había además una comparación entera que registrar.


def _resultado_con_competencia(**extra):
    from holonmed.models import CandidataAbductiva

    r = ResultadoTic(
        paciente_id="p1",
        texto_original="dolor en FID",
        skill_activa="apendicitis",
        skill_version="3.1",
        **extra,
    )
    r.competencia = [
        CandidataAbductiva(
            skill="apendicitis",
            clave=0.87,
            anclaje=0.9,
            cobertura=0.74,
            explicacion=1.0,
            admitida=True,
        ),
        CandidataAbductiva(
            skill="diverticulitis", clave=0.25, anclaje=0.87, admitida=True
        ),
        CandidataAbductiva(
            skill="colecistitis", vetada=True, motivo_veto="colecistectomía en 2019"
        ),
    ]
    r.ganadora_abductiva = "apendicitis"
    r.triaje_coincide = True
    r.aviso_competencia = (
        "La hipótesis que mejor encaja es 'gastroenteritis', coseno 0.95, y no "
        "compite porque su protocolo no cita sus cocientes (α = 0.00)."
    )
    return r


def test_el_tic_guarda_la_competencia_entera_y_no_solo_la_ganadora(entorno):
    """«Se consideró diverticulitis y sacó 0.25» ES la traza de auditoría.

    Guardar sólo la ganadora deja al sistema mostrando una conclusión sin
    poder decir contra qué compitió, que es pedir que se confíe en el orden.
    """
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    tic_id = tics.guardar(_resultado_con_competencia())

    leido = tics.tic_completo(tic_id)
    assert [c["skill"] for c in leido["competencia"]] == [
        "apendicitis",
        "diverticulitis",
        "colecistitis",
    ]
    perdedora = leido["competencia"][1]
    assert perdedora["clave"] == 0.25
    vetada = leido["competencia"][2]
    assert vetada["vetada"] and "colecistectomía" in vetada["motivo_veto"]
    assert leido["ganadora_abductiva"] == "apendicitis"
    # Y el aviso, que es la mitad del diseño: si la compuerta actúa callada
    # el sistema trata otra cosa sin dejar constancia de por qué.
    assert "gastroenteritis" in leido["aviso_competencia"]


def test_el_tic_guarda_la_version_del_protocolo_y_no_solo_su_nombre(entorno):
    """Es la columna que convierte recomputar en auditar.

    Sin ella, volver a pasar los infones de aquel día por el protocolo que
    hay hoy responde a una pregunta distinta de la que se quería hacer.
    """
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    leido = tics.tic_completo(tics.guardar(_resultado_con_competencia()))

    assert leido["skill"] == "apendicitis"
    assert leido["skill_version"] == "3.1"


def test_el_acoplamiento_y_el_veredicto_sobreviven_al_viaje(entorno):
    """El hueco que la §8 de VEREDICTO.md declaraba, cerrado."""
    from holonmed.core.acoplamiento import MedidorDeAcoplamiento
    from holonmed.core.skills import Skill

    protocolo = Skill(
        "apendicitis",
        "---\ntitulo: Apendicitis\nsignos:\n  - nombre: Fiebre\n"
        "    lr: 3.0\n    fuente: y\n---\n\nP\n",
    )
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)

    r = _resultado_con_competencia()
    r.infones = [_infon("Fiebre", None, codigo="T:5")]
    r.acoplamiento = MedidorDeAcoplamiento().medir(protocolo, r.infones)
    assert r.acoplamiento is not None

    leido = tics.tic_completo(tics.guardar(r))
    assert leido["acoplamiento"]["coseno"] == r.acoplamiento.coseno
    # y la traza entera, que es lo que hace a Φ impugnable línea a línea
    assert leido["acoplamiento"]["traza"]
    assert leido["acoplamiento"]["componentes"][0]["dimension"] == "Fiebre"


# --- La cifra que el paso 2 buscaba ------------------------------------


def test_el_acuerdo_del_triaje_se_agrega_sobre_el_historico(entorno):
    """De una línea de log por tic a una medida del histórico."""
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)

    for coincide in (True, True, False):
        r = _resultado_con_competencia()
        r.triaje_coincide = coincide
        tics.guardar(r)

    medida = tics.acuerdo_del_triaje("p1")
    assert medida["coinciden"] == 2
    assert medida["discrepan"] == 1
    assert medida["comparables"] == 3
    assert medida["acuerdo"] == pytest.approx(2 / 3)


def test_un_tic_sin_competencia_no_cuenta_como_desacuerdo(entorno):
    """NULL, 0 y 1 son tres estados, y sólo dos son un juicio sobre el prompt.

    `triaje_coincide` es NULL cuando el grafo no propuso candidatas. Meter
    esos tics en el denominador diría que el prompt falló donde nadie le
    llevó la contraria: una tasa de error inventada.
    """
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)

    acertado = _resultado_con_competencia()
    tics.guardar(acertado)
    # Un tic normal, sin competencia que registrar.
    tics.guardar(ResultadoTic(paciente_id="p1", texto_original="…", skill_activa="x"))

    medida = tics.acuerdo_del_triaje("p1")
    assert medida["tics"] == 2
    assert medida["sin_competencia"] == 1
    assert medida["comparables"] == 1
    assert medida["acuerdo"] == 1.0, "el tic sin competencia no puede bajar la tasa"


def test_sin_nada_comparable_la_tasa_es_None_y_no_cero(entorno):
    """Un cero diría «el prompt nunca acierta», que es otra afirmación."""
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    tics.guardar(ResultadoTic(paciente_id="p1", texto_original="…", skill_activa="x"))

    medida = tics.acuerdo_del_triaje("p1")
    assert medida["acuerdo"] is None
    assert medida["sin_competencia"] == 1


def test_una_base_anterior_admite_la_competencia_sin_perder_sus_tics(tmp_path):
    """Las columnas nuevas llegan por migración a una base ya escrita."""
    import sqlite3

    ruta = tmp_path / "antigua.db"
    cx = sqlite3.connect(ruta)
    cx.executescript(
        """
        CREATE TABLE paciente (id TEXT PRIMARY KEY, nombre TEXT NOT NULL,
            edad INTEGER, sexo TEXT, telefono TEXT,
            antecedentes TEXT NOT NULL DEFAULT '', creado TEXT NOT NULL);
        CREATE TABLE tic (id INTEGER PRIMARY KEY, paciente_id TEXT NOT NULL,
            timestamp TEXT NOT NULL, skill TEXT NOT NULL,
            texto_original TEXT NOT NULL, resumen TEXT NOT NULL DEFAULT '',
            inferencia TEXT);
        INSERT INTO paciente VALUES ('p1','Antiguo',NULL,NULL,NULL,'','2026-01-01');
        INSERT INTO tic VALUES (1,'p1','2026-01-01','vieja','texto','resumen',NULL);
        """
    )
    cx.commit()
    cx.close()

    db = Database(ruta)
    columnas = {f[1] for f in db.conexion().execute("PRAGMA table_info(tic)")}
    assert {
        "skill_version",
        "acoplamiento",
        "veredicto",
        "competencia",
        "ganadora_abductiva",
        "triaje_coincide",
        "aviso_competencia",
    } <= columnas

    tics = TicRepo(db, GraphRepo(db))
    tics.guardar(_resultado_con_competencia())

    # El tic viejo sigue ahí, y no cuenta como desacuerdo del triaje.
    medida = tics.acuerdo_del_triaje("p1")
    assert medida["tics"] == 2
    assert medida["sin_competencia"] == 1
    assert medida["coinciden"] == 1
