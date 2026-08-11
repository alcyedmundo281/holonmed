"""Importación de vocabularios clínicos.

HolonMed funciona recién clonado con su vocabulario semilla, que es
contenido propio del proyecto y no depende de ninguna licencia externa.
Este script sirve para añadir terminologías más completas cuando tengas
derecho a usarlas.

IMPORTANTE — licencias
======================
Este repositorio distribuye **el código que lee** estos formatos, nunca los
datos. Obtener la terminología y cumplir su licencia es responsabilidad de
quien la importa.

  SNOMED CT   Requiere licencia de afiliado, gratuita en los países
              miembros. Comprueba el tuyo en snomed.org/member-countries y
              solicítala a través del centro nacional correspondiente.

  CIE-10      Los mapas suelen venir dentro de la release de SNOMED. La
              clasificación es de la OMS y tiene sus propias condiciones.

  HPO         Licencia permisiva, redistribuible con atribución.
              Descarga: hpo.jax.org

Uso
===
    python scripts/importar_terminologia.py --semilla
    python scripts/importar_terminologia.py --rf2 /ruta/al/Snapshot/Terminology
    python scripts/importar_terminologia.py --estado
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holonmed.config import get_settings  # noqa: E402
from holonmed.core.terminology import TerminologyIndex, VocabularyLoader  # noqa: E402
from holonmed.db import Database, GraphRepo  # noqa: E402


def _db() -> Database:
    return Database(get_settings().db_path)


def estado() -> int:
    db = _db()
    index = TerminologyIndex(db, GraphRepo(db))
    stats = db.estadisticas()

    print(f"\nBase de datos: {db.ruta}")
    if db.ruta.exists():
        print(f"Tamaño: {db.ruta.stat().st_size / (1024 * 1024):,.1f} MB")
    print("=" * 58)

    sistemas = index.sistemas_cargados()
    if sistemas:
        print("\nVocabularios cargados:")
        for sistema, n in sorted(sistemas.items()):
            print(f"  {sistema:12} {n:>10,} conceptos")
    else:
        print("\nNo hay ningún vocabulario cargado.")
        print("Empieza por:  python scripts/importar_terminologia.py --semilla")

    print("\nGrafo:")
    print(f"  términos indexados        {stats['terminos']:>10,}")
    print(f"  aristas de jerarquía      {stats['aristas']:>10,}")
    print(f"  ancestros materializados  {stats['ancestros_materializados']:>10,}")

    print("\nDatos clínicos:")
    print(f"  pacientes  {stats['pacientes']:>10,}")
    print(f"  tics       {stats['tics']:>10,}")
    print(f"  infones    {stats['infones']:>10,}")
    print()
    return 0


def importar_semilla() -> int:
    settings = get_settings()
    db = _db()
    n = VocabularyLoader(db).cargar_semilla(settings.vocabulario_semilla)
    if not n:
        print(f"No se pudo leer {settings.vocabulario_semilla}")
        return 1
    print(f"Vocabulario semilla cargado: {n} conceptos")
    return _prueba_de_humo(db)


def importar_rf2(directorio: Path) -> int:
    """Importa una release RF2 (SNOMED CT y compatibles)."""
    if not directorio.is_dir():
        print(f"No es un directorio: {directorio}")
        return 1

    def buscar(patron: str) -> Path | None:
        # Se prefiere Snapshot sobre Full: el histórico no se usa aquí y
        # ocupa el doble.
        coincidencias = sorted(directorio.rglob(patron))
        for c in coincidencias:
            if "Snapshot" in c.name:
                return c
        return coincidencias[0] if coincidencias else None

    descripciones = buscar("sct2_Description_*.txt")
    relaciones = buscar("sct2_Relationship_*.txt")
    mapa = buscar("der2_*Map*.txt")

    if not descripciones:
        print(f"No se encontró ningún sct2_Description_*.txt bajo {directorio}")
        print("Descomprime ahí el Snapshot de tu release RF2.")
        return 1

    print(f"Descripciones: {descripciones.name}")
    print(f"Relaciones:    {relaciones.name if relaciones else 'no encontradas'}")
    print(f"Mapa CIE-10:   {mapa.name if mapa else 'no encontrado'}")
    print("\nImportando. Con la edición española esto tarda varios minutos.\n")

    db = _db()
    inicio = time.monotonic()
    totales = VocabularyLoader(db).cargar_rf2(descripciones, relaciones, mapa)
    duracion = time.monotonic() - inicio

    print(f"  conceptos   {totales['conceptos']:>10,}")
    print(f"  términos    {totales['terminos']:>10,}")
    print(f"  relaciones  {totales['relaciones']:>10,}")
    print(f"  mapeos      {totales['mapeos']:>10,}")
    print(f"\nCompletado en {duracion:,.0f} s")
    return _prueba_de_humo(db)


def _prueba_de_humo(db: Database) -> int:
    """Si esto no encuentra nada, el índice está mal construido."""
    index = TerminologyIndex(db, GraphRepo(db))
    print("\nPrueba de recuperación:")
    fallos = 0
    for termino in ["fiebre", "dolor abdominal", "amilasa elevada", "calcio bajo"]:
        candidatos = index.buscar_candidatos(termino, limite=1)
        if candidatos:
            c = candidatos[0]
            print(f"  '{termino}' -> {c.termino} [{c.sistema}:{c.codigo}] {c.score:.0f}%")
        else:
            fallos += 1
            print(f"  '{termino}' -> SIN RESULTADOS")
    print()
    return 1 if fallos else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--estado", action="store_true", help="Qué hay cargado")
    parser.add_argument("--semilla", action="store_true", help="Carga el vocabulario base")
    parser.add_argument("--rf2", type=Path, metavar="DIR", help="Importa una release RF2")
    args = parser.parse_args()

    if args.semilla:
        return importar_semilla()
    if args.rf2:
        return importar_rf2(args.rf2)
    return estado()


if __name__ == "__main__":
    raise SystemExit(main())
