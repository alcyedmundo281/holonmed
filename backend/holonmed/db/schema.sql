-- Esquema de HolonMed sobre SQLite.
--
-- SQLite es de dominio público y va embebido: no hay servidor que instalar,
-- ni licencia que revisar, ni puerto que exponer. Para un sistema clínico
-- que corre en la máquina del profesional, eso no es una limitación sino
-- justo lo que se quiere.
--
-- El grafo se modela con tres piezas:
--   * `es_un`    — aristas directas de la jerarquía (padre/hijo)
--   * `ancestro` — cierre transitivo materializado, sólo de lo que se usa
--   * `mapeo`    — equivalencias entre sistemas de codificación
--
-- Ver docs/GRAFO.md para el porqué de esa separación.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- =====================================================================
-- TERMINOLOGÍA
-- =====================================================================

-- Un concepto es una idea clínica, independiente de cómo se escriba.
CREATE TABLE IF NOT EXISTS concepto (
    id          INTEGER PRIMARY KEY,
    sistema     TEXT NOT NULL,   -- 'holonmed' | 'snomed' | 'hpo' | 'icd10'
    codigo      TEXT NOT NULL,
    termino     TEXT NOT NULL,   -- término preferente para mostrar
    semantica   TEXT,            -- 'hallazgo' | 'trastorno' | 'procedimiento' | …
    UNIQUE (sistema, codigo)
);

