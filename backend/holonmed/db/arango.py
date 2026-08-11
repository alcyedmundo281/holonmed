"""Persistencia sobre ArangoDB.

Se eligió Arango por dos motivos que el dominio impone: la historia
clínica es un grafo (conceptos relacionados, no filas), y ArangoSearch da
BM25 con analizador español sobre el vocabulario SNOMED sin montar un
Elasticsearch aparte.

El sistema arranca aunque la base no esté disponible: los repositorios
devuelven vacío y la API lo reporta en `/health`. Un fallo de persistencia
no debe impedir que un clínico use el validador.
"""

import logging
import socket
from typing import Any

from ..config import Settings, get_settings
from ..models import HolonPaciente, Infon, ResultadoTic

logger = logging.getLogger(__name__)

COLECCIONES = ("Pacientes", "Tics", "Infones", "Citas", "Documentos")


class Database:
    """Conexión perezosa y creación idempotente del esquema."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.db = None
        self.error: str | None = None

    def _puerto_abierto(self) -> bool:
        """Sondeo TCP rápido antes de invocar al driver.

        Sin esto, `python-arango` reintenta con backoff exponencial y el
        arranque tarda casi un minuto en una máquina sin ArangoDB. Como el
        sistema está diseñado para funcionar sin persistencia, esa espera
        sería un impuesto absurdo sobre el caso que sí queremos soportar.
        """
        from urllib.parse import urlparse

        url = urlparse(self.settings.arango_url)
        host, puerto = url.hostname or "localhost", url.port or 8529

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            return sock.connect_ex((host, puerto)) == 0

    def conectar(self) -> bool:
        try:
            from arango import ArangoClient
        except ImportError:
            self.error = "python-arango no está instalado"
            logger.warning(self.error)
            return False

        if not self._puerto_abierto():
            self.error = f"No hay nada escuchando en {self.settings.arango_url}"
            logger.warning("ArangoDB no disponible: %s", self.error)
            return False

        try:
            client = ArangoClient(
                hosts=self.settings.arango_url,
                request_timeout=10,
            )
            sys_db = client.db(
                "_system",
                username=self.settings.arango_user,
                password=self.settings.arango_password,
            )
            if not sys_db.has_database(self.settings.arango_db):
                sys_db.create_database(self.settings.arango_db)

            self.db = client.db(
                self.settings.arango_db,
                username=self.settings.arango_user,
                password=self.settings.arango_password,
            )
            for nombre in COLECCIONES:
                if not self.db.has_collection(nombre):
                    self.db.create_collection(nombre)

            self.error = None
            logger.info("ArangoDB conectado: %s", self.settings.arango_db)
            return True
        except Exception as exc:  # noqa: BLE001 — la app sigue sin base
            self.error = str(exc)
            self.db = None
            logger.warning("ArangoDB no disponible: %s", exc)
            return False

    @property
    def disponible(self) -> bool:
        return self.db is not None


class PacienteRepo:
    def __init__(self, database: Database):
        self._db = database

    def obtener(self, paciente_id: str) -> HolonPaciente | None:
        if not self._db.disponible:
            return None
        try:
            doc = self._db.db.collection("Pacientes").get(paciente_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error leyendo paciente %s: %s", paciente_id, exc)
            return None
        if not doc:
            return None
        return HolonPaciente(
            paciente_id=doc["_key"],
            nombre=doc.get("nombre", "Paciente"),
            edad=doc.get("edad"),
            sexo=doc.get("sexo"),
            telefono=doc.get("telefono"),
            antecedentes=doc.get("antecedentes", ""),
        )

    def obtener_o_efimero(self, paciente_id: str) -> HolonPaciente:
        """Nunca falla: sin base, se trabaja con un holón en memoria.

        Permite usar el validador en una máquina sin ArangoDB levantado.
        """
        return self.obtener(paciente_id) or HolonPaciente(paciente_id=paciente_id)

    def crear(self, datos: dict[str, Any]) -> dict[str, Any] | None:
        if not self._db.disponible:
            return None
        try:
            doc = self._db.db.collection("Pacientes").insert(datos, return_new=True)
            return doc["new"]
        except Exception as exc:  # noqa: BLE001
            logger.error("Error creando paciente: %s", exc)
            return None

    def listar(self, limite: int = 100) -> list[dict[str, Any]]:
        if not self._db.disponible:
            return []
        aql = "FOR p IN Pacientes SORT p.nombre LIMIT @limite RETURN p"
        try:
            return list(self._db.db.aql.execute(aql, bind_vars={"limite": limite}))
        except Exception:  # noqa: BLE001
            return []

    def buscar(self, consulta: str) -> dict[str, Any] | None:
        if not self._db.disponible:
            return None
        aql = """
            FOR p IN Pacientes
              FILTER CONTAINS(LOWER(p.nombre), LOWER(@q))
              LIMIT 1
              RETURN p
        """
        try:
            res = list(self._db.db.aql.execute(aql, bind_vars={"q": consulta.strip()}))
            return res[0] if res else None
        except Exception:  # noqa: BLE001
            return None

    def actualizar(self, paciente_id: str, campo: str, valor: Any) -> bool:
        if not self._db.disponible:
            return False
        # Lista blanca: el campo puede venir de la salida de un LLM.
        permitidos = {"nombre", "edad", "sexo", "telefono", "antecedentes"}
        if campo not in permitidos:
            logger.warning("Intento de actualizar campo no permitido: %s", campo)
            return False
        try:
            self._db.db.collection("Pacientes").update(
                {"_key": paciente_id, campo: valor}
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Error actualizando paciente: %s", exc)
            return False


class TicRepo:
    """Guarda cada ciclo de procesamiento con su trazabilidad completa."""

    def __init__(self, database: Database):
        self._db = database

    def guardar(self, resultado: ResultadoTic) -> str | None:
        if not self._db.disponible:
            return None
        try:
            doc = self._db.db.collection("Tics").insert(
                {
                    "paciente_id": resultado.paciente_id,
                    "timestamp": resultado.timestamp,
                    "skill": resultado.skill_activa,
                    "texto_original": resultado.texto_original,
                    "resumen": resultado.resumen,
                    "infones": [i.model_dump(mode="json") for i in resultado.infones],
                    "inferencia": (
                        resultado.inferencia.model_dump(mode="json")
                        if resultado.inferencia
                        else None
                    ),
                }
            )
            # Los infones validados se indexan aparte: son la línea de
            # tiempo consultable del holón.
            coleccion = self._db.db.collection("Infones")
            for infon in resultado.infones_validados:
                payload = infon.model_dump(mode="json")
                payload["paciente_id"] = resultado.paciente_id
                payload["tic_id"] = doc["_key"]
                coleccion.insert(payload)
            return doc["_key"]
        except Exception as exc:  # noqa: BLE001
            logger.error("Error guardando tic: %s", exc)
            return None

    def historial(self, paciente_id: str, limite: int = 50) -> list[dict[str, Any]]:
        if not self._db.disponible:
            return []
        aql = """
            FOR t IN Tics
              FILTER t.paciente_id == @pid
              SORT t.timestamp DESC
              LIMIT @limite
              RETURN {
                id: t._key, fecha: t.timestamp, skill: t.skill,
                resumen: t.resumen,
                total_infones: LENGTH(t.infones),
                validados: LENGTH(FOR i IN t.infones FILTER i.estado == 'VALIDADO' RETURN 1),
                inferencia: t.inferencia
              }
        """
        try:
            return list(
                self._db.db.aql.execute(
                    aql, bind_vars={"pid": paciente_id, "limite": limite}
                )
            )
        except Exception:  # noqa: BLE001
            return []

    def linea_tiempo(self, paciente_id: str, limite: int = 200) -> list[Infon]:
        """Todos los infones validados del paciente, del más nuevo al más viejo."""
        if not self._db.disponible:
            return []
        aql = """
            FOR i IN Infones
              FILTER i.paciente_id == @pid
              SORT i.timestamp DESC
              LIMIT @limite
              RETURN i
        """
        try:
            filas = list(
                self._db.db.aql.execute(
                    aql, bind_vars={"pid": paciente_id, "limite": limite}
                )
            )
        except Exception:  # noqa: BLE001
            return []

        infones = []
        for fila in filas:
            fila.pop("_key", None)
            fila.pop("_id", None)
            fila.pop("_rev", None)
            fila.pop("paciente_id", None)
            fila.pop("tic_id", None)
            try:
                infones.append(Infon(**fila))
            except Exception:  # noqa: BLE001 — un documento viejo no rompe la vista
                continue
        return infones


class CitaRepo:
    def __init__(self, database: Database):
        self._db = database

    def crear(self, datos: dict[str, Any]) -> str | None:
        if not self._db.disponible:
            return None
        try:
            return self._db.db.collection("Citas").insert(datos)["_key"]
        except Exception as exc:  # noqa: BLE001
            logger.error("Error creando cita: %s", exc)
            return None

    def listar(self, paciente_id: str | None = None) -> list[dict[str, Any]]:
        if not self._db.disponible:
            return []
        if paciente_id:
            aql = "FOR c IN Citas FILTER c.paciente_id == @pid SORT c.fecha RETURN c"
            binds = {"pid": paciente_id}
        else:
            aql = "FOR c IN Citas SORT c.fecha RETURN c"
            binds = {}
        try:
            return list(self._db.db.aql.execute(aql, bind_vars=binds))
        except Exception:  # noqa: BLE001
            return []
