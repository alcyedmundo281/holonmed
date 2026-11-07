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

LO QUE ESTE MÓDULO HACE CON EL FLUJO (CICLO 12)
-----------------------------------------------
SnNOut y SpPIn no son sólo una compuerta de promoción: dicen qué pedir a
continuación.

    sensible NEGATIVA   descarta ESA hipótesis. No se pide la específica.
                        El paciente sigue con su problema → vuelve a la
                        abducción (`vuelve_a_abduccion = True`).

    sensible POSITIVA   no confirma → propone la específica, por el portón
                        proponer/autorizar, con `solicitante = promocion`.

Una sensible negativa **no cierra la indagación: cierra una línea y abre
otra**. Y ninguna propuesta se convierte en orden sin firma.

LO QUE ESTE MÓDULO NO HACE
--------------------------
No decide el umbral. `umbral_postest` es una **política del servicio**, no un
dato de la enfermedad: dice cuánta certeza se exige antes de actuar, y es
legítimo que sea distinta para un cuadro letal y tratable. Ninguna revista
publica «actúe por encima del 90 %», así que no lleva PMID y por eso el
esquema le exige `motivo` en prosa — el mismo precedente que `sostiene:
mecanismo` en el índice.

No crea órdenes. Devuelve propuestas (`PropuestaPromocion`) que entran por
el portón proponer/autorizar (`a_propuestas_orden`), donde se mantienen como
borrador hasta que una persona nombrada las firma.

Y no llama al LLM. El modelo propone términos; los roles los declara el
índice contra PubMed, y aquí sólo se cuentan.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..models import InferenciaBayesiana, Infon, Polaridad, PropuestaPromocion
from ..models import Promocion as Veredicto

