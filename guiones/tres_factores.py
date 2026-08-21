"""¿Es cos = direccion · √cobertura · √explicacion? Y ¿qué hace el categórico?"""
import math, sys; sys.path.insert(0, __import__("os").environ.get("HOLONMED_BACKEND", "."))
from holonmed.core.skills import Skill
from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.models import EstadoDimension, EstadoInfon, Infon, Polaridad

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

def factores(a):
    decl = [c for c in a.componentes if c.estado is not EstadoDimension.NO_SIMBOLIZADO]
    resto = [c for c in a.componentes if c.estado is EstadoDimension.NO_SIMBOLIZADO]
    S = [c for c in decl if c.estado in (EstadoDimension.CONCUERDA,
                                         EstadoDimension.CONTRADICE)]
    h2, hS2 = sum(c.esperado**2 for c in decl), sum(c.esperado**2 for c in S)
    eS2 = sum(c.observado**2 for c in S)
    e2 = eS2 + sum(c.observado**2 for c in resto)
    if not (h2 and eS2):
        return 0.0, 0.0, 0.0
    direccion = sum(c.esperado*c.observado for c in S)/(math.sqrt(hS2)*math.sqrt(eS2))
    return direccion, hS2/h2, eS2/e2

base = [infon("Dolor en fosa iliaca derecha"), infon("Migracion del dolor")]
ajenos = [infon("Cefalea"), infon("Artralgia"), infon("Prurito")]
m = MedidorDeAcoplamiento()

print(f"{'caso':<32} {'cos real':>9} {'dir':>7} {'cob':>7} {'expl':>7} "
      f"{'2 factores':>11} {'3 factores':>11}")
for n, extra in (("sin resto", []), ("+1 ajeno", ajenos[:1]), ("+3 ajenos", ajenos)):
    a = m.medir(SK, base + extra)
    d, cob, ex = factores(a)
    print(f"{n:<32} {a.coseno:>9.4f} {d:>7.4f} {cob:>7.4f} {ex:>7.4f} "
          f"{d*math.sqrt(cob):>11.4f} {d*math.sqrt(cob*ex):>11.4f}")
