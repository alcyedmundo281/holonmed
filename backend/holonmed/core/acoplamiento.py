"""Coeficiente de Acoplamiento (Φ): la validación semiótica del diagnóstico.

El motor bayesiano responde *cuánta* evidencia sostiene una hipótesis. No
responde una segunda pregunta, que es la que un clínico experimentado se
hace de forma tácita: **¿esta hipótesis está acoplada a este paciente?**

Dos historias pueden arrojar la misma probabilidad posterior y ser cosas
muy distintas. En una, todos los hallazgos apuntan al mismo sitio con
fuerza moderada. En la otra, una única prueba muy específica arrastra la
probabilidad mientras el resto del registro dice otra cosa y media
historia queda sin explicar. Bayes no las distingue porque suma. Este
módulo las distingue porque mide dirección.

FUNDAMENTO
----------
Una creencia no es una imagen del mundo sino una **regla de acción**: creer
que este paciente tiene una pancreatitis es estar dispuesto a actuar —
pedir, ingresar, hidratar, no operar — como se actúa ante una pancreatitis.
Una creencia es verdadera cuando esa regla se acopla al contexto sin
fricción; es falsa cuando produce **duda**, esa incomodidad que aparece
cuando el mundo no responde como la regla anticipaba, y que es justamente
lo que reabre la indagación.

La armonía con el contexto no es aquí un estado místico ni una impresión
subjetiva. Es una cantidad geométrica.

LA FÓRMULA VECTORIAL
--------------------
En el espacio de los hallazgos, el peso natural de cada dimensión es el
**peso de evidencia**, ln(LR): es aditivo, tiene signo, y es exactamente
la moneda en la que razona Bayes.

Se construyen dos vectores sobre las mismas dimensiones:

* **h** — el *caso de libro*: lo que la hipótesis exige del mundo si es
  cierta. Cada signo declarado por el protocolo, con peso ln(LR+).
* **e** — el *caso real*: lo que el registro de este paciente afirma de
  hecho. Un hallazgo validado y presente aporta ln(LR+); una ausencia
  documentada aporta ln(LR−), que es negativo; lo que nadie ha mirado
  aporta 0, porque el silencio no es evidencia.

                        h · e
        cos(h, e) = ─────────────      ∈ [−1, +1]
                      ‖h‖ · ‖e‖

Y esa es toda la métrica. Nótese la relación con el motor bayesiano:

        Σ eᵢ  =  ln(odds posterior / odds previo)

es decir, **Bayes lee la magnitud del mismo vector y Φ lee su dirección**.
No son dos modelos compitiendo: son dos proyecciones de un único objeto.
Por eso Φ puede añadir información sin contradecir la probabilidad, y por
eso jamás debe modificarla.

La identidad es exacta, pero no es incondicional, y conviene decir dónde
termina antes de que alguien la dé por universal:

1. **La suma corre sobre las dimensiones declaradas, no sobre el vector
   completo.** El resto no simbolizado entra con un peso que es una
   convención de este módulo (sección siguiente) y con el que Bayes nunca
   operó. `Acoplamiento.peso_evidencia_declarado` es la suma que sí iguala
   el delta bayesiano, y excluye el residuo de forma explícita.
2. **Ambos motores tienen que recibir el mismo conjunto de infones.** El
   pipeline no lo hace a propósito: Bayes recibe el tic de hoy y Φ recibe
   además la línea de tiempo del holón, porque medir el acoplamiento contra
   medio paciente no mediría nada. Con historial previo, la identidad deja
   de valer numéricamente aunque la relación conceptual se mantenga.
3. **A lo sumo un infón validado por dimensión.** Si dos infones
   emparejan con el mismo signo, Bayes multiplica su LR dos veces y este
   módulo lo cuenta una. Aquí la discrepancia no favorece a Bayes: contar
   dos veces la misma prueba es doble contabilidad de la evidencia. Se
   deja como está porque corregirlo es cambiar el motor bayesiano, no
   medir el acoplamiento.

Las tres condiciones están fijadas como tests, incluida la divergencia,
para que un cambio futuro en la escala del residuo falle ruidosamente en
vez de erosionar la identidad en silencio.

Los tres polos salen de la geometría, sin necesidad de postularlos:

* **Φ = +1** — armonía. El registro dice exactamente lo que la hipótesis
  exige. El símbolo simboliza correctamente la realidad física del
  paciente.
* **Φ = 0** — inercia. Los vectores son ortogonales: la hipótesis conserva
  todo su orden interno pero no toca este caso. Ni contribuye ni daña, es
  irrelevante para la evolución del paciente.
* **Φ = −1** — desarmonía. La hipótesis mantiene su orden interno y aun así
  el contexto la contradice punto por punto. El análisis se vuelve caos.

EL RESTO NO SIMBOLIZADO
-----------------------
Un hallazgo validado que el protocolo no contempla se añade como una
dimensión propia, donde h es 0 y e no. Es ortogonal por construcción, así
que **baja el coseno sin ningún castigo ad hoc**: una hipótesis que deja
media historia sin explicar se desacopla sola. Eso es lo que quiere decir
que un signo debe representar a su objeto — un diagnóstico que no
simboliza lo que el paciente tiene es un símbolo incompleto.

Sólo cuentan como resto los hallazgos **presentes**. Una ausencia
documentada ajena al protocolo (una fiebre que no hay) no es fricción: es
un clínico haciendo bien su trabajo, y penalizarla sería absurdo.

Parsimonia y diversidad quedan definidas sobre esta misma cantidad, aunque
su cálculo pertenece a la siguiente fase: una segunda hipótesis se
justifica exactamente cuando **añadirla sube Φ del conjunto** — cuando
crea orden y significado. Si lo baja, es proliferación, y la parsimonia
gana. El criterio no lo pone el gusto: lo pone la aritmética.

LA GUARDA ANTI-PSEUDOCIENCIA (α)
--------------------------------
Un argumento puede ser internamente perfecto y no tocar la realidad. La
homeopatía tiene coherencia interna; su coseno consigo misma vale 1. Sin
una guarda, la elaboración se confundiría con la verdad.

Por eso el coseno se multiplica por un **coeficiente de anclaje** α ∈ [0,1],
media *geométrica* de tres factores — geométrica y no aritmética porque el
fallo de uno solo debe bastar para colapsar el resultado:

* la confianza media de los infones que sostienen el vector (¿está la
  evidencia auditada, o solamente es plausible?);
* la procedencia de la normalización (¿código revisado por un humano, o
  coincidencia difusa?);
* **la fuente de los likelihood ratios en uso**. Un LR sin procedencia es
  un número inventado con formato científico.

Un argumento cuyos LR no citan fuente obtiene α = 0 y por tanto Φ = 0:
no se le declara falso, se le declara *irrelevante*, que es precisamente
el polo cero. La elaboración sin anclaje no compra armonía.

LO QUE ESTE MÓDULO NO HACE
--------------------------
No llama al LLM. Φ se calcula con aritmética determinista sobre artefactos
que el sistema ya produjo y que ya fueron auditados; meter aquí un juicio
del modelo sería fundar la validación semiótica en la misma fluidez que la
validación existe para contener.

Y no toca la probabilidad. Φ es un eje independiente. Lo que se le entrega
al clínico es el par (P, Φ), y el cuadrante interesante — el que ningún
sistema de apoyo suele mostrar — es **P alta con Φ baja**: certeza
construida sobre un dato fuerte mientras el resto del paciente disiente.
Eso tiene nombre en la literatura de error diagnóstico y se llama sesgo de
anclaje.
"""

