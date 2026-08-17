# El Coeficiente de Acoplamiento (Φ)

**Validación semiótica del diagnóstico en HolonMed.**
Módulo: `backend/holonmed/core/acoplamiento.py` · Tests: `backend/tests/test_acoplamiento.py`

---

## 1. El problema que Bayes no resuelve

El motor abductivo de HolonMed responde bien a una pregunta: **cuánta**
evidencia sostiene una hipótesis. Parte de la prevalencia, la ajusta por los
factores de riesgo del paciente y la actualiza con los likelihood ratios de
cada hallazgo validado. La probabilidad posterior es correcta y su traza es
auditable línea por línea.

Pero la probabilidad es una suma, y una suma pierde información sobre sus
sumandos. Dos historias pueden arrojar exactamente el mismo posterior siendo
cosas clínicamente muy distintas:

- En la primera, todos los hallazgos apuntan al mismo sitio con fuerza
  moderada y no queda nada del paciente sin explicar.
- En la segunda, una única prueba muy específica arrastra la probabilidad
  mientras cuatro hallazgos del enfermo hablan de otra enfermedad.

Bayes no las distingue, porque suma. La segunda tiene nombre en la
literatura de error diagnóstico y se llama **sesgo de anclaje**: quedarse con
la hipótesis que un dato fuerte hizo probable y dejar de mirar el resto. Un
sistema de apoyo a la decisión que sólo muestre la probabilidad no sólo no
protege de ese error: lo autoriza con un número.

Φ existe para medir la segunda dimensión: si la hipótesis, **tomada como
regla de acción**, armoniza con el paciente entero.

---

## 2. Fundamento: la creencia como regla de acción

Una creencia no es una imagen del mundo, es una disposición a actuar. Creer
que este paciente tiene una pancreatitis aguda es estar dispuesto a hacer lo
que se hace ante una pancreatitis: pedir, ingresar, hidratar, no operar. La
creencia se define por la conducta que autoriza.

De ahí se sigue el criterio de verdad que este módulo implementa. Una
creencia es verdadera cuando esa regla se acopla al contexto sin fricción, y
es falsa cuando produce **duda** —esa incomodidad que aparece cuando el
mundo no responde como la regla anticipaba— que es precisamente lo que
reabre la indagación. La duda no es un defecto del sistema: es su motor.

La condición filosófica que se exige para aceptar una creencia como cierta
es que esté en armonía con el contexto. La apuesta de este módulo es que esa
armonía **no es un estado místico ni una impresión subjetiva, sino una
cantidad geométrica**, y que puede calcularse con aritmética determinista
sobre artefactos que el sistema ya produjo y ya auditó.

---

## 3. La fórmula vectorial

### 3.1 El espacio y su métrica

En el espacio de los hallazgos clínicos, el peso natural de cada dimensión
es el **peso de evidencia**, `ln(LR)`. La elección no es estética: es
aditivo, tiene signo, y es exactamente la moneda en la que ya razona el
motor bayesiano.

Sobre ese espacio se construyen dos vectores.

**h — el caso de libro.** Lo que la hipótesis *exige* del mundo si es
cierta. Cada signo declarado por el protocolo aporta `hᵢ = ln(LR⁺ᵢ)`. Cuando
un signo sólo declara `LR⁻` —caso legítimo: hay pruebas cuya única
información útil es su negatividad— se usa `−ln(LR⁻ᵢ)`, que es positivo y
tiene la magnitud del poder discriminante de esa prueba.

**e — el caso real.** Lo que el registro de *este* paciente afirma de hecho:

| situación en el registro | eᵢ |
|---|---|
| hallazgo validado y **presente** | `ln(LR⁺ᵢ)` |
| ausencia **documentada** y validada | `ln(LR⁻ᵢ)` (negativo) |
| nadie lo ha mirado | `0` |

La tercera fila es una decisión de seguridad heredada del resto del sistema:
**el silencio no es evidencia**. Que no se hable de algo no significa que no
esté; significa que no se sabe.

### 3.2 La métrica

```
                 h · e
   cos(h, e) = ───────────      ∈ [−1, +1]
                ‖h‖ · ‖e‖

   Φ = α · cos(h, e)
```

Y eso es toda la métrica. `α ∈ [0,1]` es el coeficiente de anclaje de la
sección 5.

### 3.3 La relación con el motor bayesiano

No son dos modelos compitiendo. Son **dos proyecciones del mismo objeto**:

```
   Σ eᵢ  =  ln(odds posterior / odds previo)
```

