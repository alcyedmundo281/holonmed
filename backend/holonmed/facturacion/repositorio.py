"""Persistencia de órdenes, ejecuciones, tarifas y cargos."""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ..db.store import Database
from .modelos import Cargo, Ejecucion, EstadoCargo, EstadoOrden, Orden

logger = logging.getLogger(__name__)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(valor: Any) -> str | None:
    return json.dumps(valor, ensure_ascii=False) if valor else None


def _desde_json(valor: Any) -> dict:
    if not valor:
        return {}
    try:
        cargado = json.loads(valor)
        return cargado if isinstance(cargado, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


class OrdenRepo:
    def __init__(self, db: Database):
        self._db = db

    def crear(self, orden: Orden) -> str | None:
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.execute(
                    "INSERT OR IGNORE INTO paciente (id, nombre, creado) VALUES (?,?,?)",
                    (orden.paciente_id, orden.paciente_id, _ahora()),
                )
                cursor = cx.execute(
                    """INSERT INTO orden (paciente_id, tic_id, timestamp, termino,
                                          codigo, sistema, concepto_id, texto_origen,
                                          prescriptor, detalle, estado, referencias)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        orden.paciente_id,
                        int(orden.tic_id) if orden.tic_id else None,
                        orden.timestamp,
                        orden.termino,
                        orden.codigo,
                        orden.sistema,
                        orden.concepto_id,
                        orden.texto_origen,
                        orden.prescriptor,
                        _json(orden.detalle),
                        orden.estado.value,
                        _json(orden.referencias),
                    ),
                )
                cx.commit()
                return str(cursor.lastrowid)
        except sqlite3.Error as exc:
            logger.error("Error creando la orden: %s", exc)
            return None

    def listar(self, paciente_id: str, estado: EstadoOrden | None = None) -> list[Orden]:
        sql = "SELECT * FROM orden WHERE paciente_id = ?"
        binds: list[Any] = [paciente_id]
        if estado:
            sql += " AND estado = ?"
            binds.append(estado.value)
        sql += " ORDER BY timestamp"
        try:
            filas = self._db.conexion().execute(sql, binds).fetchall()
        except sqlite3.Error:
            return []
        return [_a_orden(f) for f in filas]

    def marcar(self, orden_id: str, estado: EstadoOrden) -> bool:
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.execute(
                    "UPDATE orden SET estado = ? WHERE id = ?", (estado.value, orden_id)
                )
                cx.commit()
            return True
        except sqlite3.Error as exc:
            logger.error("Error actualizando la orden: %s", exc)
            return False


class EjecucionRepo:
    def __init__(self, db: Database):
        self._db = db

    def registrar(self, ejecucion: Ejecucion) -> str | None:
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.execute(
                    "INSERT OR IGNORE INTO paciente (id, nombre, creado) VALUES (?,?,?)",
                    (ejecucion.paciente_id, ejecucion.paciente_id, _ahora()),
                )
                cursor = cx.execute(
                    """INSERT INTO ejecucion (paciente_id, orden_id, tic_id, timestamp,
                                              termino, codigo, sistema, actor, origen,
                                              texto_origen, detalle, referencias,
                                              campos_faltantes)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        ejecucion.paciente_id,
                        int(ejecucion.orden_id) if ejecucion.orden_id else None,
                        int(ejecucion.tic_id) if ejecucion.tic_id else None,
                        ejecucion.timestamp,
                        ejecucion.termino,
                        ejecucion.codigo,
                        ejecucion.sistema,
                        ejecucion.actor,
                        ejecucion.origen,
                        ejecucion.texto_origen,
                        _json(ejecucion.detalle),
                        _json(ejecucion.referencias),
                        json.dumps(ejecucion.campos_faltantes, ensure_ascii=False)
                        if ejecucion.campos_faltantes
                        else None,
                    ),
                )
                cx.commit()
                return str(cursor.lastrowid)
        except sqlite3.Error as exc:
            logger.error("Error registrando la ejecución: %s", exc)
            return None

    def listar(self, paciente_id: str) -> list[Ejecucion]:
        try:
            filas = (
                self._db.conexion()
                .execute(
                    "SELECT * FROM ejecucion WHERE paciente_id = ? ORDER BY timestamp",
                    (paciente_id,),
                )
                .fetchall()
            )
        except sqlite3.Error:
            return []
        return [_a_ejecucion(f) for f in filas]

    def vincular(self, ejecucion_id: str, orden_id: str) -> bool:
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.execute(
                    "UPDATE ejecucion SET orden_id = ? WHERE id = ?",
                    (orden_id, ejecucion_id),
                )
                cx.commit()
            return True
        except sqlite3.Error:
            return False


