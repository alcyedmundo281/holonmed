# Los tres niveles de la decisión: vetar, contar, balancear

**Criterios publicados en HolonMed.**
Módulo: `backend/holonmed/core/veredicto.py` · Tests: `backend/tests/test_veredicto.py`
Complementa `docs/ACOPLAMIENTO.md`, que documenta Φ.

---

## 1. La pregunta que faltaba

El sistema sabía responder a dos preguntas y no a una tercera.

- **¿Cuánta evidencia hay?** La responde el motor bayesiano, con la
  probabilidad posterior y su traza.
- **¿Armoniza con este paciente?** La responde Φ, midiendo la dirección del
  mismo vector cuya magnitud lee Bayes.
- **¿Es siquiera posible?** No la respondía nadie.

Un paciente apendicectomizado con dolor en fosa ilíaca derecha, fiebre y
leucocitosis produce una probabilidad de apendicitis perfectamente calculada
y perfectamente inútil. Ninguna cantidad de evidencia hace posible una
apendicitis sin apéndice, y sin embargo el sistema no tenía forma de decirlo.

A esto se añade que los criterios que la clínica usa a diario **no deciden
con una probabilidad: deciden contando**. Atlanta cuenta dos de tres. MDS
cuenta apoyos contra banderas rojas. El sistema tampoco sabía aplicarlos.

---

## 2. La forma viene de un criterio publicado

Los criterios MDS 2015 para la enfermedad de Parkinson (Postuma RB et al,
*Mov Disord* 2015;30(12):1591-601, doi:10.1002/mds.26424) separan
explícitamente tres cosas que un sistema de apoyo tiende a fundir en una:

- **Criterios de exclusión absoluta** — descartan. No se contrarrestan con
  nada.
- **Banderas rojas** — restan, pero **sí** se contrarrestan con criterios de
  apoyo, uno por uno y hasta un tope.
- **Criterios de apoyo** — suman confianza.

Más un **núcleo** previo —parkinsonismo motor: bradicinesia con temblor de
reposo o rigidez— sin el cual el criterio ni siquiera se aplica. Y dos grados
de certeza: *establecida*, que maximiza especificidad, y *probable*, que
equilibra.

No se inventó una taxonomía: se adoptó una publicada y validada.

---

## 3. Por qué son tres mecanismos y no uno

Los tres parecen la misma cosa con distinto signo. No lo son, y la diferencia
se midió antes de codificarla.

### La exclusión no es un likelihood ratio

Un cociente de 0.001 deja una probabilidad pequeña pero **distinta de cero**,
y ninguna evidencia posterior la lleva a cero. Un paciente apendicectomizado
no tiene poca probabilidad de apendicitis: no puede tenerla. Es una
imposibilidad estructural, no una improbabilidad.

Por eso la exclusión vive **fuera** de Bayes y **fuera** de Φ, y por eso el
veto se aplica antes que ninguno de los dos: calcular la probabilidad de una
apendicitis en un paciente sin apéndice no es conservador, es ruido con
formato numérico.

### El tope de banderas tampoco es un balance

Un coseno es continuo y monótono en el balance entre lo que apoya y lo que
resta, de modo que **no puede expresar un corte**. Con los enteros de MDS,
cuatro apoyos y tres banderas queda rechazado por el criterio y da Φ
**positiva**, por encima de casos que el criterio acepta.

El tope se comporta como una exclusión contada, y así se trata.

### El balance sí es continuo

Y ahí Φ hace mejor trabajo que el conteo: pondera por `ln(LR)` donde hay
cociente publicado, en vez de contar cada signo como uno. Un panel de
expertos no puede multiplicar logaritmos a mano; este módulo sí.

---

## 4. El orden, que no se explica solo

```
exclusión absoluta  →  núcleo  →  tope de banderas  →  balance
```

**Este orden no es arbitrario y una versión anterior lo tenía mal.** El tope
de banderas se evaluaba antes que el núcleo, y MDS dicta lo contrario:
primero se documenta el parkinsonismo motor, y **sólo después** se determina
si la causa es la enfermedad de Parkinson.

La distinción fina:

- Una **exclusión absoluta sí precede a todo**. Una apendicectomía excluye la
  apendicitis se haya documentado lo que se haya documentado.
- El **tope de banderas no**, porque es una propiedad de la tabla de balance
  — y el núcleo es justamente lo que condiciona que esa tabla se aplique.

Con el orden invertido, un paciente sin núcleo documentado y con tres
banderas salía vetado por tope cuando debía salir con «el criterio no se
aplica todavía». Son mensajes clínicos distintos: uno dice que el diagnóstico
está descartado, el otro que la pregunta aún no cabe hacerse.