Es decir: **Bayes lee la magnitud del vector de evidencia y Φ lee su
dirección.** Por eso Φ puede añadir información sin contradecir la
probabilidad, y por eso no debe modificarla jamás. La identidad está
comprobada como test (`test_phi_y_bayes_leen_el_mismo_vector`), y es la
razón de que el emparejamiento término↔signo viva en una sola función
compartida (`bayes.emparejar_termino`): si los dos módulos poblaran el
vector con criterios distintos, la identidad se rompería en silencio.

---

## 4. Los tres polos salen de la geometría

No hay que postularlos: son lo que hace un coseno.

| Φ | nombre | qué significa |
|---|---|---|
| **+1** | **armonía** | El registro dice exactamente lo que la hipótesis exige. La acción del argumento simboliza correctamente la realidad física del paciente. |
| **0** | **inercia** | Los vectores son ortogonales. La hipótesis conserva íntegro su orden interno pero no toca este caso: ni contribuye ni daña, es irrelevante para la evolución del paciente. |
| **−1** | **desarmonía** | La hipótesis mantiene su orden interno y aun así el contexto la contradice punto por punto. El análisis se vuelve caos. |

Las bandas de lectura (`VeredictoSemiotico`) son presentación, no métrica:

```
Φ ≥  0.60   ARMONIA                creencia operable
Φ ≥  0.20   ACOPLAMIENTO_PARCIAL   encaja, pero queda por mirar
|Φ| < 0.20  INERCIA                ortogonal: no toca este caso
Φ ≤ −0.20   FRICCION               el contexto empieza a disentir
Φ ≤ −0.60   DESARMONIA             el contexto la contradice
```

---

## 5. El resto no simbolizado

Un hallazgo validado que el protocolo no contempla **se añade como una
dimensión propia**, donde `h = 0` y `e ≠ 0`. Es ortogonal por construcción,
así que baja el coseno **sin ningún castigo escrito en ninguna parte**: una
hipótesis que deja media historia sin explicar se desacopla sola.

Esto es lo que significa exigir que un signo represente a su objeto. Un
diagnóstico que no simboliza lo que el paciente tiene es un símbolo
incompleto, y el sistema lo dice con un número en lugar de con una
advertencia genérica.

Dos decisiones finas:

**Sólo cuentan los hallazgos presentes.** Una ausencia documentada ajena al
protocolo —una fiebre que se buscó y no hay— no es fricción: es un clínico
haciendo bien su trabajo, y penalizarla sería absurdo.

**El resto se escala al caso, no al protocolo.** Cada hallazgo no explicado
pesa la media cuadrática del peso de evidencia que este mismo caso *sí*
explicó. La regla queda: *por cada hallazgo que la hipótesis explica con peso
w, uno que no explica le cuesta otro tanto*. La primera versión de este
módulo escalaba el resto a la mediana del protocolo, y el resultado era que
una prueba con LR enorme compraba armonía casi ilimitada — acertar el
laboratorio estelar bastaba para tapar cualquier cantidad de historia sin
explicar. Es exactamente el error que Φ debe delatar, no cometer.
(`test_una_prueba_estelar_no_compra_armonia_ilimitada`.)

---

## 6. Parsimonia y diversidad

El criterio queda definido sobre esta misma cantidad, aunque su cálculo
pertenece a la fase 2:

> Una segunda hipótesis se justifica exactamente cuando **añadirla sube Φ
> del conjunto**: `Φ(H ∪ {h}) > Φ(H)`.

Si al añadirla el acoplamiento del conjunto sube, la hipótesis **crea orden y
significado** y la diversidad está justificada. Si baja, es proliferación, y
la parsimonia gana. El criterio no lo pone el gusto del clínico ni una
preferencia estética por lo simple: lo pone la aritmética, caso por caso.

Nótese que esto también castiga el extremo contrario al monismo: una docena
de diagnósticos, cada uno explicando un hallazgo, es internamente ordenada y
sin embargo no unifica nada — el polo Φ = 0.

En fase 1 el sistema no calcula conjuntos, pero **sí entrega la materia
prima**: la lista `resto_no_simbolizado` es literalmente la semilla de la
hipótesis competidora, y aparece en `indagacion` formulada como pregunta.

---

## 7. La guarda anti-pseudociencia (α)

Un argumento puede ser internamente perfecto y no tocar la realidad. La
homeopatía tiene coherencia interna; su coseno consigo misma vale 1. Sin una
guarda, la métrica confundiría **elaboración con verdad**, y un discurso
altamente estructurado pero desacoplado saldría premiado como "armónico".