class TarifarioRepo:
    """Catálogos de precios. Cada hospital o aseguradora carga el suyo."""

    def __init__(self, db: Database):
        self._db = db

    def cargar(self, sistema: str, entradas: list[dict], vigente_desde: str) -> int:
        """Importa un catálogo. No sobrescribe vigencias anteriores."""
        filas = [
            (
                sistema,
                str(e["codigo"]),
                str(e.get("descripcion", "")),
                e.get("unidad"),
                float(e.get("importe", 0)),
                str(e.get("moneda", "USD")),
                vigente_desde,
            )
            for e in entradas
            if e.get("codigo")
        ]
        if not filas:
            return 0
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.executemany(
                    """INSERT INTO tarifa
                       (sistema, codigo, descripcion, unidad, importe, moneda, vigente_desde)
                       VALUES (?,?,?,?,?,?,?)
                       ON CONFLICT(sistema, codigo, vigente_desde) DO UPDATE SET
                         descripcion = excluded.descripcion,
                         importe = excluded.importe""",
                    filas,
                )
                cx.commit()
            return len(filas)
        except sqlite3.Error as exc:
            logger.error("Error cargando el tarifario: %s", exc)
            return 0

    def buscar(self, sistema: str, codigo: str, fecha: str | None = None) -> dict | None:
        """La tarifa vigente en una fecha. Sin fecha, la más reciente.

        Una cuenta de hace un año tiene que poder reconstruirse con los
        precios de entonces, así que nunca se consulta «el precio actual»
        sino «el precio vigente en tal fecha».
        """
        corte = fecha or _ahora()
        try:
            fila = (
                self._db.conexion()
                .execute(
                    """SELECT * FROM tarifa
                       WHERE sistema = ? AND codigo = ? AND vigente_desde <= ?
                       ORDER BY vigente_desde DESC LIMIT 1""",
                    (sistema, codigo, corte),
                )
                .fetchone()
            )
        except sqlite3.Error:
            return None
        return dict(fila) if fila else None

    def sistemas(self) -> dict[str, int]:
        try:
            filas = self._db.conexion().execute(
                "SELECT sistema, COUNT(DISTINCT codigo) AS n FROM tarifa GROUP BY sistema"
            )
            return {f["sistema"]: f["n"] for f in filas}
        except sqlite3.Error:
            return {}

    def codigo_para(self, concepto_id: int, sistema_tarifario: str) -> str | None:
        """Traduce un concepto clínico a su código tarifario.

        Usa la misma tabla `mapeo` que resuelve CIE-10: un tarifario es
        otro sistema de destino, no un mecanismo aparte.
        """
        try:
            fila = (
                self._db.conexion()
                .execute(
                    """SELECT codigo_destino FROM mapeo
                       WHERE concepto_id = ? AND sistema_destino = ? LIMIT 1""",
                    (concepto_id, sistema_tarifario),
                )
                .fetchone()
            )
        except sqlite3.Error:
            return None
        return fila["codigo_destino"] if fila else None