import logging
import math
from collections.abc import Sequence
from statistics import median
from typing import TYPE_CHECKING, Any

from ..models import (
    Acoplamiento,
    ComponenteAcoplamiento,
    EstadoDimension,
    InferenciaBayesiana,
    Infon,
    Polaridad,
    VeredictoSemiotico,
)

if TYPE_CHECKING:  # pragma: no cover - sólo para tipado
    from .skills import Skill

logger = logging.getLogger(__name__)


# --- Umbrales de lectura ---------------------------------------------
# Las bandas son convenciones de presentación, no parte de la métrica: Φ
# es continuo y la traza siempre acompaña al número. Se declaran aquí para
# que un centro pueda moverlas sin tocar el cálculo.
UMBRAL_ARMONIA = 0.60
UMBRAL_ACOPLAMIENTO = 0.20
UMBRAL_DESARMONIA = -0.60
UMBRAL_FRICCION = -0.20

# Probabilidad a partir de la cual una hipótesis se considera "sostenida"
# para efectos de la lectura por cuadrantes. Coincide con el corte de
# `InferenciaBayesiana.veredicto`, y no es casual: el cuadrante es la
# lectura conjunta de las dos métricas y debe hablar el mismo idioma.
UMBRAL_PROBABILIDAD = 50.0

# Calidad atribuida a cada método de normalización del validador. Un
# código que revisó un humano en el protocolo no vale lo mismo que una
# coincidencia difusa que superó el umbral por poco.
CALIDAD_METODO: dict[str, float] = {
    "hint_exacto": 1.00,
    "exacto": 1.00,
    "hint_difuso": 0.90,
    "rerank_llm": 0.90,
    "fuzzy": 0.60,
}
CALIDAD_METODO_DESCONOCIDO = 0.70


