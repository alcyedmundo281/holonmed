"""Los tres niveles de la decisión: vetar, contar, balancear.

El motor bayesiano dice cuánta evidencia hay y Φ dice si armoniza con el
paciente. Falta la parte que ningún número continuo puede expresar: que hay
hipótesis **imposibles**, y que los criterios publicados deciden contando.

LA FORMA VIENE DE LOS CRITERIOS PUBLICADOS
------------------------------------------
Los criterios MDS 2015 para la enfermedad de Parkinson (Postuma RB et al,
Mov Disord 2015;30(12):1591-601, doi:10.1002/mds.26424) separan tres cosas
que un sistema de apoyo tiende a confundir en una sola:

* **Criterios de exclusión absoluta** — descartan. No se contrarrestan con
  nada.
* **Banderas rojas** — restan, pero **sí** se contrarrestan con criterios de
  apoyo, uno por uno y hasta un tope.
* **Criterios de apoyo** — suman confianza.

Y dos grados de certeza: *establecida*, que maximiza especificidad a costa
de sensibilidad, y *probable*, que las equilibra.

POR QUÉ TRES MECANISMOS Y NO UNO
--------------------------------
Los tres parecen la misma cosa con distinto signo, y no lo son.

**La exclusión no es un likelihood ratio.** Un cociente de 0.001 deja una
probabilidad pequeña pero distinta de cero, y ninguna cantidad de evidencia
posterior la lleva a cero. Un paciente apendicectomizado no tiene poca
probabilidad de apendicitis: no puede tenerla. Eso es una imposibilidad
estructural, no una improbabilidad, y por eso vive fuera de Bayes y fuera de
Φ.

**El tope de banderas tampoco es un balance.** Se midió: un coseno es
continuo y monótono en el balance entre lo que apoya y lo que resta, de modo
que no puede expresar un corte. Con los enteros de MDS, cuatro apoyos y tres
banderas queda rechazado por el criterio y sin embargo da Φ positiva, por
encima de casos que el criterio acepta. El tope se comporta como una
exclusión contada, y aquí se trata como tal.

**El balance sí es continuo**, y ahí Φ hace mejor trabajo que el conteo:
pondera por `ln(LR)` donde hay cociente publicado, en vez de contar cada
signo como uno. Un panel de expertos no puede multiplicar logaritmos a mano;
este módulo sí.

LO QUE ESTE MÓDULO NO HACE
--------------------------
No decide los enteros. `apoyos_minimos`, `contrapeso` y `banderas_maximas`
los declara el protocolo, que a su vez los toma del criterio publicado con
su cita. Buscar un umbral universal por simulación es un error de categoría:
el umbral es específico de la enfermedad y lo fija quien redacta el
criterio, igual que fija los likelihood ratios.

No llama al LLM. El modelo propone términos; **la tabla decide**. Ninguna de
las tres categorías puede salir de un juicio del modelo, y menos la
exclusión, cuyo falso positivo retira un diagnóstico correcto en silencio.

Y no reconcilia su veredicto con la probabilidad. Se leen juntos y por
separado: cuando el criterio contado y la aritmética discrepan, la
discrepancia es información clínica.
"""

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..models import Infon, Polaridad, VeredictoDeclarado, Veto

if TYPE_CHECKING:  # pragma: no cover - sólo para tipado
    from .skills import Signo, Skill

logger = logging.getLogger(__name__)


def _emparejador(presentes: Sequence[str]):
    """Devuelve una función que decide si un término consta como presente.

    Usa el mismo emparejamiento por subcadena que el motor bayesiano, para
    que el núcleo y los signos no puedan divergir.
    """
    from .bayes import emparejar_termino

    indice = {t.lower(): t for t in presentes}
    return lambda termino: emparejar_termino(termino, indice) is not None


