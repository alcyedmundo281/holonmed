# Escribir un protocolo clínico

Un protocolo (*skill*) es un archivo Markdown en `backend/skills/`. Añadir
uno es añadir un archivo: no se toca el código.

Tiene dos partes con funciones distintas:

- **Frontmatter YAML** — conocimiento estructurado que consume el código:
  códigos, puntos de corte, likelihood ratios y ámbito del grafo.
- **Cuerpo Markdown** — instrucciones en prosa que entran en el prompt.

El frontmatter **no** se le pasa al modelo. Gastaría contexto en sintaxis
que no necesita interpretar, y le daría los códigos que precisamente debe
deducir el validador.

## Comprobar lo que escribes

Antes que nada, el comando que te dirá si el protocolo está bien:

```bash
holonmed skills --validar
```

Revisa cada protocolo y, si hay vocabulario cargado, comprueba que **cada
código declarado exista de verdad**. Un hint que apunta a un concepto
inexistente no falla: produce infones sin linaje ni mapeo a CIE-10, en
silencio. Es exactamente el fallo que este comando saca a la luz.

## Estructura

```yaml
---
titulo: Protocolo de pancreatitis aguda
descripcion: >-
  La frase que ve el triaje al elegir protocolo. Escríbela pensando en eso.
version: "2.0.0"

condicion:
  nombre: Pancreatitis aguda
  codigos:
    snomed: "197456007"

# Ramas del grafo sobre las que actúa. Permite preguntar qué protocolos
# aplican a un paciente a partir de los hallazgos que ya tiene, en vez de
# que el triaje decida sólo con el texto de hoy.
ambito_grafo:
  - HM:0730

modelo_bayesiano:
  probabilidad_base: 0.05
  factores_riesgo:
    alcohol: 2.8

signos:
  - nombre: Hiperlipasemia (>3x)
    codigos: { holonmed: "HM:0732", snomed: "10443000" }
    lr: 26.6
    fuente: JAMA Rational Clinical Examination.

laboratorio:
  - parametro: Calcio sérico
    corte_inferior: 8.5
    termino_si_bajo: Hipocalcemia
    codigos: { holonmed: "HM:0721" }
---

# TÍTULO DEL PROTOCOLO

Instrucciones en prosa para el modelo…
```

## Los cuatro bloques

### `signos` — qué reconoce el protocolo

Cada entrada aporta dos cosas: un **skill-hint** (el par nombre→código que
gana a cualquier búsqueda difusa) y un **likelihood ratio** para el motor
bayesiano.

Los códigos van por sistema. Se prefiere `holonmed` porque es el único
garantizado presente; si sólo declaras `snomed` y no está importado, el
hint sigue valiendo —lo revisó un humano— pero el infón no podrá ofrecer
linaje ni mapeo a CIE-10.

**El nombre del signo tiene que existir en el vocabulario.** Si declaras
`Hiperlipasemia (>3x)` pero el vocabulario sólo conoce `Hiperlipasemia`, el
hint no resuelve. Las opciones son añadir la variante como sinónimo del
concepto, o usar el término que el vocabulario ya reconoce. `--validar` te
lo dirá.

Sobre los LR:

- Un LR de 1.0 no aporta información y se ignora.
- Un LR > 1 apoya la hipótesis; < 1 la debilita.
- Por encima de 100 se recorta y se registra: casi siempre es un error de
  transcripción.
- **`fuente` es obligatoria** cuando hay LR. Un likelihood ratio sin
  procedencia es un número inventado con formato científico, y mueve la
  probabilidad que ve un clínico. Hay un test que lo comprueba.

### `laboratorio` — de números a conceptos

```yaml
laboratorio:
  - parametro: Amilasa
    corte_superior: 110
    multiplicador: 3
    termino_si_alto: Hiperamilasemia (>3x)
    codigos: { holonmed: "HM:0731" }
```

Es lo que convierte «Calcio 6.8» en el concepto *Hipocalcemia* con su
código, en vez de dejar un número suelto. Los términos declarados aquí
también se convierten en hints.

