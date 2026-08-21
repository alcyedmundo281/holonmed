"""El Φ categórico no ve el resto no simbolizado. Y qué pasa con uno delgado."""
import math, sys; sys.path.insert(0, __import__("os").environ.get("HOLONMED_BACKEND", "."))
from holonmed.core.skills import Skill
from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.models import EstadoInfon, Infon, Polaridad

def cat(titulo, signos):
    cuerpo = "\n".join(f'  - nombre: {s}\n    fuente: "Postuma 2015"' for s in signos)
    return Skill(titulo, f"---\ntitulo: {titulo}\nsignos:\n{cuerpo}\n---\n\nP\n")

def infon(t, pol=Polaridad.PRESENTE):
    return Infon(texto_origen=t, termino_propuesto=t, termino=t, polaridad=pol,
                 estado=EstadoInfon.VALIDADO, confianza=95.0,
                 razon_auditoria="[lexico] emparejado")

GRUESO = cat("Parkinson", ["Bradicinesia", "Rigidez parkinsoniana",
                           "Temblor de reposo", "Respuesta a levodopa"])
DELGADO = cat("Hipotesis delgada", ["Bradicinesia", "Rigidez parkinsoniana"])
AJENOS = [infon(x) for x in ["Cefalea", "Artralgia", "Prurito", "Disuria",
                             "Epistaxis", "Acufenos"]]
vistos = [infon("Bradicinesia"), infon("Rigidez parkinsoniana")]
m = MedidorDeAcoplamiento()

print("1) ¿ve el categórico el resto no simbolizado?")
for n, extra in (("dos a favor, sin resto", []), ("los mismos + 6 ajenos", AJENOS)):
    a = m.medir(GRUESO, vistos + extra)
    print(f"   {n:<26} Φ_cat = {a.phi_categorico:.4f}   "
          f"resto = {len(a.resto_no_simbolizado)}")

print("\n2) el protocolo delgado, con el paciente entero sin explicar")
a = m.medir(DELGADO, vistos + AJENOS)
print(f"   declara 2 signos, ambos constan, 6 hallazgos ajenos")
print(f"   Φ_cat = {a.phi_categorico:.4f}   resto = {len(a.resto_no_simbolizado)}")
print("   ARMONÍA PERFECTA con seis hallazgos que no explica.")

print("\n3) el arreglo simétrico: m -> m + r en el denominador")
def phi_cat_corregido(skill, infones, alfa):
    from holonmed.core.bayes import emparejar_termino
    dims = [s for s in skill.signos if s.efecto != "excluye"]
    idx = {s.nombre.lower(): s for s in dims}
    contrib, r = {}, 0
    for i in infones:
        if not i.es_valido:
            continue
        k = emparejar_termino(i.termino, idx)
        if k is None:
            if i.polaridad is Polaridad.PRESENTE:
                r += 1
            continue
        if k in contrib:
            continue
        obs = "presente" if i.polaridad is Polaridad.PRESENTE else "ausente"
        contrib[k] = -1 if obs == idx[k].polaridad_adversa else 1
    mm = len(contrib)
    if not mm:
        return 0.0
    return alfa * sum(contrib.values()) / math.sqrt(len(dims) * (mm + r))

for nombre, sk, inf in (
    ("grueso, sin resto", GRUESO, vistos),
    ("grueso, + 6 ajenos", GRUESO, vistos + AJENOS),
    ("delgado, sin resto", DELGADO, vistos),
    ("delgado, + 6 ajenos", DELGADO, vistos + AJENOS),
):
    a = m.medir(sk, inf)
    corr = phi_cat_corregido(sk, inf, a.anclaje)
    print(f"   {nombre:<22} hoy {a.phi_categorico:>7.4f}   corregido {corr:>7.4f}")
