# HolonMed v0.5.0

La versión en la que el sistema deja de contestar sólo *cuánta* evidencia
hay y empieza a contestar *si el argumento se sostiene* — y, cuando no se
sostiene, por qué y hacia dónde ir.

Bayes suma, y una suma pierde información sobre sus sumandos. Dos historias
pueden dar el mismo posterior siendo cosas clínicamente distintas: en una,
todo apunta al mismo sitio y nada del paciente queda sin explicar; en otra,
una única prueba muy específica arrastra la probabilidad mientras cuatro
hallazgos hablan de otra enfermedad. La segunda tiene nombre —**sesgo de
anclaje**— y un sistema que sólo muestre la probabilidad no protege de ese
error: **lo autoriza con un número**.

Todo lo que sigue nace de ahí.

## Φ, y por qué hubo que partirlo en tres

El Coeficiente de Acoplamiento mide la dimensión que la probabilidad no ve:
si la hipótesis, **tomada como regla de acción**, armoniza con el paciente
entero. Φ = α · cos(h, e), donde α es el anclaje documental del protocolo y
el coseno es el acoplamiento entre lo que la hipótesis afirma y lo que el
paciente presenta.

Pero un coseno fundido dice que la creencia no funciona y no dice por qué.
Partirlo es lo que convierte una alarma en una instrucción:

```
cos = dirección · √(cobertura · explicación)
```

| Factor | Qué mide | Qué significa que esté bajo |
|--------|----------|-----------------------------|
| **dirección** | de lo mirado, cuánto concuerda | lo que se miró **disiente** |
| **cobertura** | de lo que la hipótesis afirma, cuánto se puso a prueba | la hipótesis está **sin comprobar** |
| **explicación** | de lo que el paciente tiene, cuánto cae dentro | la hipótesis **no explica al paciente** |

Los tres factores se exponen también en la lectura categórica, para los
protocolos que no declaran likelihood ratios. Antes, el Φ categórico era
ciego al resto no simbolizado, que es justo donde vive el anclaje.

## dΦ/dt: la duda es un movimiento, no una foto

`Acoplamiento.duda` existía desde el primer día y **nadie la leía**. El
sistema calculaba que su hipótesis había dejado de funcionar como regla de
acción, y seguía adelante sin decirlo.

La duda no es el veto, y la distinción importa: un veto dice que el
diagnóstico es imposible y **termina** la pregunta; una duda dice que el
argumento dejó de sostenerse con lo que hay y la **reabre**. Por eso la
salida no es un recálculo sino algo accionable — preguntas, o una orden de
prueba cuya respuesta llegará en otro tic.

Y aquí es donde se cobra lo de partir el coseno, porque cada porqué manda a
un sitio distinto:

- **dirección baja** → no se arregla mirando más: cada dato que confirme lo
  ya visto la hunde más. Se arregla **cambiando de hipótesis**.
- **cobertura baja** → ésta es la duda que se resuelve **indagando**, y el
  sistema ya calculó por dónde: la dimensión donde la hipótesis hace su
  afirmación más fuerte y nadie ha mirado todavía.
- **explicación baja** → la hipótesis puede ser cierta y ser irrelevante.
  Es la forma que toma el sesgo de anclaje, y se resuelve **volviendo a la
  abducción**.

## La competencia abductiva, y por qué viene apagada

La etapa que se llamaba «inferencia abductiva» era Bayes, y Bayes no genera
hipótesis: pesa una que ya alguien eligió. La abducción real ocurría en el
triaje —un prompt— y de él colgaba todo lo demás: la validación de tres
capas, el veto, los cocientes con su cita y el coseno. Era **la pieza menos
medida del sistema, en el sitio más temprano**.

Peirce lo llamaría abducción: *se observa el hecho sorprendente C; si A
fuera verdadera, C sería de curso natural; luego hay razón para sospechar
A*. Un coseno alto es exactamente eso, así que elegir la A que maximiza
cos(h, e) **es** la regla abductiva escrita como argmax — y el grafo del
paciente puede proponer las candidatas sin preguntarle nada al modelo.

El mecanismo está construido y **no está encendido**. `HOLONMED_ABDUCCION_DECIDE`
vale `false` por defecto, y es deliberado: el propio diseño puso una
precondición que hoy no se cumple —«antes de sustituir el prompt por esa
regla hay que saber cuánto se equivoca»— y esa cifra sale del acuerdo del
triaje sobre el histórico, que todavía no existe. Encenderla sin ella sería
cambiar el mecanismo que elige el diagnóstico apoyándose en una intuición,
que es exactamente lo que la competencia existe para evitar.

El interruptor gobierna la forma, no sólo el voto:

```
apagada     una lectura, con el protocolo del triaje. Sin segunda pasada.
encendida   lectura genérica, competencia, relectura con la ganadora.
```

La competencia **mide en los dos modos**. Un interruptor que apagara también
la medida haría imposible justificar nunca el encendido.

## La tupla: cuándo un problema pasa a ser diagnóstico

Weed separó esa pregunta en 1968 y el sistema la tenía fundida con la
probabilidad. Una probabilidad alta no promueve por sí sola: un dato fuerte
puede empujarla al 95 % con el resto del cuadro sin mirar.

Promover exige tres cosas a la vez, y las tres tienen que estar:

| | Rol | |
|---|---|---|
| una clínica positiva | `manifestacion` | |
| una prueba sensible positiva | `prueba_sensible` | SnNOut |
| una prueba específica positiva | `prueba_especifica` | SpPIn |

Exigir la sensible **en positivo** parece redundante junto a la específica y
no lo es: significa que **una sensible negativa impide la promoción**. Es
SnNOut usado como compuerta.

## Conocimiento nuevo

Cuatro protocolos, traídos del índice `medsemiotics-db` con el conversor:
**síndrome coronario agudo**, **embarazo ectópico**, **conjuntivitis
bacteriana** y **apnea obstructiva del sueño**.

El vocabulario semilla pasa de **1.3.0 con 136 conceptos** a **1.6.0 con
209**. Y los protocolos ahora se validan también por lo que **acuñan**, no
sólo por lo que consumen: un código colgado en la condición que representa
o en el término que su clasificación acuña no fallaba, emitía el
diagnóstico sin linaje ni CIE-10, en silencio. Ahora CI lo caza.

## Las cuatro puertas, y el contrato que las declara

De los cuatro gates que el contrato da por no negociables sólo corrían dos.
Ahora corren los cuatro, en CI y en local:

```bash
ruff check . && ruff format --check . && mypy && pytest -q
```

`AGENTS.md` es el contrato que faltaba, y tiene un apartado incómodo a
propósito: **«Lo que todavía no es cierto»**. La auditoría append-only que
incluya lecturas, la tabla de política y la aprobación humana nombrada son
requisitos vigentes y sin implementar. Escribirlos como si existieran habría
sido la primera mentira del documento.

## Lo que este release no es

No hay ningún cambio que acerque el sistema a emitir una conclusión
directiva. Φ, la duda y la promoción **describen el estado del argumento**;
ninguna decide por nadie, y la competencia abductiva —lo único que podría
cambiar qué hipótesis se persigue— viene apagada.

Sigue sin ser un dispositivo médico. Lee [DISCLAIMER.md](../DISCLAIMER.md).