Es además el material contra el que trabaja la auditoría lógica: el modelo
recibe estos cortes y debe mostrar la comparación numérica antes de dar un
hallazgo por válido.

Declara `termino_si_alto` y `termino_si_bajo` por separado. Un mismo
parámetro fuera de rango en direcciones opuestas es un cuadro distinto, y
confundir la dirección es uno de los errores que el validador vigila.

### `modelo_bayesiano` — la probabilidad a priori

`probabilidad_base` es la prevalencia en la población que atiendes, no la
de la literatura mundial. Cambiarla mueve todos los resultados.

**Los factores se emparejan por subcadena literal.** Esto importa más de lo
que parece: un clínico escribe «bebedor de riesgo», que no contiene
«alcohol», así que un factor declarado como `alcoholismo` nunca se
aplicaría. Declara las variantes que la gente usa de verdad:

```yaml
factores_riesgo:
  alcohol: 2.8
  alcoholismo: 2.8
  enolismo: 2.8
  bebedor: 2.8
```

Consecuencia de lo mismo: **no entiende negaciones**. Una nota que diga «no
consume alcohol» activaría igualmente el factor. Por eso la traza muestra
siempre qué factor se aplicó y con qué peso, para que se pueda revisar.

Los factores se buscan en tres sitios: los antecedentes de la ficha, los
hallazgos validados de visitas anteriores, y **la narrativa de hoy**. Sin
esto último, una primera consulta arrancaría siempre en la prevalencia
poblacional.

**Si omites el bloque, no hay inferencia bayesiana.** Es lo correcto para
un protocolo de triaje general, que no estima la probabilidad de ninguna
enfermedad concreta. El sistema no inventa un modelo que no declaraste.

### `ambito_grafo` — dónde actúa el protocolo

Lista de códigos que delimitan la rama del grafo que cubre el protocolo.
Permite la consulta inversa: dado un paciente con ciertos hallazgos, qué
protocolos le aplican.

### `tipo` — clínico o documento

Por defecto `clinico`: el protocolo extrae hallazgos. Con `tipo: documento`
—como `receta`— el validador no le exige signos ni criterios, porque su
función es dar formato a algo que el profesional ya decidió.

## Escribir el cuerpo en prosa

Lo que funciona con modelos locales:

- **Ejemplos concretos** por encima de reglas abstractas. «Si ves "FC 115",
  extrae "Taquicardia"» funciona mejor que «interpreta los signos vitales».
- **Prohibiciones explícitas** de los errores que ese dominio produce. En
  pancreatitis: «no confundas amilasa con lipasa». El modelo las comete si
  no se lo dices.
- **Insistir en la granularidad**: «dolor epigástrico» es un hallazgo,
  «pancreatitis» es una hipótesis. Sin esa instrucción, los modelos saltan
  del síntoma al diagnóstico.
- **Negaciones**: recuerda que «sin fiebre» no debe generar ningún infón.

## Depurar

```bash
holonmed skills --nombre mi_protocolo
```

Muestra el resumen y el diccionario de hints. Si sale vacío, el frontmatter
no está parseando.

```bash
holonmed tic "narrativa de prueba" --skill mi_protocolo
```

Fuerza el protocolo y salta el triaje, que es como conviene depurar: si el
resultado es malo, quieres saber si falla la extracción o la selección.

## Formato antiguo

Los protocolos escritos con JSON-LD embebido en la prosa siguen
funcionando: se traducen al vuelo y se registra un aviso. No se recomienda
para protocolos nuevos, porque había que rascarlos con expresiones
regulares y un error de sintaxis producía un skill silenciosamente vacío
—sin hints, sin cortes y sin modelo bayesiano, pero cargado y en uso.

## Tests

`tests/test_skills.py` recorre todos los protocolos del repositorio y
comprueba que parsean, que aportan hints y que ningún LR va sin fuente. Si
añades uno, entra en esas comprobaciones automáticamente.