**Queda escrito para que nadie lo «simplifique» devolviéndolo al original.**

---

## 5. Dos reglas que parecen detalles y no lo son

### Un nivel se sostiene sobre lo que dispara, no sobre lo que consta

El agujero apareció dos veces, por dos puertas distintas.

La primera: sin núcleo, un balance que admite «cero apoyos mínimos» daba por
**probable** un diagnóstico en un paciente del que no consta absolutamente
nada, porque cero apoyos cumplen cero mínimos. Lo tapó el núcleo.

La segunda: el núcleo es **opcional**, y bastaba un signo emparejado que no
activara su efecto —un `dispara_si: ausente` que constara presente— para que
la lista de observados dejara de estar vacía con cero apoyos y cero banderas.
El nivel volvía a alcanzarse sobre nada.

La regla, en una frase: **un nivel se sostiene sobre lo que dispara, no sobre
lo que consta.** Es lo que impide que vuelva por una tercera puerta.

### `Nucleo.satisfecho(empareja)` recibe una función a propósito

Es una firma rara, y sin conocer lo que evita parece un rodeo. Recibe el
emparejador en vez de un conjunto de cadenas porque **el núcleo tiene que
casar igual que todo lo demás**: por subcadena, con `bayes.emparejar_termino`.

La primera versión comparaba por igualdad exacta, y entonces un infón
«Bradicinesia leve» satisfacía un signo y **no** el núcleo. Es exactamente la
divergencia silenciosa que la **§3.3 de `ACOPLAMIENTO.md`** existe para
impedir —la sección que insiste en que el emparejamiento viva en una sola
función compartida— y ocurrió dentro del módulo que la cita.

Es el segundo caso del mismo fallo. Si aparece un tercero, el sitio donde
mirar es esa sección.

---

## 6. El esquema, y qué garantiza la compatibilidad

```yaml
nucleo:
  requiere: [Bradicinesia]                    # todos
  y_al_menos_uno_de: [Temblor de reposo, Rigidez]

signos:
  - nombre: Apendicectomía
    efecto: excluye              # apoya | bandera_roja | excluye
    dispara_si: presente         # presente | ausente
  - nombre: Dolor en fosa ilíaca derecha
    efecto: bandera_roja
    dispara_si: ausente          # la AUSENCIA documentada es la bandera
  - nombre: Fiebre
    efecto: apoya

balance:
  fuente: "Postuma RB et al, Mov Disord 2015;30:1591-601"
  establecida: {apoyos_minimos: 2, banderas_maximas: 0}
  probable:    {contrapeso: 1, banderas_maximas: 2}
```

Todo opcional. `efecto` por defecto es `apoya` y `dispara_si` es `presente`.
Y **sin ningún `efecto` distinto de `apoya` y sin `balance`**, el evaluador
devuelve `None` —que no es lo mismo que un veredicto vacío: uno dice que el
criterio no se cumple, el otro que no hay criterio que aplicar.

Nótese qué **no** entra en esa guarda. El núcleo por sí solo no activa nada:
un protocolo que declare `nucleo` y nada más devuelve `None`. Y una exclusión
sí activa, aunque no haya `balance` declarado — el caso de la apendicectomía
funciona con **una sola arista `efecto: excluye`**, sin tabla de conteo.

**La compatibilidad hacia atrás no es una promesa, la comprueba CI.** El paso
«Los protocolos anclan lo que acuñan» corre los seis protocolos del
repositorio en cada commit, y ninguno declara las claves nuevas.

---

## 7. Los enteros son de MDS, no del sistema

`apoyos_minimos`, `contrapeso` y `banderas_maximas` **no son un umbral de
HolonMed**. Los fija el panel que redacta el criterio publicado y llegan con
su cita. El «al menos dos apoyos» y el «máximo dos banderas» son de MDS 2015
y de nadie más; otra enfermedad traerá otros números o ninguno.

Esto se dice porque se aprendió por el camino difícil. Un estudio previo
intentó **derivar** un umbral universal por simulación, y falló por un error
de categoría: el umbral es específico de la enfermedad. Buscarlo con
matemáticas era buscar algo que la disciplina ya fija y publica.

**Si alguna vez este documento lleva cifras propias, deben ir con la muestra
sobre la que se midieron.**

---

## 8. Persistencia: cerrada

Esta sección declaraba la limitación más urgente del módulo. Ya no lo es: la
tabla `tic` registra el razonamiento entero, y lo que sigue queda escrito
porque el argumento de por qué hacía falta no ha caducado.

### 8.1 Lo que se guarda, y por qué cada cosa

