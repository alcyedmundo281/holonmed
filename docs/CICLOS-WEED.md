# Inyectar a Weed, ciclo a ciclo

Lawrence Weed dividió la acción médica en cuatro fases —base de datos, lista de
problemas, plan por problema, notas de evolución tituladas y numeradas— y
sostuvo que la calidad del registro **es** la calidad de la práctica, no su
reflejo.

HolonMed implementa hoy la tercera y la cuarta a medias, y **no implementa la
primera en absoluto**. Este documento es el plan para cerrarlo.

## La tesis

Antes de cualquier ciclo, lo que ordena todos:

> **No queremos que un modelo de lenguaje trate a un paciente. Queremos que
> la práctica clínica sea perfecta.**

HolonMed no es un clínico ni aspira a serlo. Es el sistema minucioso y
ordenado que Weed pedía y que nunca tuvo: el que impide que la lista de
problemas dependa de quién pasó visita, que una orden se ejecute sin
autorización, que un hallazgo entre en la historia sin poder defenderse, o
que una hipótesis siga en pie cuando el paciente ya la contradice.

De ahí se sigue todo lo demás, y en particular la regla que puede parecer
una concesión burocrática y no lo es: **el sistema propone, la persona
firma**. Un sistema que decidiera sería otro clínico —falible, y encima
opaco—. Un sistema que no deja decidir mal es otra cosa.

Es también lo que mantiene a HolonMed del lado correcto de la línea
regulatoria. Ver [`DISCLAIMER.md`](../DISCLAIMER.md).

## El octavo actor: HolonMed

`origen` tenía siete actores y ninguno era el sistema. Pero HolonMed
produce documentos —sobre todo notas clínicas, que son síntesis periódicas
del holón y trabajo suyo, no del clínico—.

Que sea un actor **con nombre propio** y no un `otro` disfrazado es la
condición de la partida doble del ciclo 16: si lo que redacta el sistema
entrara bajo el origen de la consulta, los dos libros se habrían fundido en
uno y la discrepancia —que es el producto— dejaría de existir.

**Autor no es firmante.** Lo que HolonMed redacta es un borrador hasta que
una persona nombrada lo firma.

## Los fundamentos

Tres commitments que no son ciclos: son la forma del sistema, y todo ciclo
que los contradiga está mal aunque pase las pruebas.

### El tiempo es discreto

Para HolonMed el tiempo no es continuo: es **tic, tic, tic**. Nada cambia
entre tics. El estado en el tic *n* es recomputable desde los tics 1..*n*,
que es exactamente lo que `skill_version` existía para permitir —«convierte
recomputar en auditar»—.

De ahí una consecuencia de notación que conviene decir: `dΦ/dt` **no es una
derivada**. Es la diferencia entre dos tics consecutivos, y así está
implementado — `duda.py` no lee el reloj en ninguna línea, compara contra el
tic anterior.

### Potencia y acto

En cada tic, **lo potencial es validado por el médico y se vuelve presente
real**. Lo que el sistema propone es potencia; el acto es humano.

Esto obliga a distinguir dos cosas que hoy están fundidas en `EstadoInfon`:
`VALIDADO` significa hoy «el validador del sistema lo confirmó», que es
juicio de la máquina. Bajo este principio eso sigue siendo **potencial**
hasta que alguien lo actualiza. Es la misma forma que ya tienen
`solicitante` y `prescriptor`: el juicio del sistema y la ratificación
humana nunca comparten campo.

### El bucle

```
tic real ──genera──► tic potencial ──acepta │ corrige │ valida──► nuevo tic real ──►
```

Del tic real sale el siguiente tic potencial, **sobre la base de lo que el
médico aprobó**. No se propone sobre lo que el sistema cree, sino sobre lo
que quedó actualizado.

**«Corrige» no es un tercer botón, es el producto.** Aceptar o rechazar
mide poco; la corrección dice en qué se equivocó el sistema y cuánto. Es la
discrepancia de la partida doble, y tiene la misma forma que
`triaje_coincide`: se registra aunque no decida nada, porque sin ella la
medida que justificaría hacerle caso al sistema no existe.

### El holon es anidado

Y aquí el nombre se redime. Un holon, en Koestler, es un todo que es parte
de un todo mayor:

```
infones            componen ──►  historia clínica   holon PRIMARIO
+ historia         componen ──►  notas clínicas     holones SECUNDARIOS
+ todo lo anterior componen ──►  epicrisis          holon FINAL
```

