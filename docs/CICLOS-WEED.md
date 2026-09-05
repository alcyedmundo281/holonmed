# Inyectar a Weed: siete ciclos

Lawrence Weed dividió la acción médica en cuatro fases —base de datos, lista de
problemas, plan por problema, notas de evolución tituladas y numeradas— y
sostuvo que la calidad del registro **es** la calidad de la práctica, no su
reflejo.

HolonMed implementa hoy la tercera y la cuarta a medias, y **no implementa la
primera en absoluto**. Este documento es el plan para cerrarlo.

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

## Ciclo 13 — `resumen_vivo` vivo

**Por qué.** El campo existe desde el primer día y **nadie lo escribe nunca**. Es
el hueco de la condensación mantenida.

Weed funda el registro en un límite de capacidad —la mente no puede cargar todo
sin error— y ese argumento se traslada entero a una ventana de contexto. Pero lo
que justifica es una **condensación mantenida**, no una serie de instantáneas: la
lista de problemas y la hoja de flujo se mantienen, no se archivan por fechas.

- Se reescribe cuando cambia algo material, y también por volumen.
- No lleva fecha ni firma: no afirma el estado del paciente en un instante.

**Condición de hecho.** Nunca está obsoleto respecto de la última nota.

## Ciclo 14 — La nota clínica firmada

**Por qué.** Es el holón revelado, y es un documento: tiene fecha, autor y firma,
y afirma el estado del paciente en ese instante.

- Nace del **cambio en la lista de problemas**, que es el disparo de Weed.
- El volumen es válvula secundaria, y cuando dispara él **la nota lo dice**: esta
  síntesis la pidió el tamaño, no el paciente.
- Weed sobre las notas escritas el domingo por la mañana: una nota cuyo sello de
  tiempo no corresponde a un evento es ficción, no ciencia.

**Condición de hecho.** Aprobación humana nombrada antes de emitirla.

---

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
8  ──► 9 ──► 10 ──► 11
   └─► 15 (necesita 9: sin base definida no hay qué pedir en la interfaz)
11 ──► 12
10 ──► 16 (la partida doble concilia lo que el laboratorio trajo)
13 ──► 14
```

Lo que sí es firme: ningún ciclo empieza con su dependencia fuera de `main`.
Dos ciclos que tocan el mismo esquema en paralelo garantizan el conflicto, y el
ciclo 8 ya dejó la lección —la epicrisis entró antes de fusionar justo para no
migrar dos veces la misma columna.