-- Las formas de escribir un concepto: preferente, sinónimos, abreviaturas.
-- Separar `termino` de `concepto` es lo que permite que "fiebre",
-- "hipertermia" y "febrícula" apunten al mismo sitio.
CREATE TABLE IF NOT EXISTS termino (
    id          INTEGER PRIMARY KEY,
    concepto_id INTEGER NOT NULL REFERENCES concepto(id) ON DELETE CASCADE,
    texto       TEXT NOT NULL,
    normalizado TEXT NOT NULL,   -- minúsculas y sin acentos, para igualdad exacta
    preferente  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_termino_concepto ON termino(concepto_id);
CREATE INDEX IF NOT EXISTS idx_termino_normalizado ON termino(normalizado);

-- Búsqueda de texto completo con ranking BM25, nativa de SQLite.
-- Sustituye a ArangoSearch sin añadir ninguna dependencia.
CREATE VIRTUAL TABLE IF NOT EXISTS termino_fts USING fts5(
    texto,
    content = 'termino',
    content_rowid = 'id',
    tokenize = "unicode61 remove_diacritics 2"
);

CREATE TRIGGER IF NOT EXISTS termino_ai AFTER INSERT ON termino BEGIN
    INSERT INTO termino_fts(rowid, texto) VALUES (new.id, new.texto);
END;

CREATE TRIGGER IF NOT EXISTS termino_ad AFTER DELETE ON termino BEGIN
    INSERT INTO termino_fts(termino_fts, rowid, texto) VALUES ('delete', old.id, old.texto);
END;

CREATE TRIGGER IF NOT EXISTS termino_au AFTER UPDATE ON termino BEGIN
    INSERT INTO termino_fts(termino_fts, rowid, texto) VALUES ('delete', old.id, old.texto);
    INSERT INTO termino_fts(rowid, texto) VALUES (new.id, new.texto);
END;

-- =====================================================================
-- GRAFO ONTOLÓGICO
-- =====================================================================

-- Aristas directas de la jerarquía. Es un DAG, no un árbol: un concepto
-- puede tener varios padres (una neumonía es infección Y enfermedad
-- pulmonar), y el modelo tiene que admitirlo.
CREATE TABLE IF NOT EXISTS es_un (
    hijo_id   INTEGER NOT NULL REFERENCES concepto(id) ON DELETE CASCADE,
    padre_id  INTEGER NOT NULL REFERENCES concepto(id) ON DELETE CASCADE,
    PRIMARY KEY (hijo_id, padre_id)
);

CREATE INDEX IF NOT EXISTS idx_es_un_padre ON es_un(padre_id);

-- Cierre transitivo materializado.
--
-- El cierre completo de SNOMED serían decenas de millones de filas, así
-- que sólo se materializa para los conceptos que realmente aparecen en
-- los datos clínicos. Se construye al insertar un infón y convierte las
-- consultas de cohorte ("pacientes con algo bajo enfermedad pancreática")
-- en un join indexado en vez de un recorrido recursivo por paciente.
CREATE TABLE IF NOT EXISTS ancestro (
    descendiente_id INTEGER NOT NULL REFERENCES concepto(id) ON DELETE CASCADE,
    ancestro_id     INTEGER NOT NULL REFERENCES concepto(id) ON DELETE CASCADE,
    profundidad     INTEGER NOT NULL,
    PRIMARY KEY (descendiente_id, ancestro_id)
);

CREATE INDEX IF NOT EXISTS idx_ancestro_ancestro ON ancestro(ancestro_id);

-- Equivalencias entre sistemas: SNOMED → CIE-10, HPO → SNOMED, etc.
CREATE TABLE IF NOT EXISTS mapeo (
    concepto_id     INTEGER NOT NULL REFERENCES concepto(id) ON DELETE CASCADE,
    sistema_destino TEXT NOT NULL,
    codigo_destino  TEXT NOT NULL,
    PRIMARY KEY (concepto_id, sistema_destino, codigo_destino)
);

CREATE INDEX IF NOT EXISTS idx_mapeo_destino ON mapeo(sistema_destino, codigo_destino);

-- =====================================================================
-- CLÍNICA
-- =====================================================================

CREATE TABLE IF NOT EXISTS paciente (
    id           TEXT PRIMARY KEY,
    nombre       TEXT NOT NULL,
    edad         INTEGER,
    sexo         TEXT,
    telefono     TEXT,
    antecedentes TEXT NOT NULL DEFAULT '',
    creado       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_paciente_nombre ON paciente(nombre);

-- Un tic es un ciclo completo de procesamiento.
--
-- `origen` distingue qué proceso lo produjo: la consulta, el laboratorio,
-- la farmacia. Los tres alimentan la misma historia pero no valen lo
-- mismo, y sin el campo un informe de laboratorio y una nota dictada son
-- indistinguibles a posteriori.
--
-- `actor` es quién lo asertó. Hoy es informativo porque no hay
-- autenticación; existe desde ahora para que añadirla después no obligue
-- a migrar registros clínicos ya escritos.
CREATE TABLE IF NOT EXISTS tic (
    id             INTEGER PRIMARY KEY,
    paciente_id    TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    timestamp      TEXT NOT NULL,
    origen         TEXT NOT NULL DEFAULT 'consulta',
    actor          TEXT,
    skill          TEXT NOT NULL,
    texto_original TEXT NOT NULL,
    resumen        TEXT NOT NULL DEFAULT '',
    inferencia     TEXT             -- JSON de la inferencia bayesiana
);

CREATE INDEX IF NOT EXISTS idx_tic_paciente ON tic(paciente_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tic_origen ON tic(paciente_id, origen, timestamp DESC);

-- Documentos emitidos: recetas, informes.
--
-- Van colgados de un tic para que aparezcan en la historia. Antes una
-- receta sólo generaba un PDF y no dejaba rastro: el fármaco prescrito
-- desaparecía del registro en cuanto se cerraba la ventana.
CREATE TABLE IF NOT EXISTS documento (
    id          INTEGER PRIMARY KEY,
    tic_id      INTEGER REFERENCES tic(id) ON DELETE CASCADE,
    paciente_id TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    tipo        TEXT NOT NULL,   -- receta | informe | …
    archivo     TEXT,            -- nombre del PDF en el directorio de documentos
    datos       TEXT,            -- JSON con el contenido estructurado
    creado      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documento_paciente ON documento(paciente_id, creado DESC);

-- Se guardan TODOS los infones, incluidos los descartados: es lo que
-- permite auditar después si el validador está rechazando de más.
CREATE TABLE IF NOT EXISTS infon (
    id                INTEGER PRIMARY KEY,
    tic_id            INTEGER NOT NULL REFERENCES tic(id) ON DELETE CASCADE,
    paciente_id       TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    concepto_id       INTEGER REFERENCES concepto(id) ON DELETE SET NULL,
    timestamp         TEXT NOT NULL,
    texto_origen      TEXT NOT NULL,
    termino_propuesto TEXT NOT NULL,
    termino           TEXT NOT NULL,
    polaridad         TEXT NOT NULL DEFAULT 'presente',
    derivado_de       TEXT,            -- JSON: términos que lo satisfacen
    criterio          TEXT,            -- criterio de clasificación que lo produjo
    codigo            TEXT,
    sistema           TEXT,
    cie10             TEXT,
    linaje            TEXT,
    estado            TEXT NOT NULL,   -- VALIDADO | ALERTA | RUIDO
    confianza         REAL NOT NULL DEFAULT 0,
    score_ontologico  REAL NOT NULL DEFAULT 0,
    score_logico      REAL NOT NULL DEFAULT 0,
    razon_auditoria   TEXT NOT NULL DEFAULT '',
    origen_skill      TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_infon_paciente ON infon(paciente_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_infon_estado ON infon(paciente_id, estado);
CREATE INDEX IF NOT EXISTS idx_infon_concepto ON infon(concepto_id);
CREATE INDEX IF NOT EXISTS idx_infon_tic ON infon(tic_id);

CREATE TABLE IF NOT EXISTS cita (
    id           INTEGER PRIMARY KEY,
    paciente_id  TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    fecha        TEXT NOT NULL,
    interpretada INTEGER NOT NULL DEFAULT 0,
    motivo       TEXT NOT NULL DEFAULT '',
    estado       TEXT NOT NULL DEFAULT 'agendada',
    creada       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cita_paciente ON cita(paciente_id, fecha);

-- =====================================================================
-- FACTURACIÓN
-- =====================================================================
--
-- La cadena es orden -> ejecución -> cargo, y no se puede saltar ningún
-- eslabón: `cargo` referencia siempre una orden. Sin orden no hay cargo,
-- no porque se lo pidamos amablemente a un modelo sino porque no existe
-- la fila. La propiedad antifraude es estructural.

-- Lo que el profesional autorizó. La fuente de verdad.
CREATE TABLE IF NOT EXISTS orden (
    id           INTEGER PRIMARY KEY,
    paciente_id  TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    tic_id       INTEGER REFERENCES tic(id) ON DELETE SET NULL,
    timestamp    TEXT NOT NULL,
    termino      TEXT NOT NULL,
    codigo       TEXT,
    sistema      TEXT,
    concepto_id  INTEGER REFERENCES concepto(id) ON DELETE SET NULL,
    texto_origen TEXT NOT NULL DEFAULT '',   -- cita de la nota
    prescriptor  TEXT,
    detalle      TEXT,                        -- JSON: dosis, vía, frecuencia
    estado       TEXT NOT NULL DEFAULT 'pendiente'
);

CREATE INDEX IF NOT EXISTS idx_orden_paciente ON orden(paciente_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_orden_estado ON orden(paciente_id, estado);

-- Lo que un actor hizo. `orden_id` nulo mientras no se concilie, o si
-- nunca hubo orden — que es un incidente, no un hueco.
CREATE TABLE IF NOT EXISTS ejecucion (
    id           INTEGER PRIMARY KEY,
    paciente_id  TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    orden_id     INTEGER REFERENCES orden(id) ON DELETE SET NULL,
    tic_id       INTEGER REFERENCES tic(id) ON DELETE SET NULL,
    timestamp    TEXT NOT NULL,
    termino      TEXT NOT NULL,
    codigo       TEXT,
    sistema      TEXT,
    actor        TEXT,
    origen       TEXT NOT NULL DEFAULT 'farmacia',
    texto_origen TEXT NOT NULL DEFAULT '',
    detalle      TEXT
);

CREATE INDEX IF NOT EXISTS idx_ejecucion_paciente ON ejecucion(paciente_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ejecucion_orden ON ejecucion(orden_id);

-- Tarifario. Un catálogo de precios es un vocabulario más, con su
-- `sistema`: cada hospital o aseguradora carga el suyo sin tocar código.
-- El enlace concepto clínico -> código tarifario usa la tabla `mapeo` que
-- ya existía para CIE-10; no hace falta un mecanismo nuevo.
--
-- Los precios cambian, así que la clave incluye la fecha de vigencia y
-- nunca se sobrescribe una tarifa antigua: una cuenta de hace un año debe
-- poder reconstruirse con los precios de entonces.
CREATE TABLE IF NOT EXISTS tarifa (
    sistema       TEXT NOT NULL,
    codigo        TEXT NOT NULL,
    descripcion   TEXT NOT NULL,
    unidad        TEXT,
    importe       REAL NOT NULL,
    moneda        TEXT NOT NULL DEFAULT 'USD',
    vigente_desde TEXT NOT NULL,
    PRIMARY KEY (sistema, codigo, vigente_desde)
);

CREATE INDEX IF NOT EXISTS idx_tarifa_sistema ON tarifa(sistema, codigo);

-- Un cargo nace propuesto: facturar exige que una persona lo confirme.
CREATE TABLE IF NOT EXISTS cargo (
    id                INTEGER PRIMARY KEY,
    paciente_id       TEXT NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    orden_id          INTEGER NOT NULL REFERENCES orden(id) ON DELETE CASCADE,
    ejecucion_id      INTEGER REFERENCES ejecucion(id) ON DELETE SET NULL,
    creado            TEXT NOT NULL,
    codigo_tarifario  TEXT NOT NULL,
    sistema_tarifario TEXT NOT NULL,
    descripcion       TEXT NOT NULL,
    cantidad          REAL NOT NULL DEFAULT 1,
    importe_unitario  REAL NOT NULL DEFAULT 0,
    estado            TEXT NOT NULL DEFAULT 'propuesto',
    UNIQUE (orden_id, ejecucion_id, codigo_tarifario)
);

CREATE INDEX IF NOT EXISTS idx_cargo_paciente ON cargo(paciente_id, estado);
