# El Coeficiente de Acoplamiento (Φ)

**Validación semiótica del diagnóstico en HolonMed.**
Módulo: `backend/holonmed/core/acoplamiento.py` · Tests: `backend/tests/test_acoplamiento.py`
Complementa [`docs/VEREDICTO.md`](VEREDICTO.md), que documenta los tres
niveles de la decisión: vetar, contar, balancear.

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
   Σ eᵢ  =  ln(odds posterior / odds previo)          (sobre las dimensiones declaradas)
```

Es decir: **Bayes lee la magnitud del vector de evidencia y Φ lee su
dirección.** Por eso Φ puede añadir información sin contradecir la
probabilidad, y por eso no debe modificarla jamás. Es también la razón de
que el emparejamiento término↔signo viva en una sola función compartida
(`bayes.emparejar_termino`): si los dos módulos poblaran el vector con
criterios distintos, la identidad se rompería en silencio.

**Dónde termina la identidad.** Es exacta, pero no incondicional, y decirlo
importa: quien la dé por universal escribirá código que la rompa sin
enterarse. Se cumple bajo tres condiciones.

**1. La suma corre sobre el subespacio declarado, no sobre el vector
completo.** El resto no simbolizado entra con un peso que es una convención
de este módulo (sección 5) y con el que Bayes nunca operó. La cantidad que
iguala el delta bayesiano es `Acoplamiento.peso_evidencia_declarado`, que
excluye el residuo explícitamente. Existe como propiedad con nombre, y no
como una suma escrita dentro de un test, precisamente para que quien cambie
la escala del residuo vea que la invariante lo excluye a propósito.

**2. Ambos motores tienen que recibir el mismo conjunto de infones.** El
pipeline no lo hace, y no por descuido: Bayes recibe el tic de hoy y Φ
recibe además la línea de tiempo del holón, porque medir el acoplamiento
contra medio paciente no mediría nada. Con historial previo la identidad
deja de valer numéricamente, aunque la relación conceptual —magnitud frente
a dirección— se mantiene intacta.

**3. A lo sumo un infón validado por dimensión.** Si dos infones emparejan
con el mismo signo, Bayes multiplica su LR dos veces y este módulo lo cuenta
una. Aquí la discrepancia no favorece a Bayes: contar dos veces la misma
prueba es doble contabilidad de la evidencia. Se deja como está porque
corregirlo es cambiar el motor bayesiano, y eso es otra conversación.

Las tres condiciones están fijadas como tests —incluida la divergencia, que
se afirma para que nadie la «arregle» creyendo que corrige un fallo:

| test | qué fija |
|---|---|
| `test_phi_y_bayes_leen_el_mismo_vector` | la identidad sobre el subespacio declarado |
| `test_la_identidad_sobrevive_al_resto_no_simbolizado` | que con residuo el subespacio cuadra y el vector completo no |
| `test_la_identidad_exige_el_mismo_conjunto_de_infones` | la divergencia que introduce el historial |
| `test_la_identidad_exige_un_infon_por_dimension` | el factor 2 del doble emparejamiento |
| `test_el_peso_declarado_excluye_el_residuo_por_construccion` | que la invariante viva en el código |

### 3.4 Los tres factores del coseno

Un coseno de 0.86 no dice cuál de tres cosas ha pasado, y las tres piden
conductas distintas: que lo mirado concuerda, que se ha mirado poco, o que
la hipótesis deja al paciente sin explicar. El número fundido las presenta
iguales.

Llamando `S` a las dimensiones declaradas que el registro **sí** informa, y
usando que `e` vale 0 en las que nadie miró:

```
                h_S · e_S       ‖h_S‖     ‖e_S‖
   cos(h, e) = ───────────  ·  ───────  ·  ───────
                ‖h_S‖‖e_S‖       ‖h‖        ‖e‖

   cos = dirección · √cobertura · √explicación