Hoy `HolonPaciente` tiene **un solo nivel**: la historia entera creciendo
por absorción de infones, sin jerarquía. Que un holon se componga de
holones y no sólo de infones es estructura que falta, y es la misma escalera
que el episodio del ciclo 17 ya ordena en el tiempo.

## Lo que hoy no es cierto

| Fase de Weed | Estado |
|---|---|
| 1 — base de datos **definida**, obtenida siempre | **no existe**: `antecedentes: str = ""` |
| 2 — lista de problemas al día | a medias: `/problemas` y `promocion.py` |
| 3 — plan por problema | a medias: `orden` existe, pero no cuelga del problema |
| 4 — notas tituladas y numeradas | a medias: hay tics, no llevan tipo ni problema |

Y una advertencia suya que gobierna el orden de todo lo que sigue: **no se
automatiza el caos, primero se endereza**. Construir la entrada antes de definir
la base sería exactamente eso.

## El vocabulario, fijado

Se acordó en la conversación que originó este plan, y conviene dejarlo escrito
porque hubo colisión con el código:

- **`Infon`** es y sigue siendo el átomo de verdad: una afirmación clínica
  validada y trazable. **No** es una nota de evolución. Una nota contiene muchos
  infones. El nombre viene de la semántica de situaciones de Barwise y Perry,
  donde un infón *es* un ítem atómico de información.
- **`Holon`** es la historia clínica entera, que crece por absorción. La **nota
  clínica no es otro documento**: es el holón revelado en un instante, con fecha
  y firma.
- **La nota** —base, evolución o clínica— es lo que no tenía nombre. Es un `tic`
  con un `tipo`.

## Los tres ejes que estaban fundidos

```
tipo         ¿qué clase de documento es?   base · evolucion · clinica
origen       ¿quién lo produjo?            consulta · laboratorio · … · paciente
solicitante  ¿quién pidió este dato?       medico · acoplamiento · bayes · promocion
```

---

## Ciclo 8 — Los tres ejes

**Por qué.** `origen` hacía tres trabajos a la vez, y por eso una nota clínica y
un resultado de laboratorio se leían igual.

- `TipoNota` en el tic, con su migración y su defecto `evolucion`.
- `OrigenTic.PACIENTE`. Los cinco actores anteriores eran todos del centro
  sanitario; Weed sostiene que el paciente es quien más variables conoce de su
  propio cuadro.
- `Solicitante` y `motivo` en la orden. No sustituyen a `prescriptor`: lo
  acompañan. Φ y Bayes **originan**, la persona **firma**.

**Condición de hecho.** El tipo y el origen sobreviven al viaje a SQLite, una
base anterior se migra sin perder tics, y el contrato con el frontend declara
exactamente lo que el backend manda.

## Ciclo 9 — La base definida

**Por qué.** Es la fase 1 de Weed y la que hoy no existe. Su argumento: la lista
de problemas es un artefacto de la base, así que sin definirla la lista depende
de dónde se formó quien preguntó y de cuántos ingresos hubo anoche.

- Esquema declarativo de la base, al estilo de las skills: qué se pregunta
  siempre, qué se explora siempre, qué laboratorio por grupo de edad.
- **Base mínima** para atención episódica, declarada aparte y no como excepción
  informal.
- El determinismo vive en el código: es un esquema que se prueba, no una
  instrucción en un prompt.
- La entrada **no la teclea el médico**. La solución de Weed para esta fase es
  cuestionario con lógica de ramificación, personal de enfermería entrenado y
  verificado, y el propio paciente.

**Condición de hecho.** Una base incompleta se detiene y dice qué falta; no se
completa con un valor por defecto razonable.

## Ciclo 10 — El laboratorio solicitado, y la serendipia

**Por qué.** No todo lo que el laboratorio reporta es evidencia. Sólo lo que
alguien pidió responde a una pregunta; lo demás **abre** una.

```
resultado CON orden  → evidencia de la hipótesis que lo pidió
resultado SIN orden  → infón igual, pero problema NUEVO en la lista
```

Lo segundo es Weed literal: cuando aparece un problema nuevo va a la lista. Su
queja en el Grand Rounds era encontrar rastros de problemas que nadie había
listado.

Nada se descarta. Lo que cambia es **de qué es evidencia**.

