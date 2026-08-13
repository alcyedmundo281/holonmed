# HolonMed v0.4.0

La versión en la que el sistema deja de terminar en el diagnóstico y llega
hasta la cuenta, sin que en ningún punto haya que fiarse de un modelo de
lenguaje.

Tres cosas nuevas, y todas descansan sobre la misma idea: **una orden
médica es un acto de autorización de una persona**. Lo que el modelo hace
es proponer; lo que el código hace es impedir que una propuesta pase por
autorización.

## La facturación empieza en la orden, no en la factura

La cadena no permite saltarse ningún eslabón:

```
plan de la nota ──► ORDEN ──► ejecución del actor ──► cargo
                      ↑                 ↑
                  autoriza       confirma que se hizo
```

`cargo` referencia siempre una `orden`. Sin autorización no hay cargo, y no
porque se lo pidamos amablemente a un modelo en un prompt, sino porque no
existe la fila. La propiedad antifraude es **estructural**.

Eso hace que el módulo se llame `conciliacion` y no `facturador`: factura
como efecto secundario de comprobar que lo ordenado se cumplió. De los tres
resultados de esa comprobación, sólo uno es de dinero:

| Situación | Qué significa |
|-----------|---------------|
| Orden sin ejecución | El paciente no recibió lo prescrito |
| Ejecución sin orden | Administración no autorizada |
| Orden + ejecución | Facturable |

Los dos primeros son incidentes clínicos que hoy se detectan tarde o nunca.
El mismo mecanismo que cuadra la cuenta cuadra la medicación, y de las dos
cosas la segunda importa más.

También cambia *cuándo* se calcula. Las horas de espera al alta no son un
problema de velocidad de proceso sino de arquitectura: la cuenta se
calculaba en bloque al final. Aquí los cargos se acumulan según se
concilian, y consultar la cuenta no recalcula nada.

**Los tarifarios son un vocabulario más.** Se cargan con su `sistema` y su
fecha de vigencia, y el enlace entre concepto clínico y código facturable
usa la misma tabla `mapeo` que SNOMED o CIE-10. No hay mecanismo nuevo:
cada hospital o aseguradora carga el suyo y el resto del sistema no se
entera. Una entrada antigua nunca se sobrescribe, porque una cuenta de hace
un año debe poder reconstruirse con los precios de entonces.

```bash
python scripts/importar_tarifario.py --json tarifario_hospital.json
python scripts/importar_tarifario.py --csv tarifas.csv --sistema privado
```

Mismo principio de licencias que con la terminología: el código que lee los
catálogos es libre, los catálogos los aporta quien tenga derecho a usarlos.
El repositorio incluye uno de demostración con importes inventados para que
el circuito pueda recorrerse recién clonado.

## El botón junto al plan: proponer no es autorizar

El eslabón que más trabajo cuesta en la vida real es el primero, pasar de
lo que el médico escribe a una orden estructurada. HolonMed lee el plan y
**propone**; el médico firma con un clic.

```
POST /api/facturacion/ordenes/proponer    devuelve borradores, no escribe
POST /api/facturacion/ordenes/autorizar   crea las órdenes reales
```

Son dos endpoints a propósito. Entre ellos está la firma, que es lo único
que convierte un texto sugerido por un modelo en algo que obliga a otros a
actuar. La propuesta no toca la base y no tiene identificador de orden: no
puede facturar nada aunque alguien se equivoque de llamada.

El borrador es editable, y lo es porque probarlo con el modelo local mostró
exactamente cómo falla. Con `gemma-4-E4B`, «Ondansetrón 8 mg si náusea»
volvía como término **«Medicamento»**, y «morfina 3 mg IV» como
«Administración intravenosa»: el fármaco desaparecía justo de la orden que
manda administrarlo. Una regla en el prompt lo corrigió, pero como volverá
a fallar quedan dos defensas que no dependen del modelo:

- **Una categoría genérica se marca y no se corrige sola.** Adivinar cuál
  era el fármaco es precisamente lo que no debe hacer.
- **Lo que el plan no especifica se muestra como hueco vacío**, nunca
  relleno a ojo. Un hueco visible se corrige antes de firmar; uno inventado
  se firma sin mirar y acaba administrándose.

Cambiar el término borra el código asociado: un código que ya no
corresponde al término factura otra cosa.

## Protocolos operativos por rol

`tipo: operativo` describe lo que debe constar cuando un actor cumple una
orden. `enfermeria.md` y `farmacia.md` declaran sus campos en YAML.