Por eso el coseno se multiplica por un **coeficiente de anclaje** `α ∈ [0,1]`,
media **geométrica** de tres factores —geométrica y no aritmética porque el
fallo de uno solo debe bastar para colapsar el resultado:

1. **Confianza** — la confianza media de los infones que sostienen el vector.
   ¿Está la evidencia auditada, o solamente es plausible?
2. **Procedencia** — cómo se ancló cada término al vocabulario: un código
   revisado por un humano en el protocolo (1.00) no vale lo mismo que una
   coincidencia difusa que superó el umbral por poco (0.60).
3. **Fuente de los likelihood ratios en uso** — la fracción de los LR
   efectivamente invocados que citan procedencia. *Un LR sin fuente es un
   número inventado con formato científico.*

Un argumento cuyos LR no citan fuente obtiene `α = 0` y por tanto **Φ = 0**.
Obsérvese qué se afirma exactamente: no se le declara *falso*, se le declara
**irrelevante**, que es el polo cero. La elaboración sin anclaje no compra
armonía. El test `test_argumento_sin_fuentes_colapsa_a_irrelevante` construye
dos protocolos idénticos salvo por las citas: el coseno es el mismo —la
coherencia interna está intacta— y uno da ARMONIA mientras el otro da
INERCIA.

Sólo se juzga la procedencia de los LR que el caso realmente usó. Que el
protocolo tenga un signo sin fuente no ensucia un razonamiento que no lo
invocó.

---

## 8. La lectura conjunta (P, Φ)

Φ **nunca** modifica la probabilidad. Lo que se entrega al clínico es el par,
y el `cuadrante` lo nombra:

| P | Φ | lectura |
|---|---|---|
| ≥ 50 % | ≥ 0.60 | **Creencia operable.** Probable y en armonía. Puede sostener una regla de acción. |
| ≥ 50 % | 0.20–0.60 | **Certeza con resto no simbolizado.** Probable, pero no da cuenta de todo el paciente. Revisar qué queda fuera antes de cerrar el caso. |
| ≥ 50 % | < 0.20 | **CERTEZA MAL ACOPLADA.** La probabilidad descansa en un dato fuerte mientras el resto del registro dice otra cosa. Es la forma que toma el sesgo de anclaje. No actuar sin replantear. |
| < 50 % | ≥ 0.20 | **Coherente pero aún improbable.** Lo que hay encaja, falta evidencia: la indagación es productiva. |
| < 50 % | < 0.20 | **Hipótesis ajena a este caso.** |

Las tres bandas del lado probable no son un capricho: la diferencia entre
*tratar*, *seguir indagando* y *parar a replantear el caso entero* es
demasiado grande para resolverse con un booleano.

---

## 9. La duda como dirección

La duda no es una emoción del sistema, es un vector. La dimensión donde la
hipótesis hace su afirmación más fuerte y donde **nadie ha mirado todavía**
es, literalmente, la pregunta cuya respuesta más movería Φ. Ahí se indaga
primero, y por eso `indagacion` viene ordenada por `|hᵢ|` y no por el orden
en que el protocolo declaró los signos.

Nótese cómo lo no medido se comporta solo: sube `‖h‖` sin subir `h·e`, de
modo que **un caso a medio estudiar da armonía parcial, no desarmonía**. Que
es exactamente lo que es. No hizo falta programar esa distinción: la
geometría la produce.

---

## 10. Comportamiento verificado

Viñetas reales contra `backend/skills/acute_pancreatitis.md`, el protocolo
del repositorio y sus LR publicados:

| viñeta | P % | cos | α | **Φ** | veredicto |
|---|---:|---:|---:|---:|---|
| A. Pancreatitis de libro | 99.0 | 0.804 | 0.983 | **0.791** | ARMONIA |
| B. Enzimas normales, dolor negado | 0.0 | −0.733 | 0.983 | **−0.721** | DESARMONIA |
| C. Lipasa alta en polipatológico | 81.8 | 0.279 | 0.983 | **0.274** | ACOPLAMIENTO_PARCIAL |
| D. Sólo vómitos | 7.8 | 0.089 | 0.983 | **0.088** | INERCIA |
| E. Protocolo ajeno al caso | 5.0 | 0.000 | 0.000 | **0.000** | INERCIA |
| F. Lipasa alta con dolor, sin imagen | 98.0 | 0.645 | 0.983 | **0.634** | ARMONIA |

**La viñeta C es la razón de ser del módulo.** Un paciente de 74 años con
lipasa elevada, hematuria, soplo sistólico, edemas y disnea paroxística
nocturna. Bayes dice 81.8 % de pancreatitis y no se equivoca: la lipasa vale
lo que vale. Φ dice 0.27, y el sistema responde:

