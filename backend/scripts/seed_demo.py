"""Datos de demostración.

Los pacientes creados aquí son **ficticios**. Nunca uses este script con
datos de personas reales: el repositorio es público y cualquier dato que
acabe en un volcado o en una captura de pantalla es una brecha.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holonmed.db import Database, PacienteRepo  # noqa: E402

PACIENTES_FICTICIOS = [
    {
        "_key": "demo",
        "nombre": "Paciente Demo",
        "edad": 45,
        "sexo": "masculino",
        "antecedentes": "Consumo de alcohol de riesgo. Litiasis biliar conocida.",
        "telefono": "",
    },
    {
        "_key": "demo2",
        "nombre": "Paciente Demo 2",
        "edad": 67,
        "sexo": "femenino",
        "antecedentes": "Diabetes mellitus tipo 2. Hipertensión arterial.",
        "telefono": "",
    },
]


def main() -> int:
    db = Database()
    if not db.conectar():
        print(f"ArangoDB no disponible: {db.error}")
        return 1

    repo = PacienteRepo(db)
    coleccion = db.db.collection("Pacientes")

    for paciente in PACIENTES_FICTICIOS:
        if coleccion.has(paciente["_key"]):
            print(f"  ya existe: {paciente['nombre']}")
            continue
        repo.crear(paciente)
        print(f"  creado:    {paciente['nombre']} ({paciente['_key']})")

    print("\nDatos ficticios listos. Prueba:")
    print('  holonmed tic "Dolor epigástrico en cinturón, amilasa 1200, calcio 6.8" --paciente demo')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