class MedidorDeAcoplamiento:
    """Calcula Φ entre una hipótesis diagnóstica y el contexto del paciente.

    Es intencionadamente una clase pequeña y sin estado, igual que
    `AntigenPresentingCell`: recibe el protocolo activo y los infones del
    tic, y devuelve un número con su traza completa. Nada persiste aquí.
    """

    def medir(
        self,
        skill: "Skill",
        infones: Sequence[Infon],
        inferencia: InferenciaBayesiana | None = None,
    ) -> Acoplamiento | None:
        """Devuelve el acoplamiento, o None si el protocolo no permite medirlo.

        Se devuelve None —y no un Φ de 0— cuando el protocolo no declara
        ningún likelihood ratio. Son situaciones distintas: un Φ de 0 dice
        que la hipótesis no toca al paciente; None dice que no hay con qué
        preguntarlo. Confundirlas sería inventar una medida.
        """
        dimensiones = self._dimensiones_declaradas(skill)
        # El protocolo puede no declarar un solo likelihood ratio y aun así
        # ser medible: es el caso de casi todos los criterios publicados,
        # que declaran categorías. Salir aquí dejaba `phi_categorico`
        # inalcanzable **justo para los protocolos que lo motivaron**.
        categoricas = [s for s in skill.signos if s.efecto != "excluye"]
        if not dimensiones and not categoricas:
            logger.debug(
                "El protocolo '%s' no declara ni LR ni signos: no hay espacio "
                "donde medir Φ",
                skill.nombre,
            )
            return None

        observaciones = self._observar(dimensiones, infones)
        residuo = self._resto_no_simbolizado(skill, dimensiones, infones)

        componentes = self._componer(dimensiones, observaciones)
        peso_tipico = self._peso_del_resto(componentes, dimensiones)
        componentes.extend(self._componer_residuo(residuo, peso_tipico))

        coseno, traza_geom = self._coseno(componentes)
        direccion, cobertura, explicacion, traza_fact = self._factores(componentes)
        phi_cat, dims_cat, traza_cat = self._categorico(skill, infones, len(residuo))
        dir_cat, cob_cat, expl_cat, traza_fact_cat = self._factores_categoricos(
            skill, infones, len(residuo)
        )
        if not dimensiones:
            traza_geom.append(
                "El protocolo no declara ningún LR: la lectura ponderada no "
                "aplica y las bandas se leen del Φ categórico."
            )
        anclaje, detalle_anclaje, traza_anc = self._anclaje(
            dimensiones, observaciones, residuo, skill, infones
        )

        phi = max(-1.0, min(1.0, coseno * anclaje))
        # Cuando no hay LR declarados, `phi` vale 0 porque no hay vector que
        # proyectar — y 0 se leería como INERCIA, que es una afirmación
        # falsa sobre el caso. La banda se lee entonces del categórico, que
        # es la única lectura disponible.
        phi_para_bandas = phi
        if not dimensiones and phi_cat is not None:
            phi_para_bandas = max(-1.0, min(1.0, phi_cat * anclaje))

        return Acoplamiento(
            phi=round(phi, 4),
            coseno=round(coseno, 4),
            phi_categorico=(
                None
                if phi_cat is None
                else round(max(-1.0, min(1.0, phi_cat * anclaje)), 4)
            ),
            coseno_categorico=None if phi_cat is None else round(phi_cat, 4),
            dimensiones_categoricas=dims_cat,
            direccion_categorica=None if dir_cat is None else round(dir_cat, 4),
            cobertura_categorica=None if cob_cat is None else round(cob_cat, 4),
            explicacion_categorica=None if expl_cat is None else round(expl_cat, 4),
            direccion=None if direccion is None else round(direccion, 4),
            cobertura=None if cobertura is None else round(cobertura, 4),
            explicacion=None if explicacion is None else round(explicacion, 4),
            anclaje=round(anclaje, 4),
            hipotesis=skill.condicion.get("nombre") or skill.titulo,
            veredicto=self._veredicto(phi_para_bandas, componentes),
            cuadrante=self._cuadrante(phi_para_bandas, inferencia),
            componentes=componentes,
            resto_no_simbolizado=[i.termino for i in residuo],
            indagacion=self._indagacion(componentes),
            anclaje_detalle=detalle_anclaje,
            traza=traza_geom + traza_fact + traza_anc + traza_cat + traza_fact_cat,
        )

    # --- El vector categórico -----------------------------------------

    @staticmethod
    def _categorico(
        skill: "Skill", infones: Sequence[Infon], resto: int = 0
    ) -> tuple[float | None, int, list[str]]:
        """Φ sobre TODOS los signos declarados, con peso ±1 en vez de ln(LR).

        La lectura ponderada de arriba sólo puede usar los signos con
        likelihood ratio publicado, y ésos son una minoría: los criterios
        que la clínica usa a diario —MDS, Atlanta, Duke, ACR/EULAR—
        declaran categorías, no cocientes. Sin esta lectura, Φ devolvería
        `None` para casi todos ellos.

        Cada dimensión pregunta lo mismo, y por eso el caso de libro es el
        vector de unos: **¿el registro confirma lo que la hipótesis
        espera?** La hipótesis espera que sus apoyos estén y que sus
        banderas rojas no. De ahí:

            hᵢ = +1  en toda dimensión declarada
            eᵢ = +1  el registro confirma la expectativa
                 −1  la contradice
                  0  nadie lo ha mirado

        Y el resto no simbolizado —los `r` hallazgos validados y presentes
        que ninguna dimensión declarada explica— son dimensiones ortogonales
        con hᵢ = 0 y eᵢ = ±1: no tocan el numerador, sólo ‖e‖.

                          Σ eᵢ
            Φ_cat = ─────────────────────      ∈ [−1, +1]
                    √(D · (medidos + r))

        que es el coseno de esos dos vectores, escrito sin cancelar.

        LOS POLOS, Y LA CONDICIÓN QUE LOS GOBIERNA
        Todo confirma da +1 **cuando la hipótesis explica todo el registro**;
        todo contradice da −1 en la misma condición, y mitad y mitad da 0.
        Con resto sin explicar el polo positivo es **inalcanzable**, y eso no
        es una limitación: es el punto. Sin el término `r`, un protocolo que
        declara dos signos y los dos constan daba armonía perfecta en un
        paciente con seis hallazgos que no explicaba — el polo que Φ define
        como cero, «internamente ordenado pero aislado», informado como +1.

        El término es el mismo factor de explicación de la lectura ponderada
        con pesos unitarios: `m/(m+r)` es ‖e_S‖²/‖e‖² cuando cada dimensión
        pesa 1. Y `m` y `r` no cuentan nunca el mismo infón, porque
        `_resto_no_simbolizado` salta los que emparejan con un signo
        declarado.

        Las exclusiones absolutas **no son dimensiones**: no restan, vetan,
        y para cuando esto se calcula la hipótesis ya se habrá retirado.

        El peso ±1 tiene un coste que conviene no perder de vista: un signo
        que nadie midió pesa aquí lo mismo que uno con LR de 26.6 y su
        intervalo de confianza. Lo único que separa una tabla útil de una
        lista de corazonadas con formato es la curación contra evidencia
        del índice. Cuando no hay cociente que pondere, **la disciplina de
        curación es la ponderación**.
        """
        dimensiones, contribuciones = MedidorDeAcoplamiento._contribuciones_categoricas(
            skill, infones
        )
        if not dimensiones:
            return None, 0, []

        medidos = len(contribuciones)
        if not medidos:
            return (
                0.0,
                len(dimensiones),
                ["Φ categórico = 0: ningún signo declarado consta en el registro"],
            )

        suma = sum(contribuciones.values())
        phi = suma / math.sqrt(len(dimensiones) * (medidos + resto))
        favor = sum(1 for v in contribuciones.values() if v > 0)
        traza = [
            f"Φ categórico: {favor} a favor, {medidos - favor} en contra, "
            f"sobre {len(dimensiones)} dimensiones declaradas",
            f"Φ_cat = {suma} / √({len(dimensiones)} × ({medidos} + {resto})) = {phi:.4f}",
        ]
        return phi, len(dimensiones), traza

    @staticmethod
    def _contribuciones_categoricas(
        skill: "Skill", infones: Sequence[Infon]
    ) -> tuple[list[Any], dict[str, int]]:
        """Las dimensiones categóricas y lo que el registro dice de cada una.

        Vive aparte porque la usan dos lectores —el Φ categórico y sus
        factores— y **tienen que emparejar igual**. Si cada uno recorriera
        los infones por su cuenta, los factores podrían describir una
        medición distinta de la que produjo el número, y la identidad
        cerraría o no según el caso. Es el mismo motivo por el que
        `emparejar_termino` es una sola función compartida con Bayes.
        """
        from .bayes import emparejar_termino

        dimensiones = [s for s in skill.signos if s.efecto != "excluye"]
        if not dimensiones:
            return [], {}

        indice = {s.nombre.lower(): s for s in dimensiones}
        contribuciones: dict[str, int] = {}

        for infon in infones:
            if not infon.es_valido:
                continue
            clave = emparejar_termino(infon.termino, indice)
            if clave is None or clave in contribuciones:
                continue
            signo = indice[clave]
            observada = "presente" if infon.polaridad is Polaridad.PRESENTE else "ausente"
            contribuciones[clave] = -1 if observada == signo.polaridad_adversa else 1

        return dimensiones, contribuciones

    @staticmethod
    def _factores_categoricos(
        skill: "Skill", infones: Sequence[Infon], resto: int = 0
    ) -> tuple[float | None, float | None, float | None, list[str]]:
        """Los mismos tres factores, sobre la lectura de pesos unitarios.

        La descomposición de `_factores` no es propia de la lectura
        ponderada: es lo que hace cualquier coseno. La categórica **es la
        ponderada con todos los pesos iguales**, y como el coseno es
        invariante de escala, la escala se cancela y las dos leen en la
        misma unidad. Medido en `guiones/misma_escala.py`: cinco signos y
        uno presente dan 0.4472 tanto declarando `lr: 2.0` en los cinco
        como no declarando ninguno.

        Con `h` el vector de unos, cada término se simplifica:

            dirección   = Σeᵢ / m        de lo mirado, cuánto concuerda
            cobertura   = m / D          de lo declarado, cuánto se miró
            explicación = m / (m + r)    del registro, cuánto cae dentro

        y su producto reconstruye `Σeᵢ / √(D·(m+r))`, que es el Φ
        categórico **antes de α** — es decir el término homólogo de
        `coseno`, y el único que sirve para ordenar candidatas. Ordenar por
        `phi_categorico` sería ordenar por la calidad documental del
        protocolo, que es lo que α mide.

        El criterio de `None` es el de `_factores`, dimensión por
        dimensión: sin nada mirado no hay dirección que dar, y sin ninguna
        dimensión declarada no hay ni cobertura ni explicación. Cero diría
        que el factor vale cero, que es otra afirmación.
        """
        dimensiones, contribuciones = MedidorDeAcoplamiento._contribuciones_categoricas(
            skill, infones
        )
        total = len(dimensiones)
        if not total:
            return None, None, None, []

        medidos = len(contribuciones)
        direccion = sum(contribuciones.values()) / medidos if medidos else None
        cobertura = medidos / total
        explicacion = medidos / (medidos + resto) if medidos + resto else None

        traza: list[str] = []
        if direccion is not None:
            traza.append(
                f"dirección categórica = {sum(contribuciones.values())}/{medidos} "
                f"= {direccion:.4f}"
            )
        traza.append(f"cobertura categórica = {medidos}/{total} = {cobertura:.2%}")
        if explicacion is not None:
            traza.append(
                f"explicación categórica = {medidos}/({medidos} + {resto}) "
                f"= {explicacion:.2%}"
            )
        return direccion, cobertura, explicacion, traza

    # --- Construcción del espacio ------------------------------------

    @staticmethod
    def _dimensiones_declaradas(skill: "Skill") -> list[dict[str, Any]]:
        """Una dimensión por cada signo del protocolo que declara un LR.

        `h` es lo que el caso de libro exigiría: el signo presente, con su
        peso de evidencia ln(LR+). Cuando un signo sólo declara LR− —caso
        legítimo: hay pruebas cuya única información útil es su
        negatividad— se usa −ln(LR−), que es positivo y tiene la magnitud
        del poder discriminante de esa prueba. Es una lectura conservadora:
        dice que el caso de libro la tendría presente, sin pronunciarse
        sobre con cuánta fuerza confirma.
        """
        dimensiones: list[dict[str, Any]] = []
        for signo in skill.signos:
            lr_mas = _positivo(signo.lr)
            lr_menos = _positivo(signo.lr_negativo)
            if lr_mas is None and lr_menos is None:
                continue

            if lr_mas is not None and lr_mas != 1.0:
                h = math.log(lr_mas)
            elif lr_menos is not None and lr_menos != 1.0:
                h = -math.log(lr_menos)
            else:
                continue  # LR de 1.0: el signo no discrimina nada.

            dimensiones.append(
                {
                    "nombre": signo.nombre,
                    "clave": signo.nombre.lower(),
                    "rol": signo.rol,
                    "lr_mas": lr_mas,
                    "lr_menos": lr_menos,
                    "fuente": bool((signo.fuente or "").strip()),
                    "h": h,
                }
            )
        return dimensiones

    @staticmethod
    def _peso_del_resto(
        componentes: Sequence["ComponenteAcoplamiento"],
        dimensiones: list[dict[str, Any]],
    ) -> float:
        """Cuánto pesa un hallazgo que la hipótesis no explica.

        No hay forma de conocer el LR de un hallazgo que el protocolo no
        contempla: si lo hubiera, estaría contemplado. Hay que elegir una
        escala, y la elección tiene consecuencias clínicas grandes.

        Se le asigna la **media cuadrática del peso de evidencia que este
        mismo caso sí explicó**. La regla queda así: por cada hallazgo que
        la hipótesis explica con un peso w, un hallazgo que no explica le
        cuesta otro tanto. Es una escala relativa al caso y no al
        protocolo, y esa diferencia importa: anclarla al protocolo hacía
        que una prueba de LR enorme comprara armonía casi ilimitada, de
        modo que acertar el laboratorio estelar bastaba para tapar media
        historia sin explicar. Es exactamente el error que Φ debe delatar,
        no cometer.

        Cuando la hipótesis no explicó nada en absoluto no hay caso al que
        referirse, y se recurre a la mediana del poder discriminante que el
        protocolo declara. La mediana y no la media, para que un LR extremo
        no arrastre la escala.
        """
        observados = [abs(c.observado) for c in componentes if c.observado]
        if observados:
            return math.sqrt(sum(v**2 for v in observados) / len(observados))
        pesos = [abs(d["h"]) for d in dimensiones if d["h"]]
        return median(pesos) if pesos else 0.0

    @staticmethod
    def _observar(
        dimensiones: list[dict[str, Any]], infones: Sequence[Infon]
    ) -> dict[str, Infon]:
        """Empareja cada dimensión con el infón validado que la informa.

        Se reutiliza el mismo emparejamiento por subcadena que usa el motor
        bayesiano. Es deliberado: si los dos módulos emparejaran distinto,
        la identidad Σeᵢ = ln(odds posterior / odds previo) dejaría de
        cumplirse y Φ ya no estaría leyendo el mismo vector que Bayes.
        """
        from .bayes import emparejar_termino

        indice = {d["clave"]: d for d in dimensiones}
        elegidos: dict[str, Infon] = {}

        for infon in infones:
            if not infon.es_valido:
                continue  # Sólo evidencia auditada entra en el vector.
            clave = emparejar_termino(infon.termino, indice)
            if clave is None:
                continue

            previo = elegidos.get(clave)
            if previo is None:
                elegidos[clave] = infon
                continue

            # Dos infones sobre el mismo signo. Si se contradicen, manda el
            # más reciente: una lipasa normal hoy no queda anulada por una
            # lipasa alta de la semana pasada, aunque aquella se midiera con
            # más confianza. Si concuerdan, manda el de mejor confianza.
            if previo.polaridad is not infon.polaridad:
                logger.info(
                    "Registro contradictorio sobre '%s': %s vs %s; manda el reciente",
                    clave,
                    previo.polaridad.value,
                    infon.polaridad.value,
                )
                if infon.timestamp > previo.timestamp:
                    elegidos[clave] = infon
            elif infon.confianza > previo.confianza:
                elegidos[clave] = infon

        return elegidos

    @staticmethod
    def _resto_no_simbolizado(
        skill: "Skill",
        dimensiones: list[dict[str, Any]],
        infones: Sequence[Infon],
    ) -> list[Infon]:
        """Hallazgos validados y presentes que la hipótesis no explica.

        Se excluyen los infones derivados —el trastorno que acuña el
        clasificador es la hipótesis misma, no un resto— y el propio
        nombre de la condición, para que el diagnóstico no figure como
        evidencia contra sí mismo.
        """
        from .bayes import emparejar_termino

        # Se indexan TODOS los signos declarados y no sólo los que llevan
        # likelihood ratio: un signo declarado categóricamente está
        # contemplado por el protocolo, y contarlo como resto diría que la
        # hipótesis no lo explica cuando sí lo declara.
        indice = {s.nombre.lower(): s for s in skill.signos}
        condicion = str(skill.condicion.get("nombre") or skill.titulo).lower()

        # El mismo hallazgo puede llegar dos veces —una desde la línea de
        # tiempo del holón y otra desde el tic de hoy— y un resto duplicado
        # abriría dos dimensiones ortogonales por un solo hecho, castigando
        # Φ el doble por la misma cosa.
        resto: dict[str, Infon] = {}
        for infon in infones:
            if infon.polaridad is not Polaridad.PRESENTE or not infon.es_valido:
                continue
            if infon.derivado_de:
                continue
            termino = infon.termino.lower()
            if termino in condicion or condicion in termino:
                continue
            if emparejar_termino(infon.termino, indice) is not None:
                continue
            previo = resto.get(termino)
            if previo is None or infon.confianza > previo.confianza:
                resto[termino] = infon
        return list(resto.values())

    # --- Vectores -----------------------------------------------------

    @staticmethod
    def _componer(
        dimensiones: list[dict[str, Any]], observaciones: dict[str, Infon]
    ) -> list[ComponenteAcoplamiento]:
        """Traduce cada dimensión declarada a su par (h, e)."""
        componentes: list[ComponenteAcoplamiento] = []

        for dim in dimensiones:
            infon = observaciones.get(dim["clave"])
            h = float(dim["h"])

            if infon is None:
                # Nadie lo ha mirado. No es una ausencia: es un vacío, y
                # aporta 0 al vector observado. Sube ‖h‖ sin subir h·e, de
                # modo que un caso a medio estudiar da armonía parcial —
                # que es exactamente lo que es.
                componentes.append(
                    ComponenteAcoplamiento(
                        dimension=dim["nombre"],
                        rol=dim["rol"],
                        esperado=round(h, 4),
                        observado=0.0,
                        estado=EstadoDimension.SIN_MEDIR,
                        detalle="sin dato en el registro",
                    )
                )
                continue

            if infon.polaridad is Polaridad.AUSENTE:
                lr = dim["lr_menos"]
                if lr is None or lr == 1.0:
                    e = 0.0
                    detalle = "ausencia documentada, sin LR− declarado"
                    estado = EstadoDimension.SIN_MEDIR
                else:
                    e = math.log(lr)
                    detalle = f"ausente, LR− {lr}"
                    estado = (
                        EstadoDimension.CONTRADICE
                        if e * h < 0
                        else EstadoDimension.CONCUERDA
                    )
            else:
                lr = dim["lr_mas"]
                if lr is None or lr == 1.0:
                    e = 0.0
                    detalle = "presente, sin LR+ declarado"
                    estado = EstadoDimension.SIN_MEDIR
                else:
                    e = math.log(lr)
                    detalle = f"presente, LR+ {lr}"
                    estado = (
                        EstadoDimension.CONTRADICE
                        if e * h < 0
                        else EstadoDimension.CONCUERDA
                    )

            componentes.append(
                ComponenteAcoplamiento(
                    dimension=dim["nombre"],
                    rol=dim["rol"],
                    esperado=round(h, 4),
                    observado=round(e, 4),
                    estado=estado,
                    detalle=detalle,
                    infon=infon.termino,
                    confianza=infon.confianza,
                )
            )

        return componentes

    @staticmethod
    def _componer_residuo(
        resto: Sequence[Infon], peso: float
    ) -> list[ComponenteAcoplamiento]:
        """Cada hallazgo no explicado abre una dimensión ortogonal."""
        return [
            ComponenteAcoplamiento(
                dimension=infon.termino,
                rol="no_contemplado",
                esperado=0.0,
                observado=round(peso, 4),
                estado=EstadoDimension.NO_SIMBOLIZADO,
                detalle="hallazgo validado que el protocolo no explica",
                infon=infon.termino,
                confianza=infon.confianza,
            )
            for infon in resto
        ]

    @staticmethod
    def _coseno(
        componentes: Sequence[ComponenteAcoplamiento],
    ) -> tuple[float, list[str]]:
        """El coseno del ángulo entre el caso de libro y el caso real."""
        producto = sum(c.esperado * c.observado for c in componentes)
        norma_h = math.sqrt(sum(c.esperado**2 for c in componentes))
        norma_e = math.sqrt(sum(c.observado**2 for c in componentes))

        traza = [
            f"Dimensiones del espacio: {len(componentes)}",
            f"‖h‖ (caso de libro) = {norma_h:.3f}",
            f"‖e‖ (caso real) = {norma_e:.3f}",
            f"h·e = {producto:.3f}",
        ]

        if norma_h == 0 or norma_e == 0:
            traza.append(
                "Vector observado nulo: no hay evidencia validada que acople "
                "con este protocolo. Φ = 0 por inercia, no por contradicción."
            )
            return 0.0, traza

        coseno = producto / (norma_h * norma_e)
        # El error de coma flotante puede sacar el coseno del intervalo por
        # unas milmillonésimas; se recorta antes de que llegue a una banda.
        coseno = max(-1.0, min(1.0, coseno))
        traza.append(
            f"cos(h,e) = {producto:.3f} / ({norma_h:.3f} × {norma_e:.3f}) = {coseno:.4f}"
        )
        return coseno, traza

    @staticmethod
    def _factores(
        componentes: Sequence[ComponenteAcoplamiento],
    ) -> tuple[float | None, float | None, float | None, list[str]]:
        """Parte el coseno en sus tres factores. No calcula nada nuevo.

        Un coseno de 0.86 no dice cuál de tres cosas distintas ha pasado, y
        las tres piden conductas opuestas: que lo mirado concuerda, que se
        ha mirado poco, o que la hipótesis deja al paciente sin explicar.
        El número fundido las presenta iguales.

        Llamando `S` a las dimensiones declaradas que el registro **sí**
        informa, y usando que `e` vale 0 en las que nadie miró:

            cos(h,e) = ─────────── · ─────── · ───────
                        ‖h_S‖‖e_S‖    ‖h‖       ‖e‖
                          h_S·e_S      ‖h_S‖     ‖e_S‖

            cos = dirección · √cobertura · √explicación

        No es una aproximación: es la misma cantidad escrita sin cancelar,
        y el producto la reconstruye exactamente.

        LOS DOS LADOS, QUE SON DISTINTOS
        La **cobertura** es del lado `h`: cuánto de lo que la hipótesis
        afirma se ha puesto a prueba. La **explicación** es del lado `e`:
        cuánto de lo que el paciente tiene cae dentro de lo que la
        hipótesis declara. El resto no simbolizado no entra en la
        cobertura —no es superficie de la hipótesis, es del paciente— pero
        tampoco desaparece: sale por la explicación, que es su lado.

        Esa asimetría es la que hace legible la diferencia entre *nada la
        contradice todavía* —dirección alta, cobertura baja— y *se ha
        puesto a prueba y aguanta* —las dos altas—.

        Y NUNCA SE MULTIPLICAN
        Los tres ya están dentro de `coseno`. Se informan para poder leer
        POR QUÉ salió lo que salió; aplicarlos otra vez contaría dos veces
        lo mismo. Es la misma razón por la que la cobertura acompaña a un
        posterior provisional en vez de corregirlo.

        Se devuelve `None` —y no 0.0— donde la definición no existe: sin
        dimensión declarada no hay cobertura que preguntar, y sin nada
        mirado no hay dirección. Un cero diría que el factor vale cero, que
        es una afirmación distinta y falsa.
        """
        declaradas = [
            c for c in componentes if c.estado is not EstadoDimension.NO_SIMBOLIZADO
        ]
        medidas = [
            c
            for c in declaradas
            if c.estado in (EstadoDimension.CONCUERDA, EstadoDimension.CONTRADICE)
        ]

        norma_h = sum(c.esperado**2 for c in declaradas)
        norma_h_s = sum(c.esperado**2 for c in medidas)
        norma_e_s = sum(c.observado**2 for c in medidas)
        # ‖e‖ va sobre TODOS los componentes: el resto no simbolizado tiene
        # h=0 y no toca el numerador, pero sí esta norma. Ahí es donde el
        # resto cobra su descuento, y por eso el tercer factor existe.
        norma_e = sum(c.observado**2 for c in componentes)

        cobertura = norma_h_s / norma_h if norma_h else None
        explicacion = norma_e_s / norma_e if norma_e else None
        direccion = None
        if norma_h_s and norma_e_s:
            producto = sum(c.esperado * c.observado for c in medidas)
            direccion = producto / math.sqrt(norma_h_s * norma_e_s)
            direccion = max(-1.0, min(1.0, direccion))

        traza: list[str] = []
        if direccion is not None:
            traza.append(
                f"dirección = cos(h_S, e_S) = {direccion:.4f} — de lo mirado, "
                f"cuánto concuerda con la hipótesis"
            )
        if cobertura is not None:
            traza.append(
                f"cobertura = {cobertura:.2%} — de lo que la hipótesis afirma, "
                f"cuánto se ha puesto a prueba"
            )
        if explicacion is not None:
            traza.append(
                f"explicación = {explicacion:.2%} — de lo que el paciente tiene, "
                f"cuánto cae dentro de la hipótesis"
            )
        if direccion is not None and cobertura is not None and explicacion is not None:
            reconstruido = direccion * math.sqrt(cobertura * explicacion)
            traza.append(
                f"cos = dirección · √(cobertura · explicación) = {reconstruido:.4f}"
            )
        return direccion, cobertura, explicacion, traza

    # --- Anclaje ------------------------------------------------------

    def _anclaje(
        self,
        dimensiones: list[dict[str, Any]],
        observaciones: dict[str, Infon],
        residuo: Sequence[Infon],
        skill: "Skill",
        infones: Sequence[Infon],
    ) -> tuple[float, dict[str, float], list[str]]:
        """α: cuánto de este argumento está sujeto a la realidad medida.

        Media geométrica de tres factores. Geométrica porque el colapso de
        uno solo debe bastar: un razonamiento impecable sobre LR sin fuente
        no es medio verdadero, es irrelevante.
        """
        # Los infones que sostienen la lectura, sea cual sea la que exista:
        # los emparejados con dimensiones que llevan LR, los emparejados con
        # signos declarados por categoría, y el resto no simbolizado. Contar
        # sólo los primeros dejaba α a 0 en cuanto el protocolo no declaraba
        # cocientes, que es precisamente el caso que el vector categórico
        # vino a cubrir.
        contribuyentes = list(observaciones.values())
        vistos = {id(i) for i in contribuyentes}
        for infon in self._infones_invocados(skill, infones):
            if id(infon) not in vistos:
                vistos.add(id(infon))
                contribuyentes.append(infon)
        for infon in residuo:
            if id(infon) not in vistos:
                vistos.add(id(infon))
                contribuyentes.append(infon)

        if not contribuyentes:
            detalle = {"confianza": 0.0, "procedencia": 0.0, "fuente": 0.0}
            return 0.0, detalle, ["α = 0 — ningún infón sostiene el vector"]

        n = float(len(contribuyentes))
        a_conf = (
            sum(min(max(i.confianza, 0.0), 100.0) / 100.0 for i in contribuyentes) / n
        )
        a_proc = (
            sum(_calidad_normalizacion(i.razon_auditoria) for i in contribuyentes) / n
        )

        # Sólo se juzga la procedencia de lo que este caso realmente usó.
        # Que el protocolo tenga un signo sin fuente no ensucia un
        # razonamiento que no lo invocó.
        #
        # Cuando el protocolo declara categorías y no cocientes, no hay LR
        # que citar y esta lista quedaba vacía: α colapsaba a 0 y con él
        # todo Φ, castigando por falta de fuente a un protocolo que puede
        # estar perfectamente citado. La procedencia se juzga entonces sobre
        # los SIGNOS declarados que el caso invocó, que es donde vive la
        # cita en un criterio categórico.
        usadas = [d for d in dimensiones if d["clave"] in observaciones]
        if usadas:
            a_fuente = sum(1.0 for d in usadas if d["fuente"]) / len(usadas)
        else:
            invocados = self._signos_invocados(skill, infones)
            a_fuente = (
                sum(1.0 for s in invocados if (s.fuente or "").strip()) / len(invocados)
                if invocados
                else 0.0
            )

        detalle = {
            "confianza": round(a_conf, 4),
            "procedencia": round(a_proc, 4),
            "fuente": round(a_fuente, 4),
        }
        alfa = (max(a_conf, 0.0) * max(a_proc, 0.0) * max(a_fuente, 0.0)) ** (1 / 3)

        traza = [
            f"α confianza = {a_conf:.3f} · procedencia = {a_proc:.3f} · "
            f"fuente de los LR = {a_fuente:.3f}",
            f"α = media geométrica = {alfa:.4f}",
        ]
        if a_fuente == 0.0 and usadas:
            traza.append(
                "Ningún LR invocado cita fuente: el argumento no está anclado "
                "y Φ colapsa a 0 (irrelevante), no a un valor negativo."
            )
        return alfa, detalle, traza

    @staticmethod
    def _emparejar_signos(skill: "Skill", infones: Sequence[Infon]) -> dict:
        """Signo declarado -> primer infón validado que lo toca, lleve LR o no."""
        from .bayes import emparejar_termino

        indice = {s.nombre.lower(): s for s in skill.signos if s.efecto != "excluye"}
        vistos: dict[str, tuple] = {}
        for infon in infones:
            if not infon.es_valido:
                continue
            clave = emparejar_termino(infon.termino, indice)
            if clave is not None:
                vistos.setdefault(clave, (indice[clave], infon))
        return vistos

    def _signos_invocados(self, skill: "Skill", infones: Sequence[Infon]) -> list:
        """Signos declarados que este caso realmente tocó."""
        return [signo for signo, _ in self._emparejar_signos(skill, infones).values()]

    def _infones_invocados(self, skill: "Skill", infones: Sequence[Infon]) -> list:
        """Infones que tocan un signo declarado, lleve LR o no."""
        return [infon for _, infon in self._emparejar_signos(skill, infones).values()]

    # --- Lectura ------------------------------------------------------

    @staticmethod
    def _veredicto(
        phi: float, componentes: Sequence[ComponenteAcoplamiento]
    ) -> VeredictoSemiotico:
        if phi >= UMBRAL_ARMONIA:
            return VeredictoSemiotico.ARMONIA
        if phi >= UMBRAL_ACOPLAMIENTO:
            return VeredictoSemiotico.ACOPLAMIENTO_PARCIAL
        if phi <= UMBRAL_DESARMONIA:
            return VeredictoSemiotico.DESARMONIA
        if phi <= UMBRAL_FRICCION:
            return VeredictoSemiotico.FRICCION
        return VeredictoSemiotico.INERCIA

    @staticmethod
    def _cuadrante(phi: float, inferencia: InferenciaBayesiana | None) -> str:
        """La lectura conjunta (P, Φ), que es donde está el valor clínico.

        Un sistema que sólo muestra P no puede avisar del error diagnóstico
        más frecuente: quedarse con la primera hipótesis que un dato fuerte
        hizo probable, mientras el resto del paciente dice otra cosa.
        """
        if inferencia is None:
            return "sin probabilidad con la que cruzar Φ"

        alta_p = inferencia.probabilidad_porcentaje >= UMBRAL_PROBABILIDAD

        if alta_p:
            # El lado sensible. Una creencia sobre la que se va a actuar no
            # merece tres bandas por capricho: la diferencia entre «probable
            # y armónica», «probable con cabos sueltos» y «probable pero
            # ajena al paciente» es la diferencia entre tratar, seguir
            # indagando, y parar a replantear el caso entero.
            if phi >= UMBRAL_ARMONIA:
                return (
                    "Creencia operable: probable y en armonía con el contexto. "
                    "Puede sostener una regla de acción."
                )
            if phi >= UMBRAL_ACOPLAMIENTO:
                return (
                    "Certeza con resto no simbolizado: la hipótesis es probable "
                    "pero no da cuenta de todo el paciente. Revisar qué queda "
                    "fuera antes de cerrar el caso."
                )
            return (
                "CERTEZA MAL ACOPLADA: la probabilidad descansa en un dato "
                "fuerte mientras el resto del registro dice otra cosa. Es la "
                "forma que toma el sesgo de anclaje. No actuar sin replantear."
            )

        if phi >= UMBRAL_ACOPLAMIENTO:
            return (
                "Hipótesis coherente pero aún improbable: lo que hay encaja, "
                "falta evidencia. La indagación es productiva."
            )
        return "Hipótesis ajena a este caso: ni probable ni acoplada."

    @staticmethod
    def _indagacion(
        componentes: Sequence[ComponenteAcoplamiento],
    ) -> list[str]:
        """Qué preguntar para resolver la duda, ordenado por informatividad.

        La duda no es una emoción del sistema: es una dirección. La
        dimensión donde la hipótesis hace su afirmación más fuerte y nadie
        ha mirado todavía es, literalmente, la pregunta cuya respuesta más
        moverá Φ. Ahí se indaga primero.
        """
        pendientes = [
            c for c in componentes if c.estado is EstadoDimension.SIN_MEDIR and c.esperado
        ]
        pendientes.sort(key=lambda c: abs(c.esperado), reverse=True)

        preguntas = [
            f"{c.dimension} ({c.rol}): sin dato, es la afirmación más fuerte "
            f"de la hipótesis que nadie ha comprobado"
            if i == 0
            else f"{c.dimension} ({c.rol}): sin dato"
            for i, c in enumerate(pendientes[:5])
        ]

        contradicen = [c for c in componentes if c.estado is EstadoDimension.CONTRADICE]
        preguntas.extend(
            f"{c.dimension}: el registro contradice lo que la hipótesis exige "
            f"({c.detalle}) — la duda empieza aquí"
            for c in contradicen
        )

        no_simbolizados = [
            c for c in componentes if c.estado is EstadoDimension.NO_SIMBOLIZADO
        ]
        if no_simbolizados:
            nombres = ", ".join(c.dimension for c in no_simbolizados[:5])
            preguntas.append(
                f"Resto no simbolizado ({nombres}): ¿qué hipótesis lo explica? "
                f"Si una segunda hipótesis sube Φ del conjunto, la diversidad "
                f"está justificada; si lo baja, sobra."
            )
        return preguntas


# --- Utilidades -------------------------------------------------------


def _positivo(valor: Any) -> float | None:
    """Un LR sólo es utilizable si es un número estrictamente positivo."""
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        return None
    lr = float(valor)
    return lr if lr > 0 else None


def _calidad_normalizacion(razon_auditoria: str) -> float:
    """Extrae el método del validador de la traza y lo puntúa.

    La traza tiene la forma "[metodo] explicación". Se lee de ahí y no de
    un campo propio porque el método ya viaja en el infón desde el
    pipeline; duplicarlo sería una segunda fuente de verdad.
    """
    texto = (razon_auditoria or "").strip()
    if not texto.startswith("["):
        return CALIDAD_METODO_DESCONOCIDO
    cierre = texto.find("]")
    if cierre < 0:
        return CALIDAD_METODO_DESCONOCIDO
    metodo = texto[1:cierre].strip().lower()
    return CALIDAD_METODO.get(metodo, CALIDAD_METODO_DESCONOCIDO)
