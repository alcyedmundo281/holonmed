"""La duda como dirección: qué la abre, de qué clase es, y hacia dónde va.

`Acoplamiento.duda` existía desde el primer día y **nadie la leía**. El
sistema calculaba que su hipótesis había dejado de funcionar como regla de
acción y seguía adelante sin decirlo. Este módulo es lo que la consume.

LO QUE ESTE MÓDULO NO HACE
--------------------------
No retira la hipótesis. Eso es el veto, y es otra cosa: una exclusión
absoluta dice que el diagnóstico es imposible, y la duda dice que el
argumento dejó de sostenerse con lo que hay. Un veto termina la pregunta;
una duda la reabre.

No decide, no llama al modelo y no toca la probabilidad. Lee números que
las etapas anteriores ya auditaron.

Y no resuelve la duda dentro del tic. No puede: la deducción produce
preguntas o una orden de prueba, y la respuesta llega en otro tic. De modo
que la reapertura es una **salida accionable**, no un recálculo.

LA DUDA TIENE TRES CLASES, Y SE RESUELVEN POR CAMINOS DISTINTOS
--------------------------------------------------------------
Esto es lo que se ganó al partir cos(h,e) en tres. El número fundido dice
que la creencia no funciona; los factores dicen por qué, y cada porqué
manda a un sitio distinto:

* **dirección baja** — lo que se miró **disiente**. No se arregla mirando
  más: cada dato nuevo que confirme lo ya visto la hunde más. Se arregla
  cambiando de hipótesis.

* **cobertura baja** — casi nada de lo que la hipótesis afirma se ha
  puesto a prueba. La hipótesis puede ser excelente y estar sin
  comprobar. **Ésta es la duda que se resuelve indagando**, y
  `Acoplamiento.indagacion` ya calculó por dónde: la dimensión donde la
  hipótesis hace su afirmación más fuerte y nadie ha mirado todavía.

* **explicación baja** — la hipótesis no explica al paciente. Puede ser
  cierta y ser irrelevante, que es el polo que Φ define como Φ = 0:
  argumento internamente ordenado pero aislado. Es la forma que toma el
  sesgo de anclaje, y se resuelve volviendo a la abducción, porque lo que
  falta está fuera de esta hipótesis.

CUÁL DE LOS TRES MANDA
----------------------
`cos = dirección · √cobertura · √explicación`, así que cada factor tira
del producto con `dirección`, `√cobertura` y `√explicación`
respectivamente. Manda el más pequeño: es el que más lastra. La dirección
se compara con su signo y no en valor absoluto — una dirección negativa
significa que el registro contradice, y es la duda más fuerte que hay, de
modo que ser la menor de las tres es exactamente lo que le toca.

Un factor `None` no compite. `None` no es un cero disfrazado: dice que ese
factor no está definido, y un factor indefinido no puede ser la causa de
nada.
"""

import logging
import math

from ..models import Acoplamiento, CausaDeLaDuda, ReaperturaDeIndagacion

logger = logging.getLogger(__name__)

# Qué se le dice al clínico en cada caso. La frase va con el número
# delante para que se pueda impugnar la línea concreta, igual que la traza
# de Φ y la del motor bayesiano.
MOTIVOS: dict[CausaDeLaDuda, str] = {
    CausaDeLaDuda.DIRECCION: (
        "lo que se ha mirado contradice lo que la hipótesis exige; mirar más "
        "no la sostiene"
    ),
    CausaDeLaDuda.COBERTURA: (
        "casi nada de lo que la hipótesis afirma se ha puesto a prueba todavía; "
        "la duda se resuelve indagando"
    ),
    CausaDeLaDuda.EXPLICACION: (
        "la hipótesis deja sin explicar la mayor parte de lo que el paciente "
        "tiene; puede ser cierta y no ser la pregunta"
    ),
}

SIN_CAUSA = (
    "ningún factor está definido: no se ha medido nada con lo que responder "
    "por qué"
)


