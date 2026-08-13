"""Carga de tarifarios e inyección de sistemas de codificación externos.

Un tarifario es **un vocabulario más**. Se carga con su propio `sistema`,
igual que SNOMED o CIE-10, y el enlace entre el concepto clínico y su
código facturable usa la tabla `mapeo` que ya existía. No hace falta un
mecanismo nuevo: cada hospital o aseguradora carga el suyo y el resto del
sistema no se entera.

Sobre licencias, el mismo principio que con la terminología: **el código
que lee los catálogos es libre; los catálogos los aporta quien tenga
derecho a usarlos.**

  Tarifarios nacionales   Derivados de Harvard/RBRVS en varios países.
                          Condiciones según el organismo que los publica.
  CPT                     Propiedad de la AMA. Requiere licencia de pago.
  Tarifarios privados     De cada aseguradora, bajo su propio acuerdo.

Este repositorio incluye un catálogo de demostración con precios
inventados, para que el circuito funcione sin depender de ninguno.
"""

import csv
import json
import logging
from datetime import date
from pathlib import Path

from ..db.store import Database
from .repositorio import TarifarioRepo

logger = logging.getLogger(__name__)


class Tarifario:
    """Importa catálogos de precios y sus equivalencias clínicas."""

    def __init__(self, db: Database):
        self._db = db
        self.repo = TarifarioRepo(db)

    def cargar_json(self, ruta: Path, vigente_desde: str | None = None) -> dict:
        """Importa un catálogo en el formato del proyecto.

        Estructura esperada:

            {
              "sistema": "demo",
              "vigente_desde": "2026-01-01",
              "moneda": "USD",
              "prestaciones": [
                {"codigo": "T-001", "descripcion": "…", "importe": 42.0,
                 "equivale_a": ["HM:2001"]}
              ]
            }

        `equivale_a` son códigos del vocabulario clínico. Es lo que permite
        que una orden de «preparación de citostáticos» encuentre su precio
        sin que nadie escriba esa correspondencia en el código.
        """
        if not ruta.exists():
            logger.warning("No se encontró el tarifario en %s", ruta)
            return {"prestaciones": 0, "equivalencias": 0}

        datos = json.loads(ruta.read_text(encoding="utf-8"))
        sistema = str(datos.get("sistema", "demo"))
        desde = vigente_desde or str(datos.get("vigente_desde", date.today()))
        prestaciones = datos.get("prestaciones") or []

        n = self.repo.cargar(sistema, prestaciones, desde)
        equivalencias = self._mapear(sistema, prestaciones)

        logger.info(
            "Tarifario '%s': %d prestaciones, %d equivalencias", sistema, n, equivalencias
        )
        return {"sistema": sistema, "prestaciones": n, "equivalencias": equivalencias}

    def cargar_csv(
        self,
        ruta: Path,
        sistema: str,
        vigente_desde: str,
        columnas: dict[str, str] | None = None,
    ) -> dict:
        """Importa un catálogo en CSV, que es como suelen distribuirse.

        `columnas` traduce los nombres reales del archivo a los que espera
        el sistema, porque cada tarifario los llama distinto.
        """
        mapa = columnas or {
            "codigo": "codigo",
            "descripcion": "descripcion",
            "importe": "importe",
        }
        if not ruta.exists():
            logger.warning("No se encontró el CSV en %s", ruta)
            return {"prestaciones": 0}

        entradas = []
        with ruta.open(encoding="utf-8", newline="") as fh:
            for fila in csv.DictReader(fh):
                codigo = fila.get(mapa["codigo"])
                if not codigo:
                    continue
                try:
                    importe = float(
                        str(fila.get(mapa["importe"], 0)).replace(",", ".")
                    )
                except ValueError:
                    continue
                entradas.append(
                    {
                        "codigo": codigo,
                        "descripcion": fila.get(mapa["descripcion"], ""),
                        "importe": importe,
                    }
                )

        n = self.repo.cargar(sistema, entradas, vigente_desde)
        return {"sistema": sistema, "prestaciones": n}

    def _mapear(self, sistema: str, prestaciones: list[dict]) -> int:
        """Enlaza cada prestación con sus conceptos clínicos.

        Se apoya en `mapeo`, la misma tabla que resuelve CIE-10. Un
        tarifario es otro sistema de destino.
        """
        pares: list[tuple[str, str, str]] = []
        for p in prestaciones:
            for clinico in p.get("equivale_a") or []:
                pares.append((str(clinico), sistema, str(p["codigo"])))
        if not pares:
            return 0

        try:
            with self._db._escritura:
                cx = self._db.conexion()
                cx.executemany(
                    """INSERT OR IGNORE INTO mapeo (concepto_id, sistema_destino, codigo_destino)
                       SELECT id, ?2, ?3 FROM concepto WHERE codigo = ?1""",
                    pares,
                )
                cx.commit()
                return cx.execute(
                    "SELECT COUNT(*) FROM mapeo WHERE sistema_destino = ?", (sistema,)
                ).fetchone()[0]
        except Exception as exc:  # noqa: BLE001
            logger.error("Error creando las equivalencias: %s", exc)
            return 0
