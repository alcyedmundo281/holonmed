"""La misma identidad, por un camino que no pasa por `componentes`.

`tres_factores.py` lee `acop.componentes` y reparte sus columnas. Es una
comprobación de la identidad, no del vector: si `_componer` colocara mal un
peso, la descomposición cuadraría con el error dentro y el guion seguiría
en verde.

Éste no mira `componentes`. Reconstruye `h` y `e` desde el YAML del
protocolo y los infones —con emparejamiento por nombre exacto, sin usar
`emparejar_termino`— y compara su propio coseno con el que publica `medir`.
Si los dos coinciden, la identidad es cierta *y* el vector que se
descompone es el que Φ usa de verdad.

Las convenciones se leen de los docstrings de `acoplamiento.py`:

    hᵢ = ln(LR+)          y −ln(LR−) cuando el signo sólo declara LR−
    eᵢ = ln(LR+)          el registro lo da presente
         ln(LR−)          el registro lo da ausente
         0                nadie lo ha mirado
    resto: hᵢ = 0, eᵢ = la media cuadrática de los eᵢ que sí se explicaron
"""
import math
import sys

sys.path.insert(0, __import__("os").environ.get("HOLONMED_BACKEND", "."))
from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.core.skills import Skill
from holonmed.models import EstadoInfon, Infon, Polaridad

SK = Skill("apendicitis", """---
titulo: Apendicitis aguda
signos:
  - nombre: Dolor en fosa iliaca derecha
    lr: 8.0
    lr_negativo: 0.2
    fuente: "Wagner 1996"
  - nombre: Migracion del dolor
    lr: 3.1
    lr_negativo: 0.5
    fuente: "Wagner 1996"
  - nombre: Signo de Blumberg
    lr: 3.4
    lr_negativo: 0.4
    fuente: "Wagner 1996"
  - nombre: Anorexia
    lr: 1.3
    lr_negativo: 0.6
    fuente: "Wagner 1996"
  - nombre: Fiebre
    lr: 1.9
    lr_negativo: 0.6
    fuente: "Wagner 1996"
---

P
""")


def infon(t, pol=Polaridad.PRESENTE):
    return Infon(texto_origen=t, termino_propuesto=t, termino=t, polaridad=pol,
                 estado=EstadoInfon.VALIDADO, confianza=95.0,
                 razon_auditoria="[lexico] emparejado")


def vectores(skill, infones):
    """`h` y `e` a mano, desde el YAML. Devuelve (h, e, cuáles están medidas)."""
    visto = {i.termino.lower(): i for i in infones}
    h, e, medida = [], [], []

    for signo in skill.signos:
        if signo.lr:
            hi = math.log(signo.lr)
        elif signo.lr_negativo:
            hi = -math.log(signo.lr_negativo)
        else:
            continue                       # no declara cociente: no es dimensión

        i = visto.get(signo.nombre.lower())
        if i is None:
            ei = 0.0                       # SIN_MEDIR: vacío, no ausencia
        elif i.polaridad is Polaridad.AUSENTE:
            ei = math.log(signo.lr_negativo) if signo.lr_negativo else 0.0
        else:
            ei = math.log(signo.lr) if signo.lr else 0.0

        h.append(hi)
        e.append(ei)
        medida.append(ei != 0.0)

    # El resto: lo validado y presente que ningún signo declarado nombra.
    declarados = {s.nombre.lower() for s in skill.signos}
    ajenos = {i.termino.lower() for i in infones
              if i.polaridad is Polaridad.PRESENTE
              and i.termino.lower() not in declarados}
    if ajenos:
        pesados = [abs(v) for v in e if v]
        peso = math.sqrt(sum(v**2 for v in pesados) / len(pesados)) if pesados else 0.0
        for _ in ajenos:
            h.append(0.0)
            e.append(peso)
            medida.append(False)

    return h, e, medida


def coseno(h, e):
    nh = math.sqrt(sum(v**2 for v in h))
    ne = math.sqrt(sum(v**2 for v in e))
    return sum(a * b for a, b in zip(h, e)) / (nh * ne) if nh and ne else 0.0


def factores(h, e, medida):
    """dirección, cobertura y explicación, cada uno de su definición."""
    hS = [v for v, m in zip(h, medida) if m]
    eS = [v for v, m in zip(e, medida) if m]
    if not hS:
        return 0.0, 0.0, 0.0
    # cobertura es del lado h y sólo cuenta lo DECLARADO: el resto tiene h=0
    # y por tanto no entra en ‖h‖ aunque esté en la lista.
    return (coseno(hS, eS),
            sum(v**2 for v in hS) / sum(v**2 for v in h),
            sum(v**2 for v in eS) / sum(v**2 for v in e))


base = [infon("Dolor en fosa iliaca derecha"), infon("Migracion del dolor")]
ajenos = [infon("Cefalea"), infon("Artralgia"), infon("Prurito")]
m = MedidorDeAcoplamiento()

print(f"{'caso':<24} {'cos de medir()':>14} {'cos a mano':>11} "
      f"{'dir':>7} {'cob':>7} {'expl':>7} {'dir·√(cob·expl)':>16}")
for nombre, extra in (("sin resto", []), ("+1 ajeno", ajenos[:1]),
                      ("+3 ajenos", ajenos)):
    infones = base + extra
    a = m.medir(SK, infones)
    h, e, medida = vectores(SK, infones)
    d, cob, expl = factores(h, e, medida)
    print(f"{nombre:<24} {a.coseno:>14.4f} {coseno(h, e):>11.4f} "
          f"{d:>7.4f} {cob:>7.4f} {expl:>7.4f} {d * math.sqrt(cob * expl):>16.4f}")

print()
print("Las tres columnas de coseno tienen que coincidir. La primera sale de")
print("`componentes`; la segunda y la tercera no lo tocan.")