**Condición de hecho.** Un resultado no solicitado nunca mueve Φ ni Bayes de la
hipótesis activa, y nunca desaparece en silencio.

## Ciclo 11 — Las bandas: el valor deja de ser binario

**Por qué.** Hoy el umbral está congelado en el nombre del signo
—`Hiperlipasemia (>3x)`— así que una lipasa de 3.1x y una de 20x son el mismo
infón y el mismo cociente. Eso es falso.

Y no se arregla con rangos de referencia en el analito: eso devolvería por la
puerta de atrás la interpretación fuera de hipótesis que
`_sin_cortes_inventados()` le quitó al modelo. **El umbral es propiedad del par
(analito, hipótesis), y es graduado.**

```yaml
- analito: Potasio sérico
  rol: prueba_especifica
  bandas:
    - { desde: 5.5, hasta: 6.5, lr: 3.2, fuente: ... }
    - { desde: 6.5,             lr: 9.0, fuente: ... }
```

El mismo potasio aparece en otro protocolo con bandas por abajo y dirección
contraria. Ninguno necesita un «rango normal», y por eso el mismo número puede
empujar dos hipótesis en sentidos opuestos.

**Precondición.** El formato de los protocolos vive en `medsemiotics-db`. Las
bandas se acuerdan allí antes de leerlas aquí.

**Condición de hecho.** Un signo sin bandas sigue siendo válido —es una banda
única—, así que los nueve protocolos actuales no se rompen. Y un valor que
ninguna hipótesis conocida lee **se dice**, no se calla.

## Ciclo 12 — La tupla como control de flujo

**Por qué.** SnNOut y SpPIn no son sólo una compuerta de promoción: dicen qué
pedir a continuación.

```
sensible NEGATIVA   descarta ESA hipótesis. No se pide la específica.
                    El paciente sigue con su problema → vuelve a la abducción,
                    que es «dirección baja» en duda.py.

sensible POSITIVA   no confirma → propone la específica, por el portón
                    proponer/autorizar, con solicitante = promocion.
```

Una sensible negativa **no cierra la indagación: cierra una línea y abre otra**.

**Condición de hecho.** Ninguna propuesta se convierte en orden sin firma.

## Ciclo 13 — El holon de background, y su impresión

Esto era dos ciclos —«`resumen_vivo` vivo» y «la nota clínica firmada»— y
son **dos estados de un mismo mecanismo**. Separarlos habría llevado a
construir dos cosas que luego había que reconciliar.

### El background

Después de que el médico valida cada infón, HolonMed genera **en cada tic**
un holon secundario que incorpora los nuevos infones. Corre por debajo, no
se imprime, y por eso puede estar siempre al día sin molestar a nadie.

Esa es la condensación mantenida que el argumento de capacidad de Weed
justifica: la lista de problemas y la hoja de flujo se mantienen, no se
archivan por fechas. `resumen_vivo` era el hueco declarado para esto desde
el primer día, y nunca lo escribió nadie.

**No lleva fecha ni firma.** No afirma el estado del paciente en un
instante: afirma el estado *ahora*, y se reescribe.

### La impresión

Cuando las cosas cambian, ese holon de background **se imprime en el
presente real**, para que el médico actualice su conocimiento clínico del
paciente. La impresión es el evento, y lo que se imprime es un documento de
verdad: `clínica-N`, con su ordinal, su fecha y su firma.

Qué cuenta como «las cosas cambian»:

- **Cambio en la lista de problemas** — el disparo de Weed, y el que el
  sistema ya sabe calcular: `promocion.py` cuando un problema pasa a
  diagnóstico, `duda.py` cuando el argumento deja de sostenerse.
- **Volumen**, como válvula secundaria. Y cuando dispara el volumen **la
  nota lo dice**: esta síntesis la pidió el tamaño, no el paciente. Que se
  note la diferencia es la mitad del valor.

Weed sobre las notas escritas el domingo por la mañana: una nota cuyo sello
de tiempo no corresponde a un evento es ficción, no ciencia. El background
no tiene sello, así que no puede mentir; la impresión sí lo tiene, y por eso
tiene que corresponder a algo.

### Y va por problema

Es la queja central de Weed y **lo más recurrente que HolonMed hace**:
«doing well» no significa nada en un paciente con artritis, insuficiencia
cardíaca, azotemia, cadera rota e infección de oído. Cada problema lleva su
punto de vista del paciente, su dato objetivo y su siguiente paso.

