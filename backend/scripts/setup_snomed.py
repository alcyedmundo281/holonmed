"""Preparación de los datos de SNOMED CT.

SNOMED CT es propiedad de SNOMED International y su uso requiere una
licencia de afiliado, gratuita en los países miembros. Este script NO
descarga la terminología: verifica los archivos que tú has obtenido
legítimamente y construye el cache que consume el motor.

Cómo obtener los datos:
  1. Comprueba si tu país es miembro: https://www.snomed.org/member-countries
  2. Solicita una licencia de afiliado a través del centro nacional
     (en España, el Ministerio de Sanidad; en Latinoamérica varía).
  3. Descarga la *Spanish Edition* — el Snapshot basta, el Full ocupa el
     doble y aquí no se usa el histórico.
  4. Descomprime los .txt en el directorio indicado por HOLONMED_SNOMED_DIR
     (por defecto ./data/snomed).

Uso:
    python scripts/setup_snomed.py --verificar
    python scripts/setup_snomed.py --construir-cache
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holonmed.config import get_settings  # noqa: E402
from holonmed.core.snomed import LocalSnomedIndex  # noqa: E402

REQUERIDOS = [
    (
        "descripciones",
        "sct2_Description_*Snapshot*.txt",
        "Vocabulario: término -> concept id. Imprescindible.",
    ),
    (
        "mapa CIE-10",
        "der2_*Map*Snapshot*.txt",
        "Mapa a CIE-10. Sin él los hallazgos no son facturables.",
    ),
    (
        "relaciones",
        "sct2_Relationship_*Snapshot*.txt",
        "Jerarquía IS_A. Sin ella no hay linaje clínico.",
    ),
]


def verificar() -> int:
    settings = get_settings()
    directorio = Path(settings.snomed_dir)

    print(f"\nDirectorio SNOMED: {directorio.resolve()}\n" + "=" * 60)

    if not directorio.exists():
        print("  El directorio no existe. Créalo y descomprime ahí el Snapshot.")
        print(f"    mkdir -p {directorio}")
        return 1

    encontrados = list(directorio.glob("*.txt"))
    if not encontrados:
        print("  No hay archivos .txt. Lee la cabecera de este script.")
        return 1

    faltan = 0
    for etiqueta, patron, para_que in REQUERIDOS:
        coincidencias = list(directorio.glob(patron))
        if coincidencias:
            archivo = coincidencias[0]
            mb = archivo.stat().st_size / (1024 * 1024)
            print(f"  [ok] {etiqueta:16} {archivo.name}  ({mb:,.1f} MB)")
        else:
            faltan += 1
            print(f"  [--] {etiqueta:16} no encontrado ({patron})")
            print(f"       {para_que}")

    cache = settings.snomed_cache_path
    if cache.exists():
        mb = cache.stat().st_size / (1024 * 1024)
        print(f"\n  Cache existente: {cache.name} ({mb:,.1f} MB)")
    else:
        print("\n  Sin cache. Ejecuta --construir-cache para acelerar el arranque.")

    print()
    return 0 if faltan == 0 else 1


def construir_cache() -> int:
    settings = get_settings()
    cache = settings.snomed_cache_path
    if cache.exists():
        cache.unlink()
        print(f"Cache anterior eliminado: {cache.name}")

    print("Ingiriendo el Snapshot. Tarda varios minutos y consume RAM…")
    index = LocalSnomedIndex(settings)
    ok, detalle = index.cargar()
    print(detalle)

    if not ok:
        return 1

    print(f"  términos:      {len(index.term_map):,}")
    print(f"  conceptos:     {len(index.id_to_term):,}")
    print(f"  mapeos CIE-10: {len(index.cie10_map):,}")
    print(f"  relaciones:    {len(index.parents):,}")
    if cache.exists():
        print(f"  cache escrito: {cache.stat().st_size / (1024 * 1024):,.1f} MB")

    # Prueba de humo: si esto no encuentra nada, el índice está mal.
    pruebas = ["fiebre", "dolor abdominal", "hipocalcemia"]
    print("\nPrueba de recuperación:")
    for termino in pruebas:
        candidatos = index.buscar_candidatos(termino, limite=1)
        if candidatos:
            _, encontrado, score = candidatos[0]
            print(f"  '{termino}' -> '{encontrado}' ({score:.0f}%)")
        else:
            print(f"  '{termino}' -> sin resultados (revisa el archivo de descripciones)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verificar", action="store_true", help="Comprueba qué archivos hay"
    )
    parser.add_argument(
        "--construir-cache",
        action="store_true",
        help="Ingiere el Snapshot y escribe el cache binario",
    )
    args = parser.parse_args()

    if args.construir_cache:
        return construir_cache()
    return verificar()


if __name__ == "__main__":
    raise SystemExit(main())