```
Cuadrante: Certeza con resto no simbolizado: la hipótesis es probable pero
no da cuenta de todo el paciente. Revisar qué queda fuera antes de cerrar
el caso.

Resto no simbolizado: Hematuria, Soplo sistólico, Edema de miembros
inferiores, Disnea paroxística nocturna

Indagación:
  - Hiperamilasemia (>3x) (prueba_especifica): sin dato, es la afirmación
    más fuerte de la hipótesis que nadie ha comprobado
  - Hallazgos de imagen compatibles con pancreatitis (imagen): sin dato
  - Resto no simbolizado (Hematuria, Soplo sistólico, Edema de miembros
    inferiores, Disnea paroxística nocturna): ¿qué hipótesis lo explica?
    Si una segunda hipótesis sube Φ del conjunto, la diversidad está
    justificada; si lo baja, sobra.
```

Los tres hallazgos cardiológicos que quedan fuera son, en este caso, una
insuficiencia cardíaca que el protocolo de pancreatitis no puede ver. El
sistema no la diagnostica —no le corresponde— pero deja de afirmar que el
caso está cerrado, y nombra exactamente lo que falta por explicar.

---

## 11. Decisiones de diseño y sus razones

**Φ no llama al LLM.** Se calcula con aritmética determinista sobre
artefactos que las etapas anteriores ya auditaron. Meter aquí un juicio del
modelo sería fundar la validación semiótica en la misma fluidez que la
validación existe para contener.

**Φ no toca la probabilidad.** Son ejes independientes. Multiplicar los odds
por Φ daría una sola cifra más cómoda y destruiría la trazabilidad
bayesiana, que es lo que hace impugnable el razonamiento.

**Φ es auditable dimensión por dimensión.** `componentes` expone, por cada
dimensión, lo que la hipótesis exigía y lo que el registro aportó. Un clínico
puede discrepar de una línea concreta, igual que puede hacerlo con la traza
de Bayes. Una métrica de armonía que no se pudiera impugnar punto por punto
sería justamente el tipo de argumento que la métrica existe para detectar.

**Sin LR declarados, `medir()` devuelve `None`, no un Φ de 0.** Son cosas
distintas: Φ = 0 dice que la hipótesis no toca al paciente; `None` dice que
no hay con qué preguntarlo. Confundirlas sería inventar una medida.

**Sólo entra evidencia VALIDADA.** Un infón en ALERTA se le muestra al
clínico pero no acopla, igual que no entra en Bayes ni puede satisfacer un
criterio de clasificación.

**Manda el registro más reciente.** Cuando dos infones sobre el mismo signo
se contradicen, gana el nuevo: una lipasa normal hoy no queda anulada por
una lipasa alta de la semana pasada, aunque aquélla se midiera con más
confianza.

---

## 12. Limitaciones conocidas

- **El peso del resto es una convención**, no una medida. No hay forma de
  conocer el LR de un hallazgo que el protocolo no contempla: si lo hubiera,
  estaría contemplado. La media cuadrática del caso es defendible y está
  documentada, pero es una elección.
- **El emparejamiento término↔signo es por subcadena**, heredado del motor
  bayesiano. Es su limitación conocida, y se hereda a propósito para
  preservar la identidad `Σeᵢ = ln(odds posterior / odds previo)`.
- **No se usa `ambito_grafo` todavía.** Un hallazgo que cae en una rama que
  el protocolo reconoce pero no cuantifica cuenta hoy como resto entero;
  podría contar como resto parcial.
- **Φ no se persiste.** La tabla `tics` guarda `inferencia` pero no
  `acoplamiento`: al recargar el historial, Φ se pierde. Es una columna
  nueva, y es el requisito de la fase 3.

---

## 13. Hoja de ruta

**Fase 1 — implementada.** Φ de hipótesis única: cobertura, contradicción,
resto no simbolizado, anclaje, indagación dirigida, lectura por cuadrantes.

**Fase 2 — parsimonia y diversidad.** Evaluar conjuntos de hipótesis y
aplicar el criterio `ΔΦ > 0`. Requiere activar varios protocolos por tic;
`SkillManager.para_concepto()` y `ambito_grafo` ya existen para eso.

**Fase 3 — la duda temporal.** Persistir Φ por tic y calcular `dΦ/dt`. Una
creencia en armonía no necesita rescates: si cada nuevo tic obliga a revisar
la hipótesis, eso *es* la duda, y debe reabrir la indagación por sí sola. Es
la formulación más literal del principio, y la que sólo el holón —la historia
como organismo que crece— hace posible.
