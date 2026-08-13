"""Compara cómo cambia el comportamiento según se le presente el protocolo.

Motivación: al migrar los protocolos a frontmatter YAML se excluyó el
conocimiento estructurado del prompt, con el razonamiento de que «es para
el código». El resultado fue que el auditor perdió acceso a los puntos de
corte y empezó a inventarlos: para «lipasa 890» escribió «>3x el límite
normal (aprox. 250-300)» cuando el protocolo declara 60.

Este script mide tres formas de presentar lo mismo:

  minimo     sólo la prosa. El modelo no ve ningún corte.
  prosa      los cortes redactados como texto corrido.
  etiquetas  los cortes delimitados, para que sean localizables.

Métricas
--------
* **Validados** — cuántos hallazgos superan las cuatro capas.
* **Cortes citados** — de los hallazgos que derivan de un criterio de
  laboratorio, en cuántos el razonamiento menciona el número que el
  protocolo declara de verdad.
* **Cortes inventados** — en cuántos aparece un número que no es el del
  protocolo, presentado como si lo fuera.

La segunda y la tercera importan más que la primera. Un veredicto correcto
sostenido por un razonamiento inventado sigue siendo un problema: el
argumento de este sistema es la trazabilidad, y un clínico que detecte un
corte falso dejará de creerse el resto.

Uso:
    python scripts/comparar_formatos.py
    python scripts/comparar_formatos.py --repeticiones 3
"""

import argparse
import asyncio
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from holonmed.api.deps import AppContext  # noqa: E402
from holonmed.config import Settings  # noqa: E402
from holonmed.core.skills import Skill  # noqa: E402
from holonmed.models import EstadoInfon, HolonPaciente  # noqa: E402

NOTA = (
    "Varon de 45 anos, bebedor de riesgo, con litiasis biliar conocida. "
    "Acude por dolor epigastrico en cinturon de 12 horas de evolucion, con "
    "vomitos repetidos. No refiere fiebre. A la exploracion: FC 115, "
    "TA 100/60, abdomen doloroso a la palpacion profunda con defensa. "
    "Laboratorio: amilasa 1200, lipasa 890, calcio 6.8, leucocitos 18500, "
    "hematocrito 48."
)

PROTOCOLO = "acute_pancreatitis"

_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass
class Medida:
    formato: str
    total: int = 0
    validados: int = 0
    alertas: int = 0
    ruido: int = 0
    con_corte: int = 0        # el razonamiento cita el corte real
    corte_inventado: int = 0  # cita un número que no es el del protocolo
    sin_numero: int = 0       # no cita ninguna cifra
    ejemplos: list[str] = field(default_factory=list)

    @property
    def auditables(self) -> int:
        return self.con_corte + self.corte_inventado + self.sin_numero


def cortes_declarados(skill: Skill) -> dict[str, set[str]]:
    """Término clínico -> números que el protocolo declara para él."""
    mapa: dict[str, set[str]] = {}
    for c in skill.laboratorio:
        validos = {
            _fmt(v)
            for v in (c.corte_superior, c.corte_inferior)
            if v is not None
        }
        # Con multiplicador, el umbral efectivo también es legítimo.
        if c.multiplicador and c.corte_superior is not None:
            validos.add(_fmt(c.corte_superior * c.multiplicador))
        for termino in c.terminos():
            mapa.setdefault(termino.strip().lower(), set()).update(validos)
    return mapa


def _fmt(valor: float) -> str:
    """110.0 -> '110'. Los modelos escriben el entero, no el float."""
    return str(int(valor)) if float(valor).is_integer() else str(valor)


def clasificar(razon: str, esperados: set[str]) -> str:
    """¿El razonamiento cita el corte real, uno inventado, o ninguno?"""
    numeros = set(_NUMERO.findall(razon.replace(",", ".")))
    numeros = {_fmt(float(n)) for n in numeros if _es_numero(n)}
    if not numeros:
        return "sin_numero"
    if numeros & esperados:
        return "con_corte"
    return "inventado"


def _es_numero(t: str) -> bool:
    try:
        float(t)
        return True
    except ValueError:
        return False


async def medir(formato: str, repeticiones: int) -> Medida:
    medida = Medida(formato=formato)
    # Base efímera por formato: la comparación no debe contaminarse con los
    # tics de la ejecución anterior.
    ctx = AppContext(Settings(formato_protocolo=formato))
    skill = ctx.skills.cargar(PROTOCOLO)
    esperados_por_termino = cortes_declarados(skill)

    for _ in range(repeticiones):
        holon = HolonPaciente(paciente_id="comparativa")
        resultado = await ctx.pipeline.ejecutar(NOTA, holon, skill_forzada=PROTOCOLO)

        for infon in resultado.infones:
            medida.total += 1
            if infon.estado == EstadoInfon.VALIDADO:
                medida.validados += 1
            elif infon.estado == EstadoInfon.ALERTA:
                medida.alertas += 1
            else:
                medida.ruido += 1

            esperados = esperados_por_termino.get(infon.termino.strip().lower())
            if not esperados:
                continue  # hallazgo cualitativo: no hay corte que citar

            veredicto = clasificar(infon.razon_auditoria, esperados)
            if veredicto == "con_corte":
                medida.con_corte += 1
            elif veredicto == "inventado":
                medida.corte_inventado += 1
                if len(medida.ejemplos) < 3:
                    medida.ejemplos.append(
                        f"{infon.termino}: {infon.razon_auditoria[:110]}"
                    )
            else:
                medida.sin_numero += 1

    await ctx.cerrar()
    return medida


def informe(medidas: list[Medida]) -> None:
    print("\n" + "=" * 74)
    print("  COMPARATIVA DE FORMATOS DE PROTOCOLO")
    print("=" * 74)
    print(f"\n  Nota: pancreatitis aguda, protocolo forzado a '{PROTOCOLO}'.\n")

    cab = f"  {'formato':11} {'validados':>11} {'alertas':>9} {'ruido':>7} "
    cab += f"{'corte real':>11} {'inventado':>10} {'sin cifra':>10}"
    print(cab)
    print("  " + "-" * 70)
    for m in medidas:
        print(
            f"  {m.formato:11} {m.validados:>6}/{m.total:<4} {m.alertas:>9} "
            f"{m.ruido:>7} {m.con_corte:>11} {m.corte_inventado:>10} "
            f"{m.sin_numero:>10}"
        )

    print("\n  Las tres últimas columnas cuentan sólo los hallazgos derivados")
    print("  de un criterio de laboratorio, que son los que tienen un corte")
    print("  que citar.\n")

    for m in medidas:
        if m.ejemplos:
            print(f"  Cortes inventados con formato '{m.formato}':")
            for e in m.ejemplos:
                print(f"    · {e}")
            print()


async def main_async(repeticiones: int) -> int:
    medidas = []
    for formato in Skill.FORMATOS:
        print(f"[{formato}] ejecutando {repeticiones} vez/veces…", flush=True)
        medidas.append(await medir(formato, repeticiones))
    informe(medidas)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repeticiones",
        type=int,
        default=1,
        help="Ejecuciones por formato. Con temperatura 0 la varianza es baja, "
        "pero no nula: los modelos cuantizados no son del todo deterministas.",
    )
    args = parser.parse_args()
    return asyncio.run(main_async(args.repeticiones))


if __name__ == "__main__":
    raise SystemExit(main())
