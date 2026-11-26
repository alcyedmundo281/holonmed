"""Mide qué condición separa un sinónimo legítimo de un concepto equivocado.

No usa ningún modelo. Supone el peor re-ranking para los errores (elige
cualquier candidato equivocado que se le ofrezca) y el mejor para los
aciertos (elige el correcto si está entre los candidatos).

* **Sinónimo legítimo no declarado**: se quita un sinónimo del índice y se
  consulta. Su concepto correcto es conocido.
* **Concepto ausente**: se quita el concepto entero y se consultan sus
  términos. Cualquier candidato que quede es, por construcción, otro concepto.

Son sustitutos, no narrativa clínica: miden el espacio de lo que el motor
permite, no con qué frecuencia ocurre.

    cd backend && python scripts/medir_normalizacion.py
"""

import json
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from rapidfuzz import fuzz  # noqa: E402

from holonmed.core.terminology import (  # noqa: E402
    Candidato,
    TerminologyIndex,
    VocabularyLoader,
)
from holonmed.core.validator import SEMANTICAS_NO_ASIGNABLES, hay_colision  # noqa: E402
from holonmed.db.store import Database, GraphRepo, normalizar  # noqa: E402

SEMILLA = RAIZ / "data" / "vocabulario_semilla.json"
VACIAS = {"de", "del", "la", "el", "los", "las", "en", "con", "por", "a", "al", "y"}

Regla = Callable[[str, Candidato, list[str]], bool]


def _palabras(texto: str) -> list[str]:
    return [p for p in normalizar(texto).split() if p not in VACIAS]


def _cubierta(
    consulta: str, variantes: list[str], minimo: int, solo_primera: bool
) -> bool:
    conocidas = {p for v in variantes for p in _palabras(v)}
    exigidas = _palabras(consulta)[:1] if solo_primera else _palabras(consulta)
    return all(any(fuzz.ratio(a, b) >= minimo for b in conocidas) for a in exigidas)


def _reglas() -> dict[str, Regla]:
    reglas: dict[str, Regla] = {"anterior (> 40)": lambda q, c, v: c.score > 40}
    for t in (60, 70, 75, 80, 85, 92):
        reglas[f"similitud >= {t}"] = lambda q, c, v, t=t: c.score >= t
    for t in (75, 85):
        reglas[f"cada palabra cubierta (>= {t})"] = lambda q, c, v, t=t: _cubierta(
            q, v, t, False
        )
        reglas[f"primera palabra cubierta (>= {t})"] = lambda q, c, v, t=t: _cubierta(
            q, v, t, True
        )
    return reglas


def main() -> None:
    conceptos = json.loads(SEMILLA.read_text(encoding="utf-8"))["conceptos"]
    variantes = {
        c["codigo"]: list(dict.fromkeys([c["termino"], *c.get("sinonimos", [])]))
        for c in conceptos
    }

    with tempfile.TemporaryDirectory() as carpeta:
        db = Database(Path(carpeta) / "medicion.db")
        VocabularyLoader(db).cargar_semilla(SEMILLA)
        indice = TerminologyIndex(db, GraphRepo(db))
        cx = db.conexion()

        def ofrecidos(consulta: str) -> list[Candidato]:
            # Lo que de verdad llegaría al re-ranking y pasaría sus guardas.
            return [
                c
                for c in indice.buscar_candidatos(consulta, 15)
                if c.semantica not in SEMANTICAS_NO_ASIGNABLES
                and not hay_colision(consulta, c.termino)
            ]

        sinonimos: list[tuple[str, Candidato | None, list[str]]] = []
        ausentes: list[tuple[str, list[Candidato]]] = []
        for concepto in conceptos:
            if concepto.get("semantica") in SEMANTICAS_NO_ASIGNABLES:
                continue
            codigo = concepto["codigo"]
            cid = cx.execute(
                "SELECT id FROM concepto WHERE codigo = ?", (codigo,)
            ).fetchone()["id"]
            filas = cx.execute(
                "SELECT id, texto, preferente FROM termino WHERE concepto_id = ?",
                (cid,),
            ).fetchall()

            for fila in filas:
                if fila["preferente"]:
                    continue
                cx.execute("DELETE FROM termino WHERE id = ?", (fila["id"],))
                if indice.buscar_exacto(fila["texto"]) is None:
                    correcto = next(
                        (c for c in ofrecidos(fila["texto"]) if c.codigo == codigo),
                        None,
                    )
                    resto = [v for v in variantes[codigo] if v != fila["texto"]]
                    sinonimos.append((fila["texto"], correcto, resto))
                cx.rollback()

            cx.execute("DELETE FROM termino WHERE concepto_id = ?", (cid,))
            for fila in filas:
                if indice.buscar_exacto(fila["texto"]) is None:
                    ausentes.append((fila["texto"], ofrecidos(fila["texto"])))
            cx.rollback()

        cx.close()

    recuperados = [(q, c, v) for q, c, v in sinonimos if c is not None]
    pares = sum(len(cs) for _, cs in ausentes)
    print(
        f"Sinónimos retirados: {len(sinonimos)}; con su concepto entre los "
        f"candidatos: {len(recuperados)}"
    )
    print(
        f"Consultas sin su concepto: {len(ausentes)}; con algún candidato (todos "
        f"erróneos): {sum(bool(cs) for _, cs in ausentes)}; pares: {pares}\n"
    )
    print(
        "| Condición para poder quedar VALIDADO | Sinónimos correctos que la "
        "cumplen | Consultas con algún erróneo que la cumple | Pares erróneos |"
    )
    print("|---|---|---|---|")
    for nombre, regla in _reglas().items():
        buenos = sum(regla(q, c, v) for q, c, v in recuperados)
        consultas = sum(
            any(regla(q, c, variantes[c.codigo]) for c in cs) for q, cs in ausentes
        )
        malos = sum(regla(q, c, variantes[c.codigo]) for q, cs in ausentes for c in cs)
        print(
            f"| {nombre} | {buenos} ({buenos / len(recuperados):.1%}) | "
            f"{consultas} ({consultas / len(ausentes):.1%}) | "
            f"{malos} ({malos / pares:.1%}) |"
        )

    print("\nPares erróneos con similitud >= 85:")
    altos = {(q, c.termino, c.score) for q, cs in ausentes for c in cs if c.score >= 85}
    for consulta, termino, score in sorted(altos, key=lambda p: (-p[2], p[0], p[1])):
        print(f"  {score:5.1f}  {consulta} -> {termino}")


if __name__ == "__main__":
    main()