```

No es una descomposición aproximada ni una métrica nueva: es el mismo
coseno escrito sin cancelar, y el producto lo reconstruye.

| factor | fórmula | qué mide | lado |
|---|---|---|---|
| **dirección** | `cos(h_S, e_S)` | de lo mirado, cuánto concuerda | — |
| **cobertura** | `‖h_S‖²/‖h‖²` | de lo que la hipótesis **afirma**, cuánto se ha puesto a prueba | `h` |
| **explicación** | `‖e_S‖²/‖e‖²` | de lo que el paciente **tiene**, cuánto cae dentro de la hipótesis | `e` |

**Los dos lados no se mezclan, y ahí está el contenido.** El resto no
simbolizado (sección 5) no entra en la cobertura —no es superficie de la
hipótesis, es del paciente, y meterlo haría que un paciente complejo bajara
la cobertura de una hipótesis bien examinada— pero tampoco desaparece: sale
por la explicación, que es su lado. Es el mismo hecho de la sección 5 visto
como factor en vez de como dimensión ortogonal.

**Se informan y nunca se aplican.** Los tres ya están dentro de `coseno`;
multiplicarlos otra vez contaría dos veces lo mismo. Sirven para leer *por
qué* salió lo que salió, que es la diferencia entre «nada la contradice
todavía» —dirección alta, cobertura baja— y «se ha puesto a prueba y
aguanta» —las dos altas—.

**Valen `None` donde su definición no existe**, no cero: un protocolo que
declara categorías y no cocientes no tiene cobertura ponderada que
preguntar, y un cero afirmaría que no se ha mirado nada. Es la misma
distinción por la que `medir` devuelve `None` en vez de un Φ de 0, y la que
`SIN_MEDIR` hace un nivel más abajo: no es ausencia, es vacío.

**Los tres se publican redondeados a cuatro decimales, y el producto se
calcula sin redondear.** Quien recomponga la identidad desde los números
que ve puede obtener `0.7020` donde `coseno` dice `0.7019`: son hasta tres
cuantos de redondeo, no un desacuerdo. Para ordenar candidatas se usa
`coseno` —o `coseno_categorico`—, que es el valor íntegro; los factores
sirven para leer por qué, no para rehacer la cuenta.

### 3.5 La lectura categórica es la misma, con pesos unitarios

La descomposición no es propia de la lectura ponderada: es lo que hace
cualquier coseno. Con `h` el vector de unos, cada término se simplifica —y
se expone igual, con el mismo criterio de `None`:

| factor | ponderada | categórica |
|---|---|---|
| dirección | `cos(h_S, e_S)` | `Σeᵢ / m` |
| cobertura | `‖h_S‖²/‖h‖²` | `m / D` |
| explicación | `‖e_S‖²/‖e‖²` | `m / (m+r)` |

**Y las dos leen en la misma unidad.** La categórica *es* la ponderada con
todos los pesos iguales, y el coseno es invariante de escala: la escala se
cancela. Medido (`guiones/misma_escala.py`), cinco signos declarados y uno
presente:

```
ponderado · un LR estrella (26.6) y cuatro de 2.0      0.9212
ponderado · los cinco iguales (2.0)                    0.4472
categórico · los cinco iguales por definición          0.4472
```

Eso es lo que permite que una candidata categórica y una ponderada compitan
**sin traducción**. La asimetría que queda corre en una sola dirección: un
criterio categórico no puede concentrar su peso en un signo, así que nunca
alcanzará el coseno de una ponderada cuyo signo estrella consta. No es un
defecto — es la cobertura haciendo su trabajo.

**El término que se compara es `coseno_categorico`, no `phi_categorico`.**
El segundo lleva α dentro, y α es la calidad documental del protocolo:
ordenar por él ordenaría por cuán bien citado está el índice. Es el mismo
error, un nivel más abajo, que ordenar por Φ en vez de por `coseno`.

| test | qué fija |
|---|---|
| `test_los_tres_factores_reconstruyen_el_coseno` | que el producto cierra, también con residuo |
| `test_el_resto_sale_por_la_explicacion_y_nunca_por_la_cobertura` | la asimetría entre los dos lados |
| `test_los_factores_distinguen_no_mirado_de_puesto_a_prueba` | lo que el número fundido no distinguía |
| `test_un_protocolo_categorico_no_finge_factores_ponderados` | `None` y no 0 |
| `test_los_factores_categoricos_reconstruyen_su_coseno` | el producto da `coseno_categorico`, no `phi_categorico` |
| `test_la_categorica_lee_en_la_misma_escala_que_la_ponderada` | que las dos lecturas compiten sin traducir |
| `test_el_coseno_categorico_no_lo_mueve_la_bibliografia` | que α no entra en la clave de orden |

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

Dicho con los factores de la sección 3.4: como `h = 0`, el resto no toca el
numerador ni la cobertura; sólo sube `‖e‖`. Todo su efecto sobre Φ pasa por
el factor de **explicación**, y ése es el lugar donde queda visible cuánto
del paciente se está dejando fuera.

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

La regla está fijada como propiedad en
`test_un_hallazgo_no_explicado_pesa_como_los_que_si_se_explican`, y la
regresión concreta —cuatro hallazgos sin explicar dejando el coseno en 0.55—
en `test_una_prueba_estelar_no_compra_armonia_ilimitada`. Volver a escalar
el residuo al protocolo hace caer los dos; comprobado por mutación.

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

### 9.1 Quién lee la duda, y qué abre

`Acoplamiento.duda` existía desde el primer día y **nadie la leía**. El
sistema calculaba que su hipótesis había dejado de funcionar como regla de
acción y terminaba el tic igual que si todo hubiera encajado. `core/duda.py`
es lo que la consume, y la etapa 8 del pipeline lo que la llama.

**No es un veto.** Una exclusión absoluta dice que el diagnóstico es
imposible y termina la pregunta; la duda dice que el argumento dejó de
sostenerse con lo que hay, y la reabre. Tampoco resuelve nada dentro del
tic: la deducción produce preguntas o una orden de prueba, y la respuesta
llega en otro tic. La reapertura es una **salida accionable**, no un
recálculo.

**La duda tiene tres clases, y se resuelven por caminos opuestos.** Esto es
lo que se ganó al partir cos(h,e) en tres (§3.4): el número fundido dice que
la creencia no funciona y no dice por qué.

| causa | qué pasó | qué hacer |
|---|---|---|
| **dirección** | lo que se miró **disiente** | no se arregla mirando más: cambiar de hipótesis |
| **cobertura** | casi nada se ha puesto a prueba | indagar, y `indagacion` ya dice por dónde |
| **explicación** | no explica al paciente | volver a la abducción: lo que falta está fuera |

La tercera es la forma que toma el sesgo de anclaje —la hipótesis puede ser
cierta y no ser la pregunta— y es el polo que Φ define como Φ = 0: argumento
internamente ordenado pero aislado.

**Cuál de los tres manda se decide en la escala del producto.** Como
`cos = dirección · √cobertura · √explicación`, cada factor lastra con
`dirección`, `√cobertura` y `√explicación`, y se compara en esa escala.
No es un tecnicismo: con dirección 0.2533 y cobertura 0.2108, el número
crudo menor es la cobertura y el que más lastra es la dirección —«mira
más» frente a «esto no encaja»—, que son consejos clínicos opuestos.

La dirección entra **con su signo** y no en valor absoluto. Una dirección
negativa es el registro contradiciendo, la duda más fuerte que hay, y ser la
menor de las tres es exactamente lo que le toca.

Un factor `None` no compite: no es un cero disfrazado, dice que ese factor
no está definido, y un factor indefinido no puede ser la causa de nada.

**La vuelta a la abducción no se recalcula.** La competencia ya corrió en la
etapa 3b sobre el mismo paciente, así que la reapertura sólo tiene que decir
a dónde apunta. Si la competencia prefiere la hipótesis que ya se estaba
usando, no hay alternativa que ofrecer y no se inventa una.

### 9.2 `phi_legible`: la duda leía el número equivocado

`duda` leía `phi`, y para un protocolo que declara categorías y no cocientes
`phi` vale 0 porque no hay vector ponderado que proyectar. Medido, sobre
apendicitis con tres signos a favor de cuatro:

```
phi            = 0.0
phi_categorico = 0.8513
veredicto      = ARMONIA
duda           = True
```

ARMONIA y duda a la vez, sobre el mismo objeto. Las bandas ya sabían leer el
categórico cuando la ponderada no existe, pero lo hacían con una variable
local de `medir`, de modo que ninguna propiedad del modelo podía hacer lo
mismo. `phi_legible` le da nombre a ese número.

Y explica por qué la propiedad llevaba tanto sin consumirse: MDS, Atlanta,
Duke y ACR/EULAR declaran categorías, así que la duda saltaba siempre en la
mayor parte del índice. Cablear una reapertura a la versión anterior habría
reabierto la indagación en todos los protocolos categóricos, acoplados o no.

**El categórico es el suplente, no el preferido.** Cuando existen las dos
lecturas manda la ponderada: un solo vómito —LR 1.6— da Φ ponderado 0.1092 y
Φ categórico 0.4915, porque la lectura de ±1 cuenta ese vómito igual que una
lipasa con LR de 26.6.

### 9.3 dΦ/dt: la duda es un movimiento, no una foto

La especificación del primer día dice que *la creencia falsa genera duda y
por eso motiva nueva indagación*, y el verbo importa: Peirce habla de la
creencia **establecida** que la experiencia desbarata. Un Φ bajo hoy no
distingue eso de una hipótesis que nunca funcionó, y no son la misma
situación clínica.

| trayectoria | qué pasó | qué significa |
|---|---|---|
| **se rompió** | venía por encima del mínimo y cayó | algo entró en el registro y desbarató la regla de acción; lo que la disparó está en los hallazgos nuevos |
| **nunca arraigó** | la vez anterior ya estaba por debajo | no se ha roto nada: la indagación no se reabre, sigue abierta |
| `null` | no hay medida anterior | no es que la creencia esté estable: es que no hay con qué compararla |

El tercer estado es `None` y no un literal que diga «estable», por la misma
razón por la que `medir` devuelve `None` en vez de un Φ de 0: afirmar
estabilidad sobre un primer tic sería inventar una trayectoria que nadie ha
medido.

**El corte es el mismo umbral que decide la duda.** El estado que se quiere
nombrar es «cruzó la raya», así que tiene que ser la raya. Con dos umbrales
distintos habría una franja en la que una creencia se rompe sin haber estado
nunca por encima.

**Y no reinterpreta nada.** La causa sigue saliendo de los tres factores de
este acoplamiento y las preguntas de su indagación. Que la creencia venga de
arriba o de abajo **añade** una lectura, igual que la cobertura se informa y
no se aplica.

#### De dónde sale el Φ anterior

`TicRepo.phi_por_hipotesis` recorre los tics de más nuevo a más viejo y
conserva el primero de cada hipótesis. El pipeline no habla con la base de
datos, así que el resultado llega en `HolonPaciente.phi_previo`, cargado por
quien construye el holón — el mismo camino que `linea_tiempo`.

Devuelve **`phi_legible` y no `phi`**, y no es un detalle. Para un protocolo
de categorías `phi` vale 0, de modo que guardar ese 0 haría que **toda
hipótesis categórica volviera como «nunca arraigó»** aunque hubiera estado
perfectamente acoplada: el modo de fallo de §9.2 reaparecido un nivel más
abajo, y otra vez sobre la mayoría del índice. El modelo se reconstruye desde
el JSON en vez de leer la columna a mano precisamente para que la regla de
cuál de las dos lecturas manda viva en un solo sitio.

El barrido está acotado a los últimos tics: una hipótesis que no aparece en
ese tramo no tiene trayectoria útil que ofrecer, y decir «no hay Φ previo» es
más honesto que desenterrar uno de hace un año y llamarlo tendencia.

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
  preservar la identidad de la sección 3.3.
- **En el pipeline, Bayes y Φ no ven el mismo conjunto de infones.** Es
  deliberado —Φ mide contra el paciente entero— pero significa que la
  identidad numérica sólo se observa en el primer tic de un paciente. Si
  alguna vez interesa comprobarla en producción, hay que llamar a `medir()`
  con el mismo conjunto que recibió Bayes.
- **Bayes cuenta dos veces dos infones sobre el mismo signo.** Φ los cuenta
  una. La divergencia está documentada y fijada como test; la corrección,
  si se hace, va en el motor bayesiano.
- **No se usa `ambito_grafo` todavía.** Un hallazgo que cae en una rama que
  el protocolo reconoce pero no cuantifica cuenta hoy como resto entero;
  podría contar como resto parcial.
- ~~**Φ no se persiste.**~~ Resuelto: `tic.acoplamiento` guarda el objeto
  entero —componentes y traza incluidas— junto a `tic.skill_version`, que es
  lo que permite auditar un Φ de hace meses en vez de sólo recalcularlo con
  el protocolo de hoy. Ver `VEREDICTO.md` §8. Era el requisito de la fase 3.

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
