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


PROTOCOLO_DE_DOS_SIGNOS = """---
titulo: Apendicitis
signos:
  - nombre: Fiebre
    lr: 3.0
    fuente: y
  - nombre: Leucocitosis
    lr: 4.0
    fuente: y
---

Cuerpo.
"""


def test_la_reapertura_de_la_indagacion_sobrevive_al_viaje(entorno):
    """Un tic que terminó en duda no puede leerse mañana como concluido.

    La reapertura es la salida accionable del tic: de qué clase fue el
    fallo, hacia dónde indagar y qué prefiere la abducción. Sin
    persistirla, la duda sería una línea de log legible sólo por quien
    estuviera mirando la consola, que es exactamente el argumento con el
    que se persistieron el acoplamiento y la competencia.
    """
    from holonmed.core.acoplamiento import MedidorDeAcoplamiento
    from holonmed.core.duda import ReabridorDeIndagacion
    from holonmed.core.skills import Skill

    protocolo = Skill("apendicitis", PROTOCOLO_DE_DOS_SIGNOS)

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)

    r = _resultado_con_competencia()
    # Una dimensión declarada sin mirar y un hallazgo que nadie explica:
    # Φ cae y el tic tiene que decirlo.
    r.infones = [_infon("Coluria", None, codigo="T:9")]
    r.acoplamiento = MedidorDeAcoplamiento().medir(protocolo, r.infones)
    r.reapertura = ReabridorDeIndagacion().reabrir(r.acoplamiento, r.ganadora_abductiva)
    assert r.reapertura is not None

    leido = tics.tic_completo(tics.guardar(r))
    assert leido["reapertura"]["hipotesis"] == r.reapertura.hipotesis
    assert leido["reapertura"]["causa"] == r.reapertura.causa.value
    assert leido["reapertura"]["motivo"]
    assert leido["reapertura"]["traza"]


def test_un_tic_sin_duda_guarda_NULL_y_no_una_reapertura_vacia(entorno):
    """None y un objeto vacío dirían cosas distintas al leerlos mañana."""
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)

    r = _resultado_con_competencia()
    assert r.reapertura is None

    leido = tics.tic_completo(tics.guardar(r))
    assert leido["reapertura"] is None


PROTOCOLO_CATEGORICO = """---
titulo: Apendicitis por categorias
condicion:
  nombre: Apendicitis categorica
signos:
  - nombre: Fiebre
    fuente: y
  - nombre: Leucocitosis
    fuente: y
---

Cuerpo.
"""


def test_el_phi_previo_sale_del_tic_anterior_de_la_misma_hipotesis(entorno):
    """La consulta que convierte la duda en trayectoria.

    Sin ella dΦ/dt no existe: el pipeline no habla con la base de datos, y
    el Φ anterior tiene que llegarle en el holón igual que la línea de
    tiempo.
    """
    from holonmed.core.acoplamiento import MedidorDeAcoplamiento
    from holonmed.core.skills import Skill

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    med = MedidorDeAcoplamiento()
    protocolo = Skill("apendicitis", PROTOCOLO_DE_DOS_SIGNOS)

    # Primer tic: los dos signos constan, la hipótesis funciona.
    primero = _resultado_con_competencia()
    primero.infones = [
        _infon("Fiebre", None, codigo="T:5"),
        _infon("Leucocitosis", None, codigo="T:6"),
    ]
    primero.acoplamiento = med.medir(protocolo, primero.infones)
    tics.guardar(primero)

    previo = tics.phi_por_hipotesis(primero.paciente_id)
    assert previo[primero.acoplamiento.hipotesis] == pytest.approx(
        primero.acoplamiento.phi_legible, abs=1e-4
    )


def test_el_phi_previo_es_el_mas_reciente_y_no_el_primero(entorno):
    """Se recorre de nuevo a viejo y se conserva el primero de cada hipótesis.

    Un Φ de hace cinco tics no es la trayectoria: la pregunta es de dónde
    venía la creencia la última vez que se midió.
    """
    from holonmed.core.acoplamiento import MedidorDeAcoplamiento
    from holonmed.core.skills import Skill

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    med = MedidorDeAcoplamiento()
    protocolo = Skill("apendicitis", PROTOCOLO_DE_DOS_SIGNOS)

    for indice, infones in enumerate(
        (
            [
                _infon("Fiebre", None, codigo="T:5"),
                _infon("Leucocitosis", None, codigo="T:6"),
            ],
            [_infon("Coluria", None, codigo="T:9")],
        )
    ):
        r = _resultado_con_competencia()
        r.timestamp = f"2026-08-2{indice + 1}T10:00:00Z"
        r.infones = infones
        r.acoplamiento = med.medir(protocolo, infones)
        tics.guardar(r)

    hipotesis = r.acoplamiento.hipotesis
    previo = tics.phi_por_hipotesis(r.paciente_id)

    # El segundo tic —el desacoplado— es el que manda.
    assert previo[hipotesis] == pytest.approx(r.acoplamiento.phi_legible, abs=1e-4)
    assert previo[hipotesis] < 0.20