class CargoRepo:
    def __init__(self, db: Database):
        self._db = db

    def crear(self, cargo: Cargo) -> str | None:
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cursor = cx.execute(
                    """INSERT OR IGNORE INTO cargo
                       (paciente_id, orden_id, ejecucion_id, creado, codigo_tarifario,
                        sistema_tarifario, descripcion, cantidad, importe_unitario, estado)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        cargo.paciente_id,
                        int(cargo.orden_id) if cargo.orden_id else None,
                        int(cargo.ejecucion_id) if cargo.ejecucion_id else None,
                        cargo.creado,
                        cargo.codigo_tarifario,
                        cargo.sistema_tarifario,
                        cargo.descripcion,
                        cargo.cantidad,
                        cargo.importe_unitario,
                        cargo.estado.value,
                    ),
                )
                cx.commit()
                return str(cursor.lastrowid) if cursor.lastrowid else None
        except sqlite3.Error as exc:
            logger.error("Error creando el cargo: %s", exc)
            return None

    def listar(self, paciente_id: str) -> list[Cargo]:
        try:
            filas = (
                self._db.conexion()
                .execute(
                    "SELECT * FROM cargo WHERE paciente_id = ? ORDER BY creado",
                    (paciente_id,),
                )
                .fetchall()
            )
        except sqlite3.Error:
            return []
        return [_a_cargo(f) for f in filas]

    def confirmar(self, cargo_id: str, quien: str | None = None) -> bool:
        """Un cargo sólo se factura cuando una persona lo autoriza."""
        del quien  # se registrará cuando haya autenticación
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.execute(
                    "UPDATE cargo SET estado = ? WHERE id = ? AND estado = ?",
                    (EstadoCargo.CONFIRMADO.value, cargo_id, EstadoCargo.PROPUESTO.value),
                )
                cx.commit()
            return True
        except sqlite3.Error:
            return False

    def anular(self, cargo_id: str) -> bool:
        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.execute(
                    "UPDATE cargo SET estado = ? WHERE id = ?",
                    (EstadoCargo.ANULADO.value, cargo_id),
                )
                cx.commit()
            return True
        except sqlite3.Error:
            return False


def _a_orden(f: sqlite3.Row) -> Orden:
    return Orden(
        id=str(f["id"]),
        paciente_id=f["paciente_id"],
        tic_id=str(f["tic_id"]) if f["tic_id"] else None,
        timestamp=f["timestamp"],
        termino=f["termino"],
        codigo=f["codigo"],
        sistema=f["sistema"],
        concepto_id=f["concepto_id"],
        texto_origen=f["texto_origen"] or "",
        prescriptor=f["prescriptor"],
        detalle=_desde_json(f["detalle"]),
        estado=EstadoOrden(f["estado"]),
        referencias=_desde_json(_col(f, "referencias")),
    )


def _a_ejecucion(f: sqlite3.Row) -> Ejecucion:
    return Ejecucion(
        id=str(f["id"]),
        paciente_id=f["paciente_id"],
        orden_id=str(f["orden_id"]) if f["orden_id"] else None,
        tic_id=str(f["tic_id"]) if f["tic_id"] else None,
        timestamp=f["timestamp"],
        termino=f["termino"],
        codigo=f["codigo"],
        sistema=f["sistema"],
        actor=f["actor"],
        origen=f["origen"],
        texto_origen=f["texto_origen"] or "",
        detalle=_desde_json(f["detalle"]),
        referencias=_desde_json(_col(f, "referencias")),
        campos_faltantes=_lista(_col(f, "campos_faltantes")),
    )


def _col(fila: sqlite3.Row, nombre: str):
    """Lee una columna que puede no existir en una base sin migrar."""
    return fila[nombre] if nombre in fila.keys() else None


def _lista(valor) -> list[str]:
    if not valor:
        return []
    try:
        cargado = json.loads(valor)
        return cargado if isinstance(cargado, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _a_cargo(f: sqlite3.Row) -> Cargo:
    return Cargo(
        id=str(f["id"]),
        paciente_id=f["paciente_id"],
        orden_id=str(f["orden_id"]) if f["orden_id"] else None,
        ejecucion_id=str(f["ejecucion_id"]) if f["ejecucion_id"] else None,
        creado=f["creado"],
        codigo_tarifario=f["codigo_tarifario"],
        sistema_tarifario=f["sistema_tarifario"],
        descripcion=f["descripcion"],
        cantidad=f["cantidad"],
        importe_unitario=f["importe_unitario"],
        estado=EstadoCargo(f["estado"]),
    )
