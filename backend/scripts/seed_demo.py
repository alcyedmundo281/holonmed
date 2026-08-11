"""Datos de demostración.

Los pacientes creados aquí son **ficticios**. Nunca uses este script con
datos de personas reales: el repositorio es público y cualquier dato que
acabe en un volcado o en una captura de pantalla es una brecha.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holonmed.config import get_settings  # noqa: E402
from holonmed.db import Database, PacienteRepo  # noqa: E402

PACIENTES_FICTICIOS = [
    {
        "id": "demo",
        "nombre": "Paciente Demo",
        "edad": 45,
        "sexo": "masculino",
        "antecedentes": "Consumo de alcohol de riesgo. Litiasis biliar conocida.",
    },
    {
        "id": "demo2",
        "nombre": "Paciente Demo 2",
        "edad": 67,
        "sexo": "femenino",
        "antecedentes": "Diabetes mellitus tipo 2. Hipertensión arterial.",
    },
]


def main() -> int:
    db = Database(get_settings().db_path)
    if not db.disponible:
        print(f"Base de datos no disponible: {db.error}")
        return 1

    repo = PacienteRepo(db)
    for paciente in PACIENTES_FICTICIOS:
        if repo.obtener(paciente["id"]):
            print(f"  ya existe: {paciente['nombre']}")
            continue
        repo.crear(paciente)
        print(f"  creado:    {paciente['nombre']} ({paciente['id']})")

    print("\nDatos ficticios listos. Prueba:")
    print('  holonmed tic "Dolor epigástrico en cinturón, amilasa 1200, calcio 6.8" --paciente demo')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