Lo valioso no es lo que extraen sino **lo que señalan que falta**. Un
registro a medias es una causa real de que un procedimiento no se cobre —no
es que no se haga, es que se documenta a medias mientras se atiende— y aquí
se detecta cuando todavía se puede corregir:

```
completo: false
faltantes: ['Horario indicado', 'Horario de administración']
```

La cuenta se exporta en XML, JSON o CSV, con la orden y la ejecución dentro
de cada línea: un cargo sin su orden no se puede defender ante una
auditoría. HolonMed no conoce el esquema de ningún organismo ni hospital y
no debería; entrega la estructura trazable y el mapeo al esquema de cada
sitio es una capa de integración de ese despliegue. Por la misma razón,
`referencias` es un diccionario libre: las claves las decide quien
despliega, no este repositorio.

## Los criterios de clasificación son bayesianos, y lo ausente informa

Un criterio diagnóstico parece booleano, pero tiene casi siempre la misma
forma: **manifestación de alta sospecha + prueba sensible + prueba
específica**. Eso es razonamiento bayesiano congelado en una regla, y ahora
el sistema lo trata como tal.

- **`lr_negativo`**: la ausencia documentada de un signo mueve la
  probabilidad igual que su presencia. Una lipasa normal es información,
  no silencio.
- **«No consta» no es «ausente».** Un auditor aparte decide si el texto
  niega el hallazgo o simplemente no lo menciona, y sólo la negación
  explícita produce evidencia. El silencio no genera ningún infón.
- **Infones de nivel 2.** Cuando los criterios de clasificación se
  satisfacen, el sistema acuña el término del trastorno (Atlanta 2012 para
  pancreatitis aguda) **derivándolo de los hallazgos**, no citándolo de la
  narrativa. Es lo que hace un clínico experimentado al reunir varios
  hallazgos anormales bajo un nombre.
- **Lo que falta pregunta.** Si un criterio queda sin datos, el sistema
  propone la prueba que lo resolvería — y no vuelve a pedir algo que ya
  salió normal.

## Los cortes del protocolo llegan al modelo, y se midió cómo presentarlos

Los cortes de laboratorio declarados en el frontmatter no estaban llegando
al prompt: el modelo auditaba sin saber el umbral que tenía que aplicar.

Al arreglarlo apareció la pregunta de en qué formato presentarlos, y en vez
de decidirlo por intuición se midió, con tres variantes sobre la misma
nota. La hipótesis de partida —mía— era que las etiquetas tipo XML
ayudarían a localizar el dato:

| Variante | Validados | Alertas | Inventados |
|----------|-----------|---------|------------|
| `minimo` (sin cortes) | 27/33 | 3 | **9** |
| `prosa` | 24/27 | 12 | 0 |
| `etiquetas` (estilo XML) | 21/24 | 12 | 0 |

Dos conclusiones, una de ellas contra lo que yo esperaba:

**El formato no importa.** `prosa` y `etiquetas` son indistinguibles. La
hipótesis de las etiquetas queda refutada con este modelo y esta nota, así
que el sistema usa prosa por defecto: misma fiabilidad, ~10 % menos de
tokens.

**Cuidado con la métrica fácil.** `minimo` es el que más hallazgos valida en
términos absolutos y es el peor de los tres: sin los cortes reales, el
modelo se inventó nueve. Contar validados sin mirar de dónde salen premia
justo el comportamiento que este proyecto existe para impedir.

Eso deja el criterio del proyecto sobre XML donde debe estar: **XML donde
un tercero con esquema consume el documento —la exportación de la cuenta—;
prosa donde lo lee un modelo de lenguaje.**

## Lo que sigue sin estar validado

Con la misma franqueza de siempre: **no hay corpus anotado de referencia.**
Todo lo medido aquí sale de una nota de prueba y de ejecuciones manuales
contra el modelo local. Sirve para detectar fallos gruesos —y ha detectado
unos cuantos— pero no es validación clínica y no debe presentarse como tal.

Sigue siendo una herramienta de apoyo a la decisión, sin autenticación, no
es un dispositivo médico, y ninguna de sus salidas sustituye el juicio de
un profesional sanitario.

## Migración desde v0.3.0

El esquema añade las tablas de la cadena de facturación y algunas columnas.
La migración es automática al arrancar y no toca los datos existentes. No
hay cambios incompatibles en la API previa.

Los protocolos operativos ya no aparecen en `/api/skills`: viven en
`/api/facturacion/roles`. Si algo consumía esa lista esperando encontrar
`enfermeria` o `farmacia`, ahí están.

151 tests, ruff limpio, CI en verde.