def test_el_phi_previo_de_un_protocolo_categorico_no_es_cero(entorno):
    """La trayectoria tiene que leer el mismo número que decide la duda.

    Para un protocolo que declara categorías y no cocientes, `phi` vale 0
    porque no hay vector ponderado que proyectar. Guardando ese 0 como Φ
    anterior, **toda hipótesis categórica volvería como «nunca arraigó»**
    aunque hubiera estado perfectamente acoplada — el mismo modo de fallo
    que `duda` tenía al leer `phi`, reaparecido un nivel más abajo. Y son
    la mayoría del índice.
    """
    from holonmed.core.acoplamiento import MedidorDeAcoplamiento
    from holonmed.core.skills import Skill

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    protocolo = Skill("categorico", PROTOCOLO_CATEGORICO)

    r = _resultado_con_competencia()
    r.infones = [
        _infon("Fiebre", None, codigo="T:5"),
        _infon("Leucocitosis", None, codigo="T:6"),
    ]
    r.acoplamiento = MedidorDeAcoplamiento().medir(protocolo, r.infones)
    assert r.acoplamiento.phi == 0.0  # no hay lectura ponderada
    assert r.acoplamiento.phi_categorico > 0.20  # y la categórica va bien
    tics.guardar(r)

    previo = tics.phi_por_hipotesis(r.paciente_id)
    assert previo[r.acoplamiento.hipotesis] == pytest.approx(
        r.acoplamiento.phi_categorico, abs=1e-4
    )
    assert previo[r.acoplamiento.hipotesis] > 0.20


def test_sin_tics_anteriores_no_hay_phi_previo(entorno):
    """Un diccionario vacío, que el reabridor lee como «no hay trayectoria»."""
    db, grafo, _ = entorno
    assert TicRepo(db, grafo).phi_por_hipotesis("nadie") == {}


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


def test_el_tipo_de_nota_sobrevive_al_viaje(entorno):
    """Un tic sabe qué clase de documento es, no sólo quién lo produjo.

    Los dos ejes estaban fundidos en `origen`, y así una nota clínica y un
    resultado de laboratorio se leían igual. Sin el tipo no se puede
    reconstruir la historia según Weed —base, nota clínica, evolución—,
    que es lo que da orden a todo lo demás.
    """
    from holonmed.models import TipoNota

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    clinica = _tic()
    clinica.tipo = TipoNota.CLINICA
    tics.guardar(clinica)
    tics.guardar(_tic())  # el defecto

    tipos = sorted(fila["tipo"] for fila in tics.historial("p1"))
    assert tipos == ["clinica", "evolucion"]


def test_el_paciente_es_un_actor_como_los_demas(entorno):
    """Los cinco actores anteriores eran todos del centro sanitario.

    Sin esta clave, un dato que trae el enfermo se registra como si lo
    hubiera producido la consulta, y deja de poder auditarse aparte —que
    es justo lo que `origen` existe para evitar.
    """
    from holonmed.models import OrigenTic

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    tics.guardar(_tic(origen=OrigenTic.PACIENTE, actor="el propio paciente"))

    solo_paciente = tics.historial("p1", origen="paciente")
    assert len(solo_paciente) == 1
    assert solo_paciente[0]["actor"] == "el propio paciente"


def test_una_base_anterior_admite_el_tipo_sin_perder_sus_tics(entorno, tmp_path):
    """La migración no puede costar la historia ya escrita.

    `CREATE TABLE IF NOT EXISTS` no toca una tabla que ya existe, así que
    una base anterior a esta columna se quedaría coja. Se comprueba contra
    una base real a la que se le quita la columna, no contra el esquema
    nuevo.
    """
    import sqlite3

    from holonmed.db import Database

    ruta = tmp_path / "vieja.db"
    vieja = Database(ruta)
    TicRepo(vieja, GraphRepo(vieja)).guardar(_tic(resumen="escrito antes"))
    vieja.cerrar()

    with sqlite3.connect(ruta) as cx:
        cx.execute("ALTER TABLE tic DROP COLUMN tipo")
        cx.commit()

    reabierta = Database(ruta)
    filas = TicRepo(reabierta, GraphRepo(reabierta)).historial("p1")
    assert len(filas) == 1
    assert filas[0]["resumen"] == "escrito antes"
    # El defecto no es un capricho: el grueso del tráfico son notas de
    # evolución, y es lo que eran todos los tics escritos hasta ahora.
    assert filas[0]["tipo"] == "evolucion"
    reabierta.cerrar()


