"""Persistencia y grafo clínico sobre SQLite.

Sustituye a la implementación anterior sobre ArangoDB. El motivo inmediato
fue de licencia — ArangoDB pasó a BUSL-1.1 en la 3.12 y su Community
Edition prohíbe el uso comercial — pero el resultado técnico es mejor para
este caso: cero instalación, un único archivo que el profesional puede
cifrar y respaldar, y consultas de grafo con cierre transitivo.

La conexión es por hilo (`threading.local`) porque FastAPI ejecuta las
rutas síncronas en un pool de hilos y un objeto `sqlite3.Connection` no se
puede compartir entre ellos.
"""

import json
import logging
import sqlite3
import threading
import unicodedata
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models import EstadoInfon, HolonPaciente, Infon

logger = logging.getLogger(__name__)

ESQUEMA = Path(__file__).with_name("schema.sql")


def normalizar(texto: str) -> str:
    """Minúsculas sin acentos, para comparaciones de igualdad.

    "Hipocalcemia", "hipocalcemia" e "HIPOCALCEMÍA" deben ser la misma
    clave. La búsqueda difusa se encarga del resto de variaciones.
    """
    descompuesto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Conexión a SQLite y creación idempotente del esquema."""

    def __init__(self, ruta: Path | str):
        self.ruta = Path(ruta)
        self._local = threading.local()
        self._escritura = threading.Lock()
        self.error: str | None = None
        self._inicializar()

    def _inicializar(self) -> None:
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            with self.conexion() as cx:
                # La migración va ANTES del esquema: éste crea índices sobre
                # columnas nuevas, y sobre una tabla antigua que aún no las
                # tiene el script entero falla.
                self._migrar(cx)
                cx.executescript(ESQUEMA.read_text(encoding="utf-8"))
            logger.info("Base de datos lista: %s", self.ruta)
        except (OSError, sqlite3.Error) as exc:
            self.error = str(exc)
            logger.error("No se pudo inicializar la base de datos: %s", exc)

    # Columnas añadidas después de la primera versión del esquema. Como
    # `CREATE TABLE IF NOT EXISTS` no toca una tabla que ya existe, hay que
    # añadirlas explícitamente o una base creada antes se queda coja.
    MIGRACIONES: tuple[tuple[str, str, str], ...] = (
        ("tic", "origen", "TEXT NOT NULL DEFAULT 'consulta'"),
        ("tic", "actor", "TEXT"),
    )

    def _migrar(self, cx: sqlite3.Connection) -> None:
        """Añade columnas nuevas a bases creadas con un esquema anterior.

        Se prefiere esto a versionar el esquema con números: son pocas
        columnas, la comprobación es barata y no hay forma de que una base
        quede a medio migrar.
        """
        for tabla, columna, definicion in self.MIGRACIONES:
            existentes = {
                fila[1] for fila in cx.execute(f"PRAGMA table_info({tabla})")
            }
            if not existentes:  # la tabla aún no existe
                continue
            if columna not in existentes:
                cx.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
                logger.info("Migración: %s.%s añadida", tabla, columna)

    def conexion(self) -> sqlite3.Connection:
        cx = getattr(self._local, "cx", None)
        if cx is None:
            cx = sqlite3.connect(self.ruta, timeout=15.0)
            cx.row_factory = sqlite3.Row
            cx.execute("PRAGMA foreign_keys = ON")
            cx.execute("PRAGMA journal_mode = WAL")
            self._local.cx = cx
        return cx

    @property
    def disponible(self) -> bool:
        return self.error is None

    def cerrar(self) -> None:
        cx = getattr(self._local, "cx", None)
        if cx is not None:
            cx.close()
            self._local.cx = None

    def estadisticas(self) -> dict[str, int]:
        cx = self.conexion()

        def contar(tabla: str) -> int:
            try:
                return cx.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            except sqlite3.Error:
                return 0

        return {
            "conceptos": contar("concepto"),
            "terminos": contar("termino"),
            "aristas": contar("es_un"),
            "ancestros_materializados": contar("ancestro"),
            "pacientes": contar("paciente"),
            "tics": contar("tic"),
            "infones": contar("infon"),
        }


class GraphRepo:
    """Consultas sobre el grafo ontológico.

    Dos estrategias conviven a propósito:

    * `ancestros()` usa un CTE recursivo. Siempre correcto, no necesita
      mantenimiento, y sobre `es_un` indexado es rápido para un concepto
      suelto (la profundidad típica en SNOMED es de una docena de saltos).

    * `materializar_ancestros()` precalcula el cierre para los conceptos
      que aparecen en datos clínicos. Materializar SNOMED entero serían
      decenas de millones de filas; materializar sólo lo usado son unos
      miles, y convierte las consultas de cohorte en un join indexado.
    """

    def __init__(self, db: Database):
        self._db = db

    def ancestros(self, concepto_id: int, max_profundidad: int = 20) -> list[sqlite3.Row]:
        """Todos los ancestros de un concepto, del más cercano al más lejano."""
        aql = """
            WITH RECURSIVE sube(id, profundidad) AS (
                SELECT padre_id, 1 FROM es_un WHERE hijo_id = ?
                UNION
                SELECT e.padre_id, s.profundidad + 1
                FROM es_un e JOIN sube s ON e.hijo_id = s.id
                WHERE s.profundidad < ?
            )
            SELECT c.id, c.codigo, c.sistema, c.termino, MIN(s.profundidad) AS profundidad
            FROM sube s JOIN concepto c ON c.id = s.id
            GROUP BY c.id
            ORDER BY profundidad
        """
        return self._db.conexion().execute(aql, (concepto_id, max_profundidad)).fetchall()

    def padre_inmediato(self, concepto_id: int) -> str | None:
        fila = (
            self._db.conexion()
            .execute(
                """SELECT c.termino FROM es_un e
                   JOIN concepto c ON c.id = e.padre_id
                   WHERE e.hijo_id = ? LIMIT 1""",
                (concepto_id,),
            )
            .fetchone()
        )
        return fila["termino"] if fila else None

    def materializar_ancestros(self, concepto_id: int) -> int:
        """Precalcula el cierre de un concepto. Idempotente."""
        cx = self._db.conexion()
        ya = cx.execute(
            "SELECT 1 FROM ancestro WHERE descendiente_id = ? LIMIT 1", (concepto_id,)
        ).fetchone()
        if ya:
            return 0

        filas = self.ancestros(concepto_id)
        if not filas:
            return 0

        with self._db._escritura:
            cx.executemany(
                "INSERT OR IGNORE INTO ancestro VALUES (?, ?, ?)",
                [(concepto_id, f["id"], f["profundidad"]) for f in filas],
            )
            cx.commit()
        return len(filas)

    def descendientes_de(self, codigo: str, sistema: str) -> list[int]:
        """IDs de conceptos que caen bajo una rama, usando el cierre.

        Es la consulta que hace útil el grafo: permite preguntar por
        "cualquier hallazgo pancreático" sin enumerar cada concepto.
        """
        aql = """
            SELECT DISTINCT a.descendiente_id AS id
            FROM ancestro a
            JOIN concepto c ON c.id = a.ancestro_id
            WHERE c.codigo = ? AND c.sistema = ?
            UNION
            SELECT id FROM concepto WHERE codigo = ? AND sistema = ?
        """
        filas = self._db.conexion().execute(aql, (codigo, sistema, codigo, sistema))
        return [f["id"] for f in filas]

    def cohorte(self, codigo: str, sistema: str) -> list[sqlite3.Row]:
        """Pacientes con algún hallazgo validado bajo una rama del grafo."""
        aql = """
            SELECT p.id, p.nombre, COUNT(DISTINCT i.id) AS hallazgos,
                   MAX(i.timestamp) AS ultimo
            FROM infon i
            JOIN paciente p ON p.id = i.paciente_id
            WHERE i.estado = 'VALIDADO'
              AND i.concepto_id IN (
                  SELECT a.descendiente_id FROM ancestro a
                  JOIN concepto c ON c.id = a.ancestro_id
                  WHERE c.codigo = ? AND c.sistema = ?
                  UNION SELECT id FROM concepto WHERE codigo = ? AND sistema = ?
              )
            GROUP BY p.id
            ORDER BY hallazgos DESC
        """
        return (
            self._db.conexion()
            .execute(aql, (codigo, sistema, codigo, sistema))
            .fetchall()
        )

    def vecindad(self, paciente_id: str, limite: int = 60) -> dict[str, list[dict]]:
        """Subgrafo de los conceptos de un paciente y sus ancestros comunes.

        Es lo que alimenta la vista de grafo del frontend: no el grafo
        entero de SNOMED, sino la parte que este paciente ocupa, con los
        nodos de agrupación que explican por qué sus hallazgos se parecen.
        """
        cx = self._db.conexion()
        hojas = cx.execute(
            """SELECT DISTINCT c.id, c.codigo, c.sistema, c.termino,
                      COUNT(i.id) AS apariciones
               FROM infon i JOIN concepto c ON c.id = i.concepto_id
               WHERE i.paciente_id = ? AND i.estado = 'VALIDADO'
               GROUP BY c.id ORDER BY apariciones DESC LIMIT ?""",
            (paciente_id, limite),
        ).fetchall()

        if not hojas:
            return {"nodos": [], "aristas": []}

        ids_hoja = {f["id"] for f in hojas}
        nodos: dict[int, dict] = {
            f["id"]: {
                "id": f["id"],
                "codigo": f["codigo"],
                "sistema": f["sistema"],
                "termino": f["termino"],
                "tipo": "hallazgo",
                "peso": f["apariciones"],
            }
            for f in hojas
        }
        aristas: list[dict] = []

        # Se suben tres niveles: suficiente para que aparezcan las
        # agrupaciones con sentido clínico sin llegar a la raíz, que
        # conectaría todo con todo y no explicaría nada.
        for hoja in ids_hoja:
            previo = hoja
            for ancestro in self.ancestros(hoja, max_profundidad=3):
                aid = ancestro["id"]
                if aid not in nodos:
                    nodos[aid] = {
                        "id": aid,
                        "codigo": ancestro["codigo"],
                        "sistema": ancestro["sistema"],
                        "termino": ancestro["termino"],
                        "tipo": "agrupacion",
                        "peso": 0,
                    }
                arista = {"origen": previo, "destino": aid}
                if arista not in aristas:
                    aristas.append(arista)
                previo = aid

        return {"nodos": list(nodos.values()), "aristas": aristas}


class PacienteRepo:
    def __init__(self, db: Database):
        self._db = db

    def obtener(self, paciente_id: str) -> HolonPaciente | None:
        fila = (
            self._db.conexion()
            .execute("SELECT * FROM paciente WHERE id = ?", (paciente_id,))
            .fetchone()
        )
        if not fila:
            return None
        return HolonPaciente(
            paciente_id=fila["id"],
            nombre=fila["nombre"],
            edad=fila["edad"],
            sexo=fila["sexo"],
            telefono=fila["telefono"],
            antecedentes=fila["antecedentes"],
        )

    def obtener_o_efimero(self, paciente_id: str) -> HolonPaciente:
        """Nunca falla: permite usar el validador sin dar de alta a nadie."""
        return self.obtener(paciente_id) or HolonPaciente(paciente_id=paciente_id)

    def crear(self, datos: dict[str, Any]) -> dict[str, Any] | None:
        pid = datos.get("id") or _nuevo_id(datos.get("nombre", "paciente"))
        registro = {
            "id": pid,
            "nombre": datos.get("nombre", "Paciente"),
            "edad": datos.get("edad"),
            "sexo": datos.get("sexo"),
            "telefono": datos.get("telefono"),
            "antecedentes": datos.get("antecedentes", "") or "",
            "creado": _ahora(),
        }
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.execute(
                    """INSERT INTO paciente (id, nombre, edad, sexo, telefono, antecedentes, creado)
                       VALUES (:id, :nombre, :edad, :sexo, :telefono, :antecedentes, :creado)""",
                    registro,
                )
                cx.commit()
        except sqlite3.IntegrityError:
            logger.warning("El paciente '%s' ya existe", pid)
            return None
        return registro

    def listar(self, limite: int = 200) -> list[dict[str, Any]]:
        filas = self._db.conexion().execute(
            """SELECT p.*,
                      (SELECT COUNT(*) FROM tic t WHERE t.paciente_id = p.id) AS tics,
                      (SELECT MAX(t.timestamp) FROM tic t WHERE t.paciente_id = p.id) AS ultima_visita
               FROM paciente p ORDER BY p.nombre LIMIT ?""",
            (limite,),
        )
        return [dict(f) for f in filas]

    def buscar(self, consulta: str) -> dict[str, Any] | None:
        fila = (
            self._db.conexion()
            .execute(
                "SELECT * FROM paciente WHERE lower(nombre) LIKE ? LIMIT 1",
                (f"%{consulta.strip().lower()}%",),
            )
            .fetchone()
        )
        return dict(fila) if fila else None

    CAMPOS_EDITABLES = frozenset({"nombre", "edad", "sexo", "telefono", "antecedentes"})

    def actualizar(self, paciente_id: str, campo: str, valor: Any) -> bool:
        # Lista blanca: `campo` puede venir de la salida de un LLM.
        if campo not in self.CAMPOS_EDITABLES:
            logger.warning("Campo no editable: %s", campo)
            return False
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.execute(
                    f"UPDATE paciente SET {campo} = ? WHERE id = ?",  # noqa: S608
                    (valor, paciente_id),
                )
                cx.commit()
            return True
        except sqlite3.Error as exc:
            logger.error("Error actualizando paciente: %s", exc)
            return False


class TicRepo:
    def __init__(self, db: Database, grafo: GraphRepo):
        self._db = db
        self._grafo = grafo

    def guardar(self, resultado) -> str | None:
        cx = self._db.conexion()
        try:
            with self._db._escritura:
                # El paciente puede ser efímero (nunca dado de alta); se crea
                # al vuelo para no perder el tic por una clave foránea.
                cx.execute(
                    """INSERT OR IGNORE INTO paciente (id, nombre, antecedentes, creado)
                       VALUES (?, ?, '', ?)""",
                    (resultado.paciente_id, resultado.paciente_id, _ahora()),
                )
                cursor = cx.execute(
                    """INSERT INTO tic (paciente_id, timestamp, origen, actor,
                                        skill, texto_original, resumen, inferencia)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        resultado.paciente_id,
                        resultado.timestamp,
                        resultado.origen.value,
                        resultado.actor,
                        resultado.skill_activa,
                        resultado.texto_original,
                        resultado.resumen,
                        json.dumps(resultado.inferencia.model_dump(mode="json"))
                        if resultado.inferencia
                        else None,
                    ),
                )
                tic_id = cursor.lastrowid

                for infon in resultado.infones:
                    cx.execute(
                        """INSERT INTO infon (
                               tic_id, paciente_id, concepto_id, timestamp, texto_origen,
                               termino_propuesto, termino, codigo, sistema, cie10, linaje,
                               estado, confianza, score_ontologico, score_logico,
                               razon_auditoria, origen_skill)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            tic_id,
                            resultado.paciente_id,
                            infon.concepto_id,
                            infon.timestamp,
                            infon.texto_origen,
                            infon.termino_propuesto,
                            infon.termino,
                            infon.codigo,
                            infon.sistema,
                            infon.cie10_code,
                            infon.linaje_clinico,
                            infon.estado.value,
                            infon.confianza,
                            infon.score_ontologico,
                            infon.score_logico,
                            infon.razon_auditoria,
                            infon.origen_skill,
                        ),
                    )
                cx.commit()
        except sqlite3.Error as exc:
            logger.error("Error guardando el tic: %s", exc)
            return None

        # El cierre transitivo se materializa fuera de la transacción: es
        # una optimización de consulta, no parte del dato clínico, y su
        # fallo no debe invalidar un tic ya guardado.
        for infon in resultado.infones_validados:
            cid = infon.concepto_id
            if cid:
                try:
                    self._grafo.materializar_ancestros(cid)
                except sqlite3.Error as exc:
                    logger.debug("No se materializó el cierre de %s: %s", cid, exc)

        return str(tic_id)

    def historial(
        self,
        paciente_id: str,
        limite: int = 50,
        origen: str | None = None,
    ) -> list[dict[str, Any]]:
        """Línea de tiempo de tics, opcionalmente filtrada por origen.

        Filtrar por origen es lo que permite responder «enséñame sólo lo
        que vino del laboratorio» sin recorrer toda la historia.
        """
        sql = """SELECT t.id, t.timestamp AS fecha, t.origen, t.actor, t.skill,
                        t.resumen, t.inferencia,
                        COUNT(i.id) AS total_infones,
                        SUM(CASE WHEN i.estado = 'VALIDADO' THEN 1 ELSE 0 END) AS validados,
                        (SELECT COUNT(*) FROM documento d WHERE d.tic_id = t.id) AS documentos
                 FROM tic t LEFT JOIN infon i ON i.tic_id = t.id
                 WHERE t.paciente_id = ?"""
        binds: list[Any] = [paciente_id]
        if origen:
            sql += " AND t.origen = ?"
            binds.append(origen)
        sql += " GROUP BY t.id ORDER BY t.timestamp DESC LIMIT ?"
        binds.append(limite)

        filas = self._db.conexion().execute(sql, binds)
        salida = []
        for f in filas:
            registro = dict(f)
            registro["id"] = str(registro["id"])
            registro["inferencia"] = (
                json.loads(registro["inferencia"]) if registro["inferencia"] else None
            )
            salida.append(registro)
        return salida

    def tic_completo(self, tic_id: str) -> dict[str, Any] | None:
        cx = self._db.conexion()
        cabecera = cx.execute("SELECT * FROM tic WHERE id = ?", (tic_id,)).fetchone()
        if not cabecera:
            return None
        infones = cx.execute(
            "SELECT * FROM infon WHERE tic_id = ? ORDER BY id", (tic_id,)
        ).fetchall()
        registro = dict(cabecera)
        registro["id"] = str(registro["id"])
        registro["inferencia"] = (
            json.loads(registro["inferencia"]) if registro["inferencia"] else None
        )
        registro["infones"] = [dict(i) for i in infones]
        return registro

    def por_origen(self, paciente_id: str) -> list[dict[str, Any]]:
        """Cuántos tics ha aportado cada actor del entorno clínico."""
        filas = self._db.conexion().execute(
            """SELECT origen, COUNT(*) AS tics, MAX(timestamp) AS ultimo
               FROM tic WHERE paciente_id = ?
               GROUP BY origen ORDER BY tics DESC""",
            (paciente_id,),
        )
        return [dict(f) for f in filas]

    def linea_tiempo(self, paciente_id: str, limite: int = 200) -> list[Infon]:
        filas = self._db.conexion().execute(
            """SELECT * FROM infon
               WHERE paciente_id = ? AND estado = 'VALIDADO'
               ORDER BY timestamp DESC LIMIT ?""",
            (paciente_id, limite),
        )
        return [_fila_a_infon(f) for f in filas]

    def lista_problemas(self, paciente_id: str) -> list[dict[str, Any]]:
        """Lista de problemas: conceptos validados, agrupados y fechados.

        Es la vista que un clínico mira primero. Se deduplica por concepto
        y se conserva la primera y la última vez que apareció, que es la
        información que dice si algo es agudo o arrastrado.
        """
        filas = self._db.conexion().execute(
            """SELECT termino, codigo, sistema, cie10, linaje,
                      COUNT(*) AS apariciones,
                      MIN(timestamp) AS primera,
                      MAX(timestamp) AS ultima,
                      MAX(confianza) AS confianza
               FROM infon
               WHERE paciente_id = ? AND estado = 'VALIDADO'
               GROUP BY COALESCE(codigo, termino)
               ORDER BY ultima DESC""",
            (paciente_id,),
        )
        return [dict(f) for f in filas]


class DocumentoRepo:
    """Documentos emitidos, colgados del tic que los originó.

    Antes una receta sólo producía un PDF: el fármaco prescrito no dejaba
    rastro en la historia y desaparecía al cerrar la ventana. Un fármaco
    prescrito es parte del registro clínico.
    """

    def __init__(self, db: Database):
        self._db = db

    def registrar(
        self,
        paciente_id: str,
        tipo: str,
        archivo: str | None = None,
        datos: Any = None,
        tic_id: str | None = None,
    ) -> str | None:
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cursor = cx.execute(
                    """INSERT INTO documento (tic_id, paciente_id, tipo, archivo, datos, creado)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        int(tic_id) if tic_id else None,
                        paciente_id,
                        tipo,
                        archivo,
                        json.dumps(datos, ensure_ascii=False) if datos is not None else None,
                        _ahora(),
                    ),
                )
                cx.commit()
                return str(cursor.lastrowid)
        except sqlite3.Error as exc:
            logger.error("Error registrando el documento: %s", exc)
            return None

    def listar(self, paciente_id: str, tipo: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM documento WHERE paciente_id = ?"
        binds: list[Any] = [paciente_id]
        if tipo:
            sql += " AND tipo = ?"
            binds.append(tipo)
        sql += " ORDER BY creado DESC"
        try:
            filas = self._db.conexion().execute(sql, binds).fetchall()
        except sqlite3.Error:
            return []

        salida = []
        for f in filas:
            registro = dict(f)
            registro["id"] = str(registro["id"])
            if registro.get("datos"):
                try:
                    registro["datos"] = json.loads(registro["datos"])
                except json.JSONDecodeError:
                    registro["datos"] = None
            salida.append(registro)
        return salida


class CitaRepo:
    def __init__(self, db: Database):
        self._db = db

    def crear(self, datos: dict[str, Any]) -> str | None:
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.execute(
                    "INSERT OR IGNORE INTO paciente (id, nombre, creado) VALUES (?, ?, ?)",
                    (datos["paciente_id"], datos["paciente_id"], _ahora()),
                )
                cursor = cx.execute(
                    """INSERT INTO cita (paciente_id, fecha, interpretada, motivo, estado, creada)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        datos["paciente_id"],
                        datos["fecha"],
                        int(datos.get("fecha_interpretada", False)),
                        datos.get("motivo", ""),
                        datos.get("estado", "agendada"),
                        _ahora(),
                    ),
                )
                cx.commit()
                return str(cursor.lastrowid)
        except sqlite3.Error as exc:
            logger.error("Error creando la cita: %s", exc)
            return None

    def listar(self, paciente_id: str | None = None) -> list[dict[str, Any]]:
        cx = self._db.conexion()
        if paciente_id:
            filas = cx.execute(
                """SELECT c.*, p.nombre AS paciente FROM cita c
                   JOIN paciente p ON p.id = c.paciente_id
                   WHERE c.paciente_id = ? ORDER BY c.fecha""",
                (paciente_id,),
            )
        else:
            filas = cx.execute(
                """SELECT c.*, p.nombre AS paciente FROM cita c
                   JOIN paciente p ON p.id = c.paciente_id ORDER BY c.fecha"""
            )
        return [dict(f) for f in filas]


def _fila_a_infon(fila: sqlite3.Row) -> Infon:
    return Infon(
        timestamp=fila["timestamp"],
        texto_origen=fila["texto_origen"],
        termino_propuesto=fila["termino_propuesto"],
        termino=fila["termino"],
        codigo=fila["codigo"],
        sistema=fila["sistema"],
        cie10_code=fila["cie10"],
        linaje_clinico=fila["linaje"],
        estado=EstadoInfon(fila["estado"]),
        confianza=fila["confianza"],
        score_ontologico=fila["score_ontologico"],
        score_logico=fila["score_logico"],
        razon_auditoria=fila["razon_auditoria"],
        origen_skill=fila["origen_skill"],
    )


def _nuevo_id(nombre: str) -> str:
    import re
    import secrets

    base = re.sub(r"[^a-z0-9]+", "-", normalizar(nombre)).strip("-")[:24] or "paciente"
    return f"{base}-{secrets.token_hex(3)}"


def filas_a_dicts(filas: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(f) for f in filas]
