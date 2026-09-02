"""Cuándo un hallazgo deja de ser un problema y pasa a ser un diagnóstico.

LA PREGUNTA, QUE ES DISTINTA DE LAS OTRAS TRES
----------------------------------------------
El motor bayesiano dice cuánta evidencia hay. Φ dice si armoniza con el
paciente. El veredicto declarado dice si es posible y qué dice el criterio
contado. Ninguna de las tres responde a la que un clínico hace al final:

    ¿esto sigue siendo un problema en la lista, o ya es un diagnóstico?

Weed la separó en 1968 y el sistema la tenía fundida con la probabilidad.
Una probabilidad alta no promueve por sí sola: un dato fuerte puede
empujarla al 95 % con el resto del cuadro sin mirar.

LA TUPLA
--------
Tres elementos, y los tres tienen que estar:

    una clínica positiva          `manifestacion`
    una prueba sensible positiva  `prueba_sensible`     SnNOut
    una prueba específica positiva `prueba_especifica`  SpPIn

Los tres roles ya existían entre los cinco de `ROLES`. Lo que faltaba era
declarar que **juntos deciden**, que es otra cosa que sumar apoyos.

POR QUÉ LA SENSIBLE SE EXIGE EN POSITIVO
----------------------------------------
Parece redundante junto a la específica, y no lo es: exigirla en positivo
significa que **una sensible negativa impide la promoción**. Es SnNOut usado
como compuerta. Y encaja con lo que el índice publica: de las cuatro
condiciones que hoy declaran la tupla entera, tres traen su prueba sensible
**sólo con LR−** —Criterios de Light 0.04, adenopatía cervical anterior 0.6,
hipertrofia amigdalina 0.63—, porque el poder de una prueba sensible vive en
lo que descarta cuando sale negativa.

LO QUE PASA SI LA TUPLA NO SE COMPLETA
--------------------------------------
El hallazgo **se queda como problema**. No se emite un diagnóstico con
reservas ni se rebaja de grado: no se emite. Es la parsimonia del primer día
—la explicación única supera a la múltiple— aplicada a la promoción, y es la
regla clínica que el autor fijó antes de que hubiera código.

LO QUE ESTE MÓDULO NO HACE
--------------------------
No decide el umbral. `umbral_postest` es una **política del servicio**, no un
dato de la enfermedad: dice cuánta certeza se exige antes de actuar, y es
legítimo que sea distinta para un cuadro letal y tratable. Ninguna revista
publica «actúe por encima del 90 %», así que no lleva PMID y por eso el
esquema le exige `motivo` en prosa — el mismo precedente que `sostiene:
mecanismo` en el índice.

No veta. Que una prueba sensible conste negativa impide promover, y eso no
es lo mismo que descartar el diagnóstico. Si una ausencia documentada debe
descartar, el índice lo declara con `efecto: excluye` y `dispara_si:
ausente`, que ya existe y corre antes que esto.

Y no llama al LLM. El modelo propone términos; los roles los declara el
índice contra PubMed, y aquí sólo se cuentan.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..models import InferenciaBayesiana, Infon, Polaridad
from ..models import Promocion as Veredicto

if TYPE_CHECKING:  # pragma: no cover - sólo para tipado
    from .skills import Signo, Skill

logger = logging.getLogger(__name__)


class EvaluadorDePromocion:
    """Aplica la tupla declarada por el protocolo al paciente de hoy."""

    def evaluar(
        self,
        skill: Skill,
        infones: Sequence[Infon],
        inferencia: InferenciaBayesiana | None = None,
    ) -> Veredicto | None:
        """Devuelve el veredicto de promoción, o None si no hay regla.

        None —y no un veredicto negativo— cuando el protocolo no declara
        `promocion`: son situaciones distintas. Un veredicto que no promueve
        dice que la tupla no se completó; None dice que nadie ha declarado
        qué haría falta, y en ese caso el sistema se comporta como antes.
        """
        regla = skill.promocion
        if not regla.declarada:
            return None

        hipotesis = str(skill.condicion.get("nombre") or skill.titulo)
        observados = self._satisfechos(skill, infones)

        cumplidos: dict[str, list[str]] = {}
        faltan: dict[str, int] = {}
        for rol, exigidos in regla.exige.items():
            terminos = [t for r, t in observados if r == rol]
            cumplidos[rol] = terminos
            if len(terminos) < exigidos:
                faltan[rol] = exigidos - len(terminos)

        # El umbral se comprueba aparte de la tupla y se informa aparte: son
        # dos razones distintas para no promover, y fundirlas dejaría al
        # clínico sin saber si le falta una prueba o le falta evidencia.
        probabilidad = inferencia.probabilidad_porcentaje / 100.0 if inferencia else None
        # Tres estados y no dos, otra vez. `False` dice que la probabilidad se
        # quedó corta; `None` dice que no hay probabilidad con la que
        # comparar —Bayes no corrió, o el protocolo no declara prevalencia—.
        # Colapsarlos afirmaría que la evidencia falló donde nadie la midió,
        # que es la misma distinción que `SIN_MEDIR` en Φ y `triaje_coincide`
        # a NULL en el tic.
        umbral_cumplido: bool | None = None
        if regla.umbral_postest is not None and probabilidad is not None:
            umbral_cumplido = probabilidad >= regla.umbral_postest

        # No promover por falta de probabilidad es lo conservador, pero el
        # motivo que se informa es «no hay con qué comparar» y no «no llega».
        promueve = not faltan and (
            regla.umbral_postest is None or umbral_cumplido is True
        )
        traza = self._traza(regla, cumplidos, faltan, probabilidad, umbral_cumplido)

        return Veredicto(
            hipotesis=hipotesis,
            promueve=promueve,
            exigido=dict(regla.exige),
            cumplido={rol: len(t) for rol, t in cumplidos.items()},
            terminos=cumplidos,
            faltan=faltan,
            umbral_postest=regla.umbral_postest,
            probabilidad=probabilidad,
            umbral_cumplido=umbral_cumplido,
            fuente=regla.fuente,
            traza=traza,
        )

    # --- Emparejamiento ------------------------------------------------

    @staticmethod
    def _satisfechos(skill: Skill, infones: Sequence[Infon]) -> list[tuple[str, str]]:
        """(rol, término) de cada signo declarado que consta A FAVOR.

        «Positiva» quiere decir la polaridad que sostiene la hipótesis, que
        no siempre es «presente»: un signo con `dispara_si: ausente` se
        satisface constando ausente. Se reutiliza `polaridad_adversa`, que
        ya resuelve esa cuenta para Φ, en vez de rehacerla aquí y arriesgar
        que las dos diverjan.

        Sólo entra evidencia VALIDADA, y un signo cuenta una vez aunque
        varios infones emparejen con él — la misma regla que Φ y el
        veredicto declarado.
        """
        from .bayes import emparejar_termino

        indice = {s.nombre.lower(): s for s in skill.signos if s.efecto == "apoya"}
        salida: list[tuple[str, str]] = []
        vistos: set[str] = set()

        for infon in infones:
            if not infon.es_valido:
                continue
            clave = emparejar_termino(infon.termino, indice)
            if clave is None or clave in vistos:
                continue
            signo: Signo = indice[clave]
            observada = "presente" if infon.polaridad is Polaridad.PRESENTE else "ausente"
            if observada == signo.polaridad_adversa:
                continue  # consta, pero en contra: no satisface la tupla
            vistos.add(clave)
            salida.append((signo.rol, infon.termino))
        return salida

    # --- Lectura -------------------------------------------------------

    @staticmethod
    def _traza(
        regla,
        cumplidos: dict[str, list[str]],
        faltan: dict[str, int],
        probabilidad: float | None,
        umbral_cumplido: bool | None,
    ) -> list[str]:
        traza = []
        for rol, exigidos in regla.exige.items():
            tengo = cumplidos.get(rol, [])
            marca = "✓" if len(tengo) >= exigidos else "·"
            detalle = ", ".join(tengo) if tengo else "nada que lo satisfaga"
            traza.append(f"{marca} {rol}: {len(tengo)}/{exigidos} — {detalle}")

        if faltan:
            que_falta = ", ".join(f"{n} {rol}" for rol, n in faltan.items())
            traza.append(
                f"La tupla no se completa (falta {que_falta}): el hallazgo se "
                f"queda como PROBLEMA, no pasa a diagnóstico"
            )
        if regla.umbral_postest is not None:
            if probabilidad is None:
                traza.append(
                    f"Umbral post-test {regla.umbral_postest:.0%} declarado y sin "
                    f"probabilidad con la que compararlo"
                )
            else:
                marca = "✓" if umbral_cumplido else "·"
                traza.append(
                    f"{marca} post-test {probabilidad:.1%} frente al umbral "
                    f"{regla.umbral_postest:.0%}"
                )
        return traza