def test_el_almacen_obedece_la_secuencia_del_episodio(entorno):
    """Las reglas puras ya se prueban aparte; aquí se prueba que gobiernen.

    Rechazar en el almacén y no en la ruta es deliberado: es el único punto
    por el que se puede pasar, y una regla que sólo vive en la capa de
    arriba se salta desde la CLI.
    """
    from holonmed.db import EpisodioRepo
    from holonmed.models import TipoNota

    db, grafo, _ = entorno
    tics, episodios = TicRepo(db, grafo), EpisodioRepo(db)
    episodio = episodios.abrir("p1", motivo="dolor abdominal")

    # Una evolución no puede preceder a la historia clínica.
    evolucion = _tic()
    evolucion.episodio_id, evolucion.tipo = episodio, TipoNota.EVOLUCION
    assert tics.guardar(evolucion) is None

    base = _tic()
    base.episodio_id, base.tipo = episodio, TipoNota.BASE
    assert tics.guardar(base) is not None

    # Y una segunda historia clínica tampoco.
    otra = _tic()
    otra.episodio_id, otra.tipo = episodio, TipoNota.BASE
    assert tics.guardar(otra) is None


def test_el_ordinal_de_la_nota_clinica_lo_asigna_el_almacen(entorno):
    """Si dos sitios lo calcularan, un día diferirían."""
    from holonmed.db import EpisodioRepo
    from holonmed.models import TipoNota

    db, grafo, _ = entorno
    tics, episodios = TicRepo(db, grafo), EpisodioRepo(db)
    episodio = episodios.abrir("p1")

    base = _tic()
    base.episodio_id, base.tipo = episodio, TipoNota.BASE
    tics.guardar(base)

    ordinales = []
    for _ in range(3):
        clinica = _tic()
        clinica.episodio_id, clinica.tipo = episodio, TipoNota.CLINICA
        tics.guardar(clinica)
        ordinales.append(clinica.ordinal_clinica)

    assert ordinales == [1, 2, 3]


def test_un_episodio_cerrado_no_admite_nada_mas(entorno):
    """Si se pudiera seguir escribiendo, la epicrisis sería un documento más."""
    from holonmed.db import EpisodioRepo
    from holonmed.models import TipoNota

    db, grafo, _ = entorno
    tics, episodios = TicRepo(db, grafo), EpisodioRepo(db)
    episodio = episodios.abrir("p1")

    for tipo in (TipoNota.BASE, TipoNota.CLINICA, TipoNota.EPICRISIS):
        documento = _tic()
        documento.episodio_id, documento.tipo = episodio, tipo
        assert tics.guardar(documento) is not None

    episodios.cerrar(episodio)

    tarde = _tic()
    tarde.episodio_id, tarde.tipo = episodio, TipoNota.EVOLUCION
    assert tics.guardar(tarde) is None


def test_un_episodio_inventado_no_admite_escritura(entorno):
    """«No existe» no es «existe y está vacío», y confundirlos dejaría
    escribir contra un identificador cualquiera."""
    from holonmed.models import TipoNota

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    fantasma = _tic()
    fantasma.episodio_id, fantasma.tipo = "9999", TipoNota.BASE
    assert tics.guardar(fantasma) is None


def test_un_tic_sin_episodio_sigue_escribiendose(entorno):
    """Es el caso anterior al ciclo 17, y la historia ya escrita es toda así.

    No se les inventa un episodio: agruparlos afirmaría que pertenecieron al
    mismo ingreso, y nadie lo sabe.
    """
    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    assert tics.guardar(_tic(resumen="sin episodio")) is not None
    assert tics.historial("p1")[0]["resumen"] == "sin episodio"


def test_un_infon_que_nadie_actualizo_no_es_real(entorno):
    """Por bien validado que esté por el sistema, sigue siendo potencia.

    `estado` es el veredicto del validador de tres capas; `acto` es la
    ratificación humana. Fundirlos haría que «validado» significara dos
    cosas distintas según quién leyera.
    """
    from holonmed.models import EstadoInfon

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    resultado = _tic()
    resultado.infones = [
        Infon(
            texto_origen="Fiebre de 38.5",
            termino_propuesto="fiebre",
            termino="Fiebre",
            estado=EstadoInfon.VALIDADO,
        )
    ]
    tic_id = tics.guardar(resultado)

    guardado = tics.tic_completo(tic_id)["infones"][0]
    assert guardado["estado"] == "VALIDADO"
    assert guardado["acto"] is None


