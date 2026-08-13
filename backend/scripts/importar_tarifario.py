"""Importación de tarifarios.

Un tarifario es un vocabulario más: se carga con su propio `sistema` y el
enlace con los conceptos clínicos usa la misma tabla `mapeo` que resuelve
CIE-10. Cada hospital o aseguradora carga el suyo sin tocar código.

IMPORTANTE — licencias
======================
Este repositorio distribuye **el código que lee** los catálogos, y un
tarifario de demostración con importes inventados. Los catálogos reales
los aporta quien tenga derecho a usarlos:

  Tarifarios nacionales   Derivados de Harvard/RBRVS en varios países.
                          Condiciones según el organismo que los publica.
  CPT                     Propiedad de la AMA. Licencia de pago.
  Tarifarios privados     De cada aseguradora, bajo su propio acuerdo.

Uso:
    python scripts/importar_tarifario.py --demo
    python scripts/importar_tarifario.py --json /ruta/tarifario.json
    python scripts/importar_tarifario.py --csv tarifas.csv --sistema iess \\
        --vigente-desde 2026-01-01
    python scripts/importar_tarifario.py --estado
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holonmed.config import get_settings  # noqa: E402
from holonmed.db import Database  # noqa: E402
from holonmed.facturacion import Tarifario  # noqa: E402

DEMO = Path(__file__).resolve().parents[1] / "data" / "tarifario_demo.json"


def estado() -> int:
    db = Database(get_settings().db_path)
    repo = Tarifario(db).repo
    sistemas = repo.sistemas()

    print(f"\nBase de datos: {db.ruta}\n" + "=" * 58)
    if not sistemas:
        print("\nNo hay ningún tarifario cargado.")
        print("Empieza por:  python scripts/importar_tarifario.py --demo")
        return 1

    print("\nTarifarios cargados:")
    for sistema, n in sorted(sistemas.items()):
        print(f"  {sistema:16} {n:>6} prestaciones")

    cx = db.conexion()
    equivalencias = cx.execute(
        """SELECT sistema_destino, COUNT(*) FROM mapeo
           WHERE sistema_destino IN (SELECT DISTINCT sistema FROM tarifa)
           GROUP BY sistema_destino"""
    ).fetchall()
    print("\nEquivalencias con el vocabulario clínico:")
    for fila in equivalencias:
        print(f"  {fila[0]:16} {fila[1]:>6} conceptos enlazados")
    if not equivalencias:
        print("  ninguna — los cargos no encontrarán su precio")
    print()
    return 0


def importar_json(ruta: Path) -> int:
    db = Database(get_settings().db_path)
    resultado = Tarifario(db).cargar_json(ruta)
    if not resultado.get("prestaciones"):
        print(f"No se cargó nada desde {ruta}")
        return 1
    print(
        f"Tarifario '{resultado['sistema']}': "
        f"{resultado['prestaciones']} prestaciones, "
        f"{resultado['equivalencias']} equivalencias clínicas"
    )
    return 0


def importar_csv(ruta: Path, sistema: str, desde: str) -> int:
    db = Database(get_settings().db_path)
    resultado = Tarifario(db).cargar_csv(ruta, sistema, desde)
    n = resultado.get("prestaciones", 0)
    print(f"Tarifario '{sistema}': {n} prestaciones")
    if n:
        print(
            "\nAviso: un CSV no trae las equivalencias con el vocabulario "
            "clínico.\nSin ellas las órdenes no encontrarán su precio. "
            "Decláralas en un\nJSON con `equivale_a`, o mapea a mano en la "
            "tabla `mapeo`."
        )
    return 0 if n else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--estado", action="store_true", help="Qué hay cargado")
    parser.add_argument("--demo", action="store_true", help="Carga el de demostración")
    parser.add_argument("--json", type=Path, help="Catálogo en el formato del proyecto")
    parser.add_argument("--csv", type=Path, help="Catálogo en CSV")
    parser.add_argument("--sistema", default="externo", help="Nombre del tarifario")
    parser.add_argument("--vigente-desde", default="2026-01-01")
    args = parser.parse_args()

    if args.demo:
        return importar_json(DEMO)
    if args.json:
        return importar_json(args.json)
    if args.csv:
        return importar_csv(args.csv, args.sistema, args.vigente_desde)
    return estado()


if __name__ == "__main__":
    raise SystemExit(main())