```sql
skill              TEXT NOT NULL,
skill_version      TEXT,          -- la versión, junto al nombre
inferencia         TEXT,          -- JSON: la probabilidad
acoplamiento       TEXT,          -- JSON: Φ, con componentes y traza
veredicto          TEXT,          -- JSON: el criterio publicado, contado
competencia        TEXT,          -- JSON: la lista entera de candidatas
ganadora_abductiva TEXT,
triaje_coincide    INTEGER,       -- 1, 0 o NULL, y los tres son distintos
aviso_competencia  TEXT
```

**`veredicto` era la urgente.** El sistema promete que una hipótesis vetada se
descarta con su motivo visible, para que el próximo clínico no rehaga el
razonamiento. Sin la columna, esa promesa duraba lo que la sesión.

**`skill_version` es la que convierte recomputar en auditar.** Los infones se
persisten completos, así que el veredicto siempre fue *recomputable* — pero
recomputar sin la versión da *el protocolo de hoy aplicado a los infones de
aquel día*. Si alguien añadió una exclusión desde entonces, el veto
recomputado no es el que se le mostró al clínico. **Recomputable no es lo
mismo que registrado.**

**`competencia` guarda a las perdedoras a propósito.** «Se consideró
diverticulitis y sacó 0.25» *es* la traza: sin ella el sistema muestra una
conclusión sin poder decir contra qué compitió. Y `aviso_competencia` guarda
la vez que la compuerta de α actuó, porque una compuerta callada hace que el
sistema trate otra cosa sin dejar constancia del motivo.

### 8.2 Los tres estados de `triaje_coincide`

```
1      el grafo eligió lo mismo que el prompt
0      eligieron distinto
NULL   no hubo competencia con la que comparar
```

`NULL` no es un 0. Aparece cuando el grafo no propuso candidatas —sin infones
validados, o sin protocolo que cubra sus conceptos— y meterlo en el
denominador diría que el prompt falló donde nadie le llevó la contraria. Es
una tasa de error inventada, y es la misma distinción que gobierna
`SIN_MEDIR` en `ACOPLAMIENTO.md` y `Historia.sin_ubicar`: no es ausencia, es
vacío.

`TicRepo.acuerdo_del_triaje()` los devuelve en su propia clave, y da
`acuerdo: None` —no `0.0`— cuando no hay nada comparable.

### 8.3 Lo que esto habilita

La competencia abductiva corre en paralelo al triaje desde el ciclo 6, y su
resultado era una línea de log por tic: legible sólo por quien mirase la
consola en ese momento. Agregado sobre el histórico es la medida que el paso
faltaba producir —**cuánto se equivoca el prompt**— y que es lo que hay que
saber antes de sustituirlo por nada.

Las columnas están fijadas por tests que caen bajo mutación: guardar sólo la
ganadora, omitir la versión, colapsar `NULL` a 0 al escribir, meter los `NULL`
en el denominador, o devolver `0.0` en vez de `None` — cada una tira al menos
un test.

---

## 9. Otras limitaciones conocidas

- **El conversor no emite estos bloques todavía.** Las tres tablas deben
  nacer en `medsemiotics-db`, validadas contra PubMed, y el eje `efecto` está
  aprobado pero sin abrir. Este módulo define el contrato que el conversor
  tendrá que cumplir.
- **Ningún protocolo del repositorio los declara aún.** Todo lo verificado
  corre sobre protocolos de prueba; el primer caso real será apendicitis o
  intestino irritable, cuando el índice los tenga.
- **El emparejamiento es por subcadena**, heredado del motor bayesiano con su
  limitación conocida, y heredado a propósito (§5).
- **Un signo cuenta una vez**, aunque varios infones emparejen con él. Es la
  misma regla que Φ aplica y que Bayes no — ver `ACOPLAMIENTO.md` §3.3,
  condición 3.
- **Sólo entra evidencia VALIDADA.** Un hallazgo en ALERTA se le muestra al
  clínico pero no veta un diagnóstico ni satisface un criterio. La dirección
  del error importa: un falso positivo en una exclusión retira una
  apendicitis a quien la tiene.

---

## 10. Qué responde cada pieza

Las tres respuestas son a preguntas distintas, y **ninguna finge ser las
otras dos**:

| pregunta | pieza | salida |
|---|---|---|
| ¿cuánta evidencia hay? | motor bayesiano | probabilidad posterior con su traza |
| ¿armoniza con este paciente? | Φ | coeficiente en [−1, +1] y el resto no simbolizado |
| ¿es posible, y qué dice el criterio? | veredicto declarado | veto con su motivo, o el grado de certeza alcanzado |

Se leen **juntas y por separado**. Cuando el criterio contado y la aritmética
discrepan, esa discrepancia es información clínica; fundirlas en un número la
destruiría.
