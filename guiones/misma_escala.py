"""¿Es la lectura categórica la ponderada con pesos uniformes?

Si lo es, las dos comparten escala y pueden competir sin traducción. Se
comprueba construyendo el mismo caso de las dos maneras.
"""
import sys

sys.path.insert(0, __import__("os").environ.get("HOLONMED_BACKEND", "."))
from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.core.skills import Skill
from holonmed.models import EstadoInfon, Infon, Polaridad

CITA = 'fuente: "Postuma RB et al, Mov Disord 2015"'


def protocolo(titulo, lrs):
    """`lrs=None` en un signo lo deja categórico: declarado y sin cociente."""
    cuerpo = "\n".join(
        f"  - nombre: Signo {i}\n    {CITA}" + (f"\n    lr: {lr}" if lr else "")
        for i, lr in enumerate(lrs)
    )
    return Skill(titulo, f"---\ntitulo: {titulo}\nsignos:\n{cuerpo}\n---\n\nP\n")


def infon(t):
    return Infon(texto_origen=t, termino_propuesto=t, termino=t,
                 polaridad=Polaridad.PRESENTE, estado=EstadoInfon.VALIDADO,
                 confianza=95.0, razon_auditoria="[lexico] emparejado")


m = MedidorDeAcoplamiento()
visto = [infon("Signo 0")]          # cinco declarados, uno presente

estrella = m.medir(protocolo("estrella", [26.6, 2.0, 2.0, 2.0, 2.0]), visto)
uniforme = m.medir(protocolo("uniforme", [2.0, 2.0, 2.0, 2.0, 2.0]), visto)
categorico = m.medir(protocolo("categorico", [None] * 5), visto)

print(f"{'lectura':<52} {'coseno':>8}")
print(f"{'ponderado · un LR estrella (26.6) y cuatro de 2.0':<52} "
      f"{estrella.coseno:>8.4f}")
print(f"{'ponderado · los cinco iguales (2.0)':<52} {uniforme.coseno:>8.4f}")
# El categórico crudo: phi_categorico se expone ya multiplicado por α, así
# que para comparar escalas hay que dividirlo.
crudo = categorico.phi_categorico / categorico.anclaje
print(f"{'categórico · los cinco iguales por definición':<52} {crudo:>8.4f}")

print()
print("uniforme == categórico:", round(uniforme.coseno, 4) == round(crudo, 4))
print("Si coinciden, la categórica es la ponderada con pesos uniformes y las")
print("dos comparten escala: el coseno es invariante de escala, y con pesos")
print("todos iguales la escala se cancela.")