class ReabridorDeIndagacion:
    """Lee la duda de un acoplamiento y devuelve lo que abre."""

    def reabrir(
        self,
        acoplamiento: Acoplamiento | None,
        ganadora_abductiva: str | None = None,
    ) -> ReaperturaDeIndagacion | None:
        """Devuelve la reapertura, o None si no hay ninguna que abrir.

        `None` cubre dos situaciones que el llamador sí distingue, porque
        tiene el acoplamiento en la mano: que no se pudiera medir Φ, y que
        Φ esté por encima del mínimo. La segunda no es un fallo —es una
        creencia que sigue funcionando— y por eso no se devuelve un objeto
        vacío que habría que interrogar para saber que no pasa nada.
        """
        if acoplamiento is None or not acoplamiento.duda:
            return None

        causa, valor, traza = self._causa(acoplamiento)
        motivo = MOTIVOS[causa] if causa else SIN_CAUSA

        alternativa = None
        if ganadora_abductiva and ganadora_abductiva != acoplamiento.hipotesis:
            alternativa = ganadora_abductiva
            traza.append(
                f"La competencia abductiva prefiere «{ganadora_abductiva}»: la "
                f"vuelta a la abducción ya tiene a dónde ir"
            )

        phi = acoplamiento.phi_legible
        if causa and valor is not None:
            traza.insert(0, f"El factor que más lastra es {causa.value} = {valor:.4f}")
        traza.insert(
            0,
            f"Φ = {phi:.4f}, bajo el acoplamiento mínimo: "
            f"«{acoplamiento.hipotesis}» ha dejado de funcionar como regla "
            f"de acción",
        )

        logger.info(
            "Duda sobre '%s' (Φ=%.4f, %s): la indagación se reabre",
            acoplamiento.hipotesis,
            phi,
            causa.value if causa else "sin causa medible",
        )

        return ReaperturaDeIndagacion(
            hipotesis=acoplamiento.hipotesis,
            phi=round(phi, 4),
            causa=causa,
            motivo=motivo,
            preguntas=list(acoplamiento.indagacion),
            alternativa=alternativa,
            traza=traza,
        )

    @staticmethod
    def _causa(
        acoplamiento: Acoplamiento,
    ) -> tuple[CausaDeLaDuda | None, float | None, list[str]]:
        """Cuál de los tres factores lastra más el producto.

        Se leen los factores de la lectura que este protocolo permite: la
        ponderada, o la categórica cuando no hay ni un likelihood ratio. El
        discriminante es el mismo que usa `phi_legible` y el mismo que usa
        la competencia abductiva para decidir en qué unidad compara.
        """
        ponderada = acoplamiento.cobertura is not None
        if ponderada:
            direccion = acoplamiento.direccion
            cobertura = acoplamiento.cobertura
            explicacion = acoplamiento.explicacion
        else:
            direccion = acoplamiento.direccion_categorica
            cobertura = acoplamiento.cobertura_categorica
            explicacion = acoplamiento.explicacion_categorica

        lectura = "ponderada" if ponderada else "categórica"
        traza = [
            f"Lectura {lectura}: dirección={_fmt(direccion)} "
            f"cobertura={_fmt(cobertura)} explicación={_fmt(explicacion)}"
        ]

        # Cada factor tira del producto con su propia magnitud: la dirección
        # entra tal cual y las otras dos bajo raíz. Se comparan en esa
        # escala, que es la única en la que «cuál lastra más» significa algo.
        tiros: list[tuple[float, CausaDeLaDuda, float]] = []
        if direccion is not None:
            tiros.append((direccion, CausaDeLaDuda.DIRECCION, direccion))
        if cobertura is not None:
            tiros.append((math.sqrt(cobertura), CausaDeLaDuda.COBERTURA, cobertura))
        if explicacion is not None:
            tiros.append(
                (math.sqrt(explicacion), CausaDeLaDuda.EXPLICACION, explicacion)
            )

        if not tiros:
            return None, None, traza

        _, causa, valor = min(tiros, key=lambda t: t[0])
        return causa, valor, traza


def _fmt(valor: float | None) -> str:
    return "n/d" if valor is None else f"{valor:.4f}"