if TYPE_CHECKING:  # pragma: no cover - sólo para tipado
    from ..facturacion.propuesta import OrdenPropuesta
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
        observados, sensibles_negativas = self._clasificar_observados(skill, infones)

        cumplidos: dict[str, list[str]] = {}
        faltan: dict[str, int] = {}
        for rol, exigidos in regla.exige.items():
            terminos = [t for r, t in observados if r == rol]
            cumplidos[rol] = terminos
            if len(terminos) < exigidos:
                faltan[rol] = exigidos - len(terminos)

        # --- LA TUPLA COMO CONTROL DE FLUJO (Ciclo 12) ----------------
        #
        # 1. Sensible NEGATIVA: descarta esta hipótesis (SnNOut). No se pide
        #    la específica —sería pedir una prueba confirmatoria para una
        #    línea que la de descarte ya cerró— y el paciente sigue con su
        #    problema, así que vuelve a la abducción.
        # 2. Sensible POSITIVA (satisfecha en la tupla) y falta la
        #    específica: no confirma por sí sola, así que propone pedir las
        #    pruebas específicas del protocolo que aún no se han medido, con
        #    `solicitante = promocion`.
        vuelve_a_abduccion = bool(sensibles_negativas)
        propuestas: list[PropuestaPromocion] = []
        exige_sensible = regla.exige.get("prueba_sensible", 0)
        sensible_cumplida = (
            exige_sensible > 0
            and len(cumplidos.get("prueba_sensible", [])) >= exige_sensible
        )
        if (
            not vuelve_a_abduccion
            and sensible_cumplida
            and faltan.get("prueba_especifica", 0) > 0
        ):
            propuestas = self._proponer_especificas(
                skill,
                infones,
                hipotesis,
                cumplidos.get("prueba_sensible", []),
            )

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
        # Y una sensible negativa bloquea la promoción aunque otra sensible
        # haya salido positiva: SnNOut ya cerró esta línea.
        promueve = (
            not faltan
            and not vuelve_a_abduccion
            and (regla.umbral_postest is None or umbral_cumplido is True)
        )
        traza = self._traza(
            regla,
            cumplidos,
            faltan,
            probabilidad,
            umbral_cumplido,
            sensibles_negativas,
            propuestas,
        )

        return Veredicto(
            hipotesis=hipotesis,
            promueve=promueve,
            exigido=dict(regla.exige),
            cumplido={rol: len(t) for rol, t in cumplidos.items()},
            terminos=cumplidos,
            faltan=faltan,
            sensible_negativa=sensibles_negativas,
            vuelve_a_abduccion=vuelve_a_abduccion,
            propuestas=propuestas,
            umbral_postest=regla.umbral_postest,
            probabilidad=probabilidad,
            umbral_cumplido=umbral_cumplido,
            fuente=regla.fuente,
            traza=traza,
        )

    # --- Emparejamiento ------------------------------------------------

    @staticmethod
    def _clasificar_observados(
        skill: Skill, infones: Sequence[Infon]
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Separa lo que consta a favor de las pruebas sensibles que constan en contra.

        «Positiva» quiere decir la polaridad que sostiene la hipótesis, que
        no siempre es «presente»: un signo con `dispara_si: ausente` se
        satisface constando ausente. Se reutiliza `polaridad_adversa`, que
        ya resuelve esa cuenta para Φ, en vez de rehacerla aquí y arriesgar
        que las dos diverjan.

        Sólo entra evidencia VALIDADA y no serendípica (`not infon.abre_problema`),
        y un signo cuenta una vez aunque varios infones emparejen con él —
        la misma regla que Φ y el veredicto declarado.
        """
        from .bayes import emparejar_termino

        # Sólo `apoya`: la tupla cuenta lo que el protocolo declara que apoya.
        # `evidencia` pesa en la probabilidad pero no satisface ninguna tupla.
        indice = {s.nombre.lower(): s for s in skill.signos if s.efecto == "apoya"}
        satisfechos: list[tuple[str, str]] = []
        sensibles_negativas: list[str] = []
        vistos_favor: set[str] = set()
        vistos_contra: set[str] = set()

        for infon in infones:
            if not infon.es_valido or infon.abre_problema:
                continue
            clave = emparejar_termino(infon.termino, indice)
            if clave is None:
                continue
            signo: Signo = indice[clave]
            observada = "presente" if infon.polaridad is Polaridad.PRESENTE else "ausente"
            if observada == signo.polaridad_adversa:
                if signo.rol == "prueba_sensible" and clave not in vistos_contra:
                    vistos_contra.add(clave)
                    sensibles_negativas.append(infon.termino)
                continue  # consta, pero en contra: no satisface la tupla
            if clave not in vistos_favor:
                vistos_favor.add(clave)
                satisfechos.append((signo.rol, infon.termino))
        return satisfechos, sensibles_negativas

    @classmethod
    def _satisfechos(
        cls, skill: Skill, infones: Sequence[Infon]
    ) -> list[tuple[str, str]]:
        """Compatibilidad directa: devuelve sólo los pares (rol, término) a favor."""
        satisfechos, _ = cls._clasificar_observados(skill, infones)
        return satisfechos

    @staticmethod
    def _proponer_especificas(
        skill: Skill,
        infones: Sequence[Infon],
        hipotesis: str,
        sensibles_positivas: list[str],
    ) -> list[PropuestaPromocion]:
        """Propone las pruebas específicas declaradas que aún no se han medido.

        Nace cuando la prueba sensible salió positiva y falta la específica.
        No propone una prueba que ya conste en el registro (ni a favor ni en
        contra): pedir lo que ya se hizo es el error que `VALIDACION.md`
        denuncia.
        """
        from .bayes import emparejar_termino

        especificas = [
            s
            for s in skill.signos
            if s.efecto == "apoya" and s.rol == "prueba_especifica"
        ]
        if not especificas:
            return []

        indice_esp = {s.nombre.lower(): s for s in especificas}
        ya_medidas: set[str] = set()
        for infon in infones:
            if not infon.es_valido or infon.abre_problema:
                continue
            clave = emparejar_termino(infon.termino, indice_esp)
            if clave is not None:
                ya_medidas.add(clave)

        apoyo_sensible = ", ".join(sensibles_positivas)
        motivo = (
            f"Prueba sensible positiva ({apoyo_sensible}) para «{hipotesis}»: "
            "no confirma por sí sola; se propone la prueba específica (SpPIn) "
            "para completar la tupla de promoción."
        )

        propuestas: list[PropuestaPromocion] = []
        for signo in especificas:
            if signo.nombre.lower() in ya_medidas:
                continue
            pref = signo.codigo_preferido()
            sistema, codigo = pref if pref else (None, None)
            propuestas.append(
                PropuestaPromocion(
                    termino=signo.nombre,
                    codigo=codigo,
                    sistema=sistema,
                    rol="prueba_especifica",
                    solicitante="promocion",
                    motivo=motivo,
                )
            )
        return propuestas

    # --- Lectura -------------------------------------------------------

    @staticmethod
    def _traza(
        regla,
        cumplidos: dict[str, list[str]],
        faltan: dict[str, int],
        probabilidad: float | None,
        umbral_cumplido: bool | None,
        sensibles_negativas: list[str] | None = None,
        propuestas: list[PropuestaPromocion] | None = None,
    ) -> list[str]:
        traza = []
        for rol, exigidos in regla.exige.items():
            tengo = cumplidos.get(rol, [])
            marca = "✓" if len(tengo) >= exigidos else "·"
            detalle = ", ".join(tengo) if tengo else "nada que lo satisfaga"
            traza.append(f"{marca} {rol}: {len(tengo)}/{exigidos} — {detalle}")

        if sensibles_negativas:
            quienes = ", ".join(sensibles_negativas)
            traza.append(
                f"Prueba sensible NEGATIVA ({quienes}): descarta esta línea "
                "(SnNOut). No se pide la prueba específica; el paciente sigue "
                "con su problema y vuelve a la abducción."
            )
        elif faltan:
            que_falta = ", ".join(f"{n} {rol}" for rol, n in faltan.items())
            traza.append(
                f"La tupla no se completa (falta {que_falta}): el hallazgo se "
                f"queda como PROBLEMA, no pasa a diagnóstico"
            )
            if propuestas:
                nombres = ", ".join(p.termino for p in propuestas)
                traza.append(
                    f"Sensible positiva sin específica: se propone pedir "
                    f"{nombres} (solicitante = promocion)"
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


def a_propuestas_orden(veredicto: Veredicto | None) -> list[OrdenPropuesta]:
    """Pasa las propuestas de la tupla al portón proponer/autorizar.

    No crea ninguna orden ni toca la base de datos: devuelve borradores
    `OrdenPropuesta` con `solicitante = Solicitante.PROMOCION` y su `motivo`.
    Sólo cuando un humano llama a `a_orden(..., prescriptor=...)` y lo guarda
    existe una orden real.
    """
    from ..facturacion.modelos import Solicitante
    from ..facturacion.propuesta import OrdenPropuesta

    if veredicto is None or not veredicto.propuestas:
        return []

    return [
        OrdenPropuesta(
            termino=p.termino,
            codigo=p.codigo,
            sistema=p.sistema,
            reconocida=bool(p.codigo),
            solicitante=Solicitante.PROMOCION,
            motivo=p.motivo,
        )
        for p in veredicto.propuestas
    ]