Es justo el trabajo en el que los médicos fallan y en el que una máquina
minuciosa es buena.

**Condición de hecho.** El background nunca está obsoleto respecto del
último tic. Nada se imprime sin firma. Y una nota impresa dice si la pidió
el paciente o el tamaño.

## Ciclo 15 — La interfaz por la que entra todo

**Por qué.** Los tipos existen desde el ciclo 8 y no hay por dónde
producirlos. Hoy todo entra como texto suelto por un chat.

La serie completa de un episodio son cinco documentos:

```
historia clínica          la base. Fase 1 de Weed.
primera nota clínica      el holón, revelado por primera vez
notas de evolución        el grueso del tráfico
notas clínicas intermedias  el holón, revelado otra vez
epicrisis                 cierra el episodio, y sale de la institución
```

La primera nota clínica y las intermedias son el **mismo tipo**: su
diferencia es de posición, y la posición se lee del orden. La epicrisis es
el único que sale de la institución, y por eso es el único bajo aprobación
humana nombrada obligatoria.

**La historia clínica no la teclea el médico.** Es la solución de Weed para
la fase 1, y la interfaz tiene que reflejarla: cuestionario con lógica de
ramificación, enfermería entrenada, y el propio paciente. Un formulario
libre para el médico sería automatizar el caos.

**Condición de hecho.** Ningún documento se emite sin tipo, y la epicrisis
no se emite sin firma.

## Ciclo 16 — La partida doble

**Por qué.** Weed sostiene que la medicina es un negocio de billones **sin
sistema contable**, y que sin poder auditar la calidad no hay medio de
producirla. La partida doble es lo que hace que una discrepancia sea
estructuralmente visible: no se puede maquillar un libro sin que el otro lo
delate.

HolonMed lleva su propio libro por debajo del que lleva el clínico, sobre
todo lo que llegó —incluido lo que nadie anotó—. La conciliación entre los
dos tiene tres resultados, y es la misma forma que `conciliacion.py` ya usa
para órdenes y ejecuciones:

| Situación | Qué significa |
|---|---|
| HolonMed lo vio, el clínico no lo escribió | **problema pasado por alto** |
| El clínico lo escribió, HolonMed no lo vio | fallo de cobertura del índice |
| Los dos | concuerda |

El primero es medible y Weed lo midió: en la sala de urgencias, con un
cuestionario de 32 preguntas y personal paramédico, los médicos se estaban
dejando **5.2 problemas por paciente**. Esa cifra hoy no la produce nadie.

**HolonMed no escribe en el expediente.** Lo que encontró y el clínico no
anotó entra en su propio libro y se **propone**, por el mismo portón
proponer/autorizar que ya existe para las órdenes.

Y esto no es una limitación que el contrato impone a regañadientes: **es lo
que hace que la partida doble funcione**. Si el sistema fundiera en
silencio sus hallazgos con el registro del clínico habría otra vez un solo
libro, y la discrepancia —que es el producto— desaparecería. Los dos libros
tienen que quedarse separados para que haya algo que conciliar.

**Condición de hecho.** La tasa de discrepancia se puede consultar y
agregar, como `acuerdo_del_triaje()` hace con el triaje. Un hallazgo del
sistema nunca aparece en el registro del clínico sin una firma.

## Ciclo 17 — El episodio

**Por qué.** La secuencia canónica de un episodio es ésta:

```
historia clínica
  evolución … evolución …
clínica-1
  evolución … evolución …
clínica-2
  evolución … evolución …
clínica-XX
  evolución … evolución …
epicrisis
```

Tres cosas se siguen de la forma, y ninguna se sostiene hoy:

1. **Las notas clínicas van numeradas.** No es decoración: Weed pide notas
   tituladas y numeradas, y `clínica-2` sólo significa algo respecto de
   `clínica-1`. El ordinal es por episodio.
2. **La primera nota clínica no sigue a la historia.** Entre las dos hay
   evoluciones, y la clínica-1 las sintetiza. La nota clínica nace de lo
   acumulado, no de la apertura.
3. **El episodio tiene principio y fin declarados.** La historia clínica lo
   abre, la epicrisis lo cierra, y ambos ocurren exactamente una vez.

