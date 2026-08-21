"""Weed: el diagnóstico cristalizado SUSTITUYE a sus hallazgos en la lista.

`pomr.py` mide la guarda de Φ —acuñar el trastorno no mueve el coeficiente—
pero eso NO prueba nada sobre la lista de problemas, que es lo que la §9.2
afirma. Ésta es la otra mitad, contra SQLite real.
"""
import json, os, sys, tempfile
from pathlib import Path

sys.path.insert(0, os.environ.get("HOLONMED_BACKEND", "."))

from holonmed.core.terminology import VocabularyLoader   # noqa: E402
from holonmed.db import Database                          # noqa: E402

VOCAB = {"conceptos": [
    {"codigo": "T:0", "termino": "Hallazgo clínico"},
    {"codigo": "T:1", "termino": "Disnea", "padre": "T:0"},
    {"codigo": "T:2", "termino": "Ingurgitacion yugular", "padre": "T:0"},
    {"codigo": "T:3", "termino": "Edema periferico", "padre": "T:0"},
    {"codigo": "T:4", "termino": "Insuficiencia cardiaca", "padre": "T:0"},
]}

d = Path(tempfile.mkdtemp())
(d / "v.json").write_text(json.dumps(VOCAB), encoding="utf-8")
db = Database(d / "pomr.db")
VocabularyLoader(db).cargar_semilla(d / "v.json")
cx = db.conexion()
cx.execute("INSERT INTO paciente (id, nombre, creado) VALUES "
           "('P1','Prueba','2024-01-01T00:00:00')")
cx.execute("INSERT INTO tic (id,paciente_id,timestamp,origen,actor,skill,"
           "texto_original,resumen) VALUES (1,'P1','2024-03-01T09:00:00',"
           "'consulta','Dr. A','icc','t','disnea')")

def cid(codigo):
    f = cx.execute("SELECT id FROM concepto WHERE codigo=? LIMIT 1", (codigo,)).fetchone()
    return f["id"] if f else None

# Los tres hallazgos, y el trastorno que el clasificador acuña a partir de
# ellos: lleva `derivado_de`, que es lo que lo distingue de un hallazgo.
for codigo, termino, derivado in (
    ("T:1", "Disnea", None),
    ("T:2", "Ingurgitacion yugular", None),
    ("T:3", "Edema periferico", None),
    ("T:4", "Insuficiencia cardiaca",
     json.dumps(["Disnea", "Ingurgitacion yugular", "Edema periferico"])),
):
    cx.execute(
        "INSERT INTO infon (tic_id,paciente_id,concepto_id,timestamp,texto_origen,"
        "termino_propuesto,termino,polaridad,derivado_de,codigo,sistema,estado,"
        "confianza) VALUES (1,'P1',?,'2024-03-01T09:00:00',?,?,?,'presente',?,?,"
        "'holonmed','VALIDADO',95)",
        (cid(codigo), termino, termino, termino, derivado, codigo))
cx.commit()

from holonmed.db import GraphRepo, TicRepo   # noqa: E402
repo = TicRepo(db, GraphRepo(db))
lista = repo.lista_problemas("P1")
total = cx.execute("SELECT COUNT(*) c FROM infon WHERE paciente_id='P1'").fetchone()["c"]

print(f"infones guardados: {total}   filas en la lista: {len(lista)}")
print(f"{'problema':<26} {'codigo':<8} {'apar':>4}  ¿derivado?")
for p in lista:
    trae = "derivado_de" in p
    print(f"{p['termino']:<26} {p['codigo'] or '':<8} {p['apariciones']:>4}  "
          f"{'sí' if trae else 'no se sabe: la consulta no lo trae'}")
print()
print("Weed: con disnea, ingurgitación y edema se pone UN problema —insuficiencia")
print("cardiaca—, no cuatro. La lista los muestra todos, y no puede filtrarlos:")
print("`derivado_de` se persiste pero no aparece en el SELECT.")