def test_la_ratificacion_sobrevive_al_viaje(entorno):
    from holonmed.models import EstadoInfon

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    resultado = _tic()
    resultado.infones = [
        Infon(
            texto_origen="Dolor epigástrico",
            termino_propuesto="dolor",
            termino="Dolor epigástrico",
            estado=EstadoInfon.VALIDADO,
            acto="corregido",
            actualizado_por="Dra. Ruiz",
            actualizado_en="2026-09-05T10:00:00Z",
            correccion={"termino": ["Dolor abdominal", "Dolor epigástrico"]},
        )
    ]
    tic_id = tics.guardar(resultado)

    guardado = tics.tic_completo(tic_id)["infones"][0]
    assert guardado["acto"] == "corregido"
    assert guardado["actualizado_por"] == "Dra. Ruiz"


def test_sin_nadie_que_actue_la_tasa_de_correccion_es_none(entorno):
    """Cero diría que el sistema no se equivocó; nadie ha mirado todavía."""
    from holonmed.models import EstadoInfon

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    resultado = _tic()
    resultado.infones = [
        Infon(
            texto_origen="x",
            termino_propuesto="x",
            termino="X",
            estado=EstadoInfon.VALIDADO,
        )
    ]
    tics.guardar(resultado)

    medida = tics.tasa_de_correccion("p1")
    assert medida["tasa"] is None
    assert medida["sin_actuar"] == 1
    assert medida["actuados"] == 0


def test_la_tasa_dice_en_que_campo_falla_el_sistema(entorno):
    """Un contador de aciertos no dice en qué falla; el desglose sí."""
    from holonmed.models import EstadoInfon

    db, grafo, _ = entorno
    tics = TicRepo(db, grafo)
    resultado = _tic()
    resultado.infones = [
        Infon(
            texto_origen="a",
            termino_propuesto="a",
            termino="A",
            estado=EstadoInfon.VALIDADO,
            acto="aceptado",
            actualizado_por="Dra. Ruiz",
        ),
        Infon(
            texto_origen="b",
            termino_propuesto="b",
            termino="B",
            estado=EstadoInfon.VALIDADO,
            acto="corregido",
            actualizado_por="Dra. Ruiz",
            correccion={"termino": ["B", "B'"]},
        ),
    ]
    tics.guardar(resultado)

    medida = tics.tasa_de_correccion("p1")
    assert medida["actuados"] == 2
    assert medida["tasa"] == 0.5
    assert medida["por_campo"] == {"termino": 1}


def test_la_escalera_de_holones_se_deriva_del_episodio(entorno):
    """La composición no se almacena: es función de la secuencia.

    Una tabla de enlace sería una segunda fuente de verdad que un día
    diverge, y el compromiso del sistema es que el estado en el tic n sea
    recomputable desde 1..n.
    """
    from holonmed.db import EpisodioRepo
    from holonmed.models import TipoNota

    db, grafo, _ = entorno
    tics, episodios = TicRepo(db, grafo), EpisodioRepo(db)
    episodio = episodios.abrir("p1")

    for tipo in (
        TipoNota.BASE,
        TipoNota.EVOLUCION,
        TipoNota.CLINICA,
        TipoNota.EPICRISIS,
    ):
        documento = _tic()
        documento.episodio_id, documento.tipo = episodio, tipo
        tics.guardar(documento)

    escalera = episodios.holones(episodio)
    etiquetas = [h["etiqueta"] for h in escalera["holones"]]

    # La evolución no aparece: aporta infones, no síntesis.
    assert etiquetas == ["primario", "clínica-1", "final"]
    # Y el final los contiene a todos los anteriores.
    assert len(escalera["holones"][-1]["compone"]) == 2


def test_los_infones_de_las_evoluciones_los_recoge_el_holon_siguiente(entorno):
    """Es para lo que nace un holon secundario."""
    from holonmed.db import EpisodioRepo
    from holonmed.models import EstadoInfon, TipoNota

    db, grafo, _ = entorno
    tics, episodios = TicRepo(db, grafo), EpisodioRepo(db)
    episodio = episodios.abrir("p1")

    base = _tic()
    base.episodio_id, base.tipo = episodio, TipoNota.BASE
    tics.guardar(base)

    evolucion = _tic()
    evolucion.episodio_id, evolucion.tipo = episodio, TipoNota.EVOLUCION
    evolucion.infones = [
        Infon(
            texto_origen="Fiebre",
            termino_propuesto="fiebre",
            termino="Fiebre",
            estado=EstadoInfon.VALIDADO,
        )
    ]
    tics.guardar(evolucion)

    # Antes de la nota clínica, ese infón espera: no es una pérdida.
    en_espera = episodios.holones(episodio)
    assert en_espera["conservacion"]["coincide"]
    assert len(en_espera["conservacion"]["huerfanos"]) == 1

    clinica = _tic()
    clinica.episodio_id, clinica.tipo = episodio, TipoNota.CLINICA
    tics.guardar(clinica)

    tras_sintetizar = episodios.holones(episodio)
    assert tras_sintetizar["conservacion"]["huerfanos"] == []
    assert len(tras_sintetizar["holones"][-1]["infones_propios"]) == 1