**Y no existe.** Las tablas son `paciente`, `tic`, `infon`, `orden`… y todo
cuelga de `paciente_id`. Un paciente con tres ingresos es hoy un único
flujo continuo: `clínica-1` sería ambigua entre ellos y la epicrisis no
tendría qué cerrar.

**Condición de hecho.** Un episodio no admite dos historias clínicas ni dos
epicrisis, el ordinal de una nota clínica es único dentro de él, y la
historia ya escrita —que no tiene episodios— se migra a uno sin perder un
tic.

## Ciclo 18 — La procedencia de un infón

**Por qué.** Weed pide la nota escrita «sintomáticamente y objetivamente»,
en ese orden. Esa separación no es de estilo: es de procedencia, y sin
registrarla la nota mezcla lo que alguien contó con lo que alguien comprobó.

```
subjetivo   lo expresó el paciente
objetivo    lo observó el clínico, o lo midió quien informa
derivado    no lo aseveró nadie: se sigue de otros infones
```

**Lo que clasifica es quién asevera, no el instrumento.** Una glucemia que
el paciente refiere es subjetiva aunque salga de un glucómetro: nadie vio el
aparato, ni la lectura, ni si estaba calibrado.

La consecuencia es la que da valor a la regla: **un valor referido no puede
compararse contra un punto de corte como si se hubiera medido**.

**Condición de hecho.** El eje es del infón y no del tic, porque una nota de
consulta lleva las dos clases en el mismo párrafo. Y un origen que no
declara qué produce no recibe ninguna procedencia.

## Ciclo 19 — Potencia y acto

**Por qué.** `EstadoInfon.VALIDADO` significa hoy «el validador del sistema
lo confirmó». Eso es juicio de la máquina, y bajo el principio de potencia y
acto sigue siendo potencial hasta que un médico lo actualiza.

- Un eje nuevo, separado del veredicto del validador: quién lo actualizó y
  cuándo. Sin él, «validado» dice dos cosas distintas según quién lea.
- El tic potencial se genera **sobre lo aprobado**, no sobre lo que el
  sistema cree.
- **Aceptar, corregir o validar**, y la corrección se registra con lo que
  cambió. Es la medida de cuánto se equivoca el sistema, y sin registrarla
  no existe.

**Condición de hecho.** Un infón que ningún humano actualizó nunca se
presenta como real. Y la tasa de corrección se puede agregar, como
`acuerdo_del_triaje()`.

## Ciclo 20 — El holon anidado

**Por qué.** `HolonPaciente` tiene un solo nivel. La historia clínica es el
holon primario, las notas clínicas son secundarios y la epicrisis es el
final; hoy los tres son el mismo objeto plano.

- Un holon referencia los holones que lo componen, no sólo sus infones.
- La escalera coincide con la secuencia del episodio, que el ciclo 17 ya
  ordena en el tiempo: es la misma estructura vista desde la composición en
  vez de desde el orden.

**Condición de hecho.** Reconstruir la epicrisis desde sus holones da lo
mismo que reconstruirla desde los infones de todo el episodio, y si no da lo
mismo el sistema lo dice en vez de elegir uno.

## Lo que este plan NO cubre

Los tres requisitos que [`AGENTS.md`](../AGENTS.md) declara vigentes y sin
implementar —auditoría append-only que incluya lecturas, tabla de política, y la
aprobación humana nombrada como mecanismo general— son anteriores a esto y no se
resuelven aquí. El ciclo 14 **usa** la aprobación; no la construye.

## Cómo se ejecuta

Un ciclo por rama, un PR por ciclo, CI en verde antes de fusionar.

El orden no es una fila india sino un grafo de dependencias, y conviene decirlo
con precisión para no serializar de más:

```
HECHOS      8 · 9 · 17 · 18 · 19 · 20

8  ──► 9 ──► 10 ──► 11 ──► 12
9 + 17 ──► 15   la interfaz: sin base no hay qué pedir, y sin episodio la
                nota clínica no se puede numerar
10 ──► 16       la partida doble concilia lo que el laboratorio trajo
19 + 20 ──► 13  el holon de background necesita la escalera (20) y saber qué
                está ratificado (19), porque se genera TRAS la validación
```

Lo que sí es firme: ningún ciclo empieza con su dependencia fuera de `main`.
Dos ciclos que tocan el mismo esquema en paralelo garantizan el conflicto, y el
ciclo 8 ya dejó la lección —la epicrisis entró antes de fusionar justo para no
migrar dos veces la misma columna.