class EvaluadorDeVeredicto:
    """Aplica los tres niveles declarados por el protocolo a un paciente."""

    def evaluar(
        self, skill: "Skill", infones: Sequence[Infon]
    ) -> VeredictoDeclarado | None:
        """Devuelve el veredicto contado, o None si el protocolo no declara nada.

        Se devuelve None —y no un veredicto vacío— cuando el protocolo no
        declara ni exclusiones ni banderas ni balance: son situaciones
        distintas. Un veredicto sin nivel dice que el criterio no se
        cumple; None dice que no hay criterio que aplicar.
        """
        hipotesis = str(skill.condicion.get("nombre") or skill.titulo)
        declara_efectos = any(s.efecto != "apoya" for s in skill.signos)
        if not declara_efectos and not skill.balance.declarado:
            return None

        observados = self._observar(skill, infones)
        traza: list[str] = []

        # --- NIVEL 1: los vetos ---------------------------------------
        veto = self._buscar_exclusion(observados, hipotesis)
        if veto:
            traza.append(f"Exclusión absoluta: {veto.motivo}")
            return VeredictoDeclarado(
                veto=veto, fuente=skill.balance.fuente, traza=traza
            )

        apoyos = [
            i.termino for s, i in observados if s.efecto == "apoya" and _dispara(s, i)
        ]
        banderas = [
            i.termino
            for s, i in observados
            if s.efecto == "bandera_roja" and _dispara(s, i)
        ]
        traza.append(f"{len(apoyos)} apoyo(s), {len(banderas)} bandera(s) roja(s)")

        # --- NIVEL 2: el núcleo ---------------------------------------
        # Sin el rasgo central, el criterio no se aplica. No es que el
        # diagnóstico sea imposible: es que la pregunta todavía no se puede
        # hacer.
        if skill.nucleo.declarado:
            presentes = [
                i.termino for _, i in observados if i.polaridad is Polaridad.PRESENTE
            ]
            if not skill.nucleo.satisfecho(_emparejador(presentes)):
                traza.append(
                    "Núcleo no documentado: el criterio no se aplica todavía"
                )
                return VeredictoDeclarado(
                    apoyos=apoyos,
                    banderas_rojas=banderas,
                    fuente=skill.balance.fuente,
                    traza=traza,
                )

        # --- NIVEL 3: el tope de banderas -----------------------------
        # Va DESPUÉS del núcleo y no antes. Una exclusión absoluta sí
        # precede a todo —una apendicectomía excluye la apendicitis se haya
        # documentado lo que se haya documentado— pero el tope es una
        # propiedad de la tabla de balance, y el núcleo es justamente lo
        # que condiciona que esa tabla se aplique. MDS documenta el
        # parkinsonismo primero y sólo después juzga la causa.
        if skill.balance.declarado and len(banderas) > skill.balance.banderas_tolerables:
            veto = Veto(
                tipo="tope_banderas",
                motivo=(
                    f"{len(banderas)} banderas rojas, y el criterio no admite más de "
                    f"{skill.balance.banderas_tolerables}: ningún apoyo lo contrarresta"
                ),
                hipotesis=hipotesis,
            )
            traza.append(veto.motivo)
            return VeredictoDeclarado(
                veto=veto,
                apoyos=apoyos,
                banderas_rojas=banderas,
                fuente=skill.balance.fuente,
                traza=traza,
            )

        # --- NIVEL 4: el balance declarado ----------------------------
        nivel = None
        if not apoyos and not banderas:
            # Cero apoyos y cero banderas no es un caso equilibrado: es un
            # caso del que no consta nada que cuente. Un balance que admita
            # «cero apoyos mínimos» daría por probable un diagnóstico sobre
            # el vacío, porque 0 ≥ 0 se cumple.
            #
            # Se mira lo que DISPARA y no lo que empareja: basta un signo
            # emparejado que no active su efecto —un `dispara_si: ausente`
            # que conste presente— para que la lista de observados deje de
            # estar vacía sin que nada sostenga el diagnóstico.
            traza.append("Nada que cuente: no hay balance que evaluar")
        elif skill.balance.declarado:
            for candidato in skill.balance.niveles:
                if candidato.satisface(len(apoyos), len(banderas)):
                    nivel = candidato.nombre
                    traza.append(f"Alcanza el nivel «{candidato.nombre}»")
                    break
            if nivel is None:
                traza.append("No alcanza ningún nivel de certeza declarado")

        return VeredictoDeclarado(
            nivel=nivel,
            apoyos=apoyos,
            banderas_rojas=banderas,
            fuente=skill.balance.fuente,
            traza=traza,
        )

    # --- Emparejamiento ------------------------------------------------

    @staticmethod
    def _observar(
        skill: "Skill", infones: Sequence[Infon]
    ) -> list[tuple["Signo", Infon]]:
        """Empareja infones validados con los signos que el protocolo declara.

        Se reutiliza el emparejamiento del motor bayesiano para que los tres
        módulos vean el mismo vector. Sólo entra evidencia VALIDADA: un
        hallazgo en alerta se le muestra al clínico pero no veta un
        diagnóstico ni satisface un criterio.
        """
        from .bayes import emparejar_termino

        indice = {s.nombre.lower(): s for s in skill.signos}
        salida: list[tuple[Signo, Infon]] = []
        vistos: set[str] = set()

        for infon in infones:
            if not infon.es_valido:
                continue
            clave = emparejar_termino(infon.termino, indice)
            if clave is None or clave in vistos:
                continue
            vistos.add(clave)   # un signo cuenta una vez, no dos
            salida.append((indice[clave], infon))
        return salida

    @staticmethod
    def _buscar_exclusion(
        observados: Sequence[tuple["Signo", Infon]], hipotesis: str
    ) -> Veto | None:
        for signo, infon in observados:
            if signo.efecto == "excluye" and _dispara(signo, infon):
                return Veto(
                    tipo="exclusion_absoluta",
                    motivo=f"{infon.termino} — {signo.fuente or 'exclusión declarada'}",
                    termino=infon.termino,
                    hipotesis=hipotesis,
                )
        return None


def _dispara(signo: "Signo", infon: Infon) -> bool:
    """¿La polaridad observada activa el efecto declarado?

    La distinción entre ausencia documentada y silencio se hereda del resto
    del sistema y aquí es donde más importa: que no conste dolor en fosa
    ilíaca derecha no es lo mismo que constar que no lo hay, y sólo lo
    segundo levanta una bandera.
    """
    observada = "presente" if infon.polaridad is Polaridad.PRESENTE else "ausente"
    return observada == signo.dispara_si
