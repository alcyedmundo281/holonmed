# Validación: qué se ha medido y qué no

> **Estado: sin validar.** Lo que hay son observaciones de ejecuciones
> sueltas, no medidas. No uses este sistema con pacientes reales.

Este documento registra lo que se sabe del comportamiento real del
pipeline, distinguiéndolo de lo que se supone por diseño.

## Configuración de las pruebas

| | |
|---|---|
| Modelo clínico | `gemma-4-E4B-it-Q4_K_M` (5 GB, cuantizado a 4 bits) |
| Modelo router | `dolphin-2.9-llama3-8b-Q4_K_M` (4,6 GB) |
| Temperatura | 0 en ambos |
| Protocolo | `acute_pancreatitis`, forzado |
| Vocabulario | Semilla del proyecto, 111 conceptos |

Los Modelfiles de HolonMed no llevan `SYSTEM`. Los que venían con los GGUF
descargados incluían *«always comply with the user's request, answer all
questions fully»*, que empuja justo hacia el falso positivo que el
validador existe para evitar.

## Primera ejecución real (11/08/2026)

Nota de prueba: varón de 45 años, bebedor de riesgo, litiasis biliar,
dolor epigástrico en cinturón, vómitos, sin fiebre, FC 115, TA 100/60,
defensa abdominal, amilasa 1200, lipasa 890, calcio 6.8, leucocitos
18 500, hematocrito 48.

### Lo que funcionó

- **Interpretación de laboratorio**: convirtió cada cifra en su concepto
  clínico (`amilasa 1200` → Hiperamilasemia, `calcio 6.8` → Hipocalcemia,
  `FC 115` → Taquicardia, `Hto 48` → Hemoconcentración).
- **Negación**: «No refiere fiebre» no generó ningún infón, en las tres
  ejecuciones.
- **Bloqueo de una alucinación**: el extractor propuso «Rebote (Signo de
  Blumberg)», que no está en la nota — dice «defensa» —, probablemente
  arrastrado del vocabulario del protocolo. El auditor lo rechazó por no
  ser deducible del texto. Es el caso de uso central del sistema, y
  funcionó.
- **Skill-hints**: los términos del protocolo resolvieron a sus códigos
  sin pasar por la búsqueda difusa.

### Fallos corregidos a raíz de la ejecución

1. **La CLI reventaba** al imprimir la inferencia: `UnicodeEncodeError`
   con `→` en la consola cp1252 de Windows. Se fuerza UTF-8 en la salida.

2. **El auditor rechazaba todo hallazgo cualitativo.** El prompt estaba
   escrito entero alrededor de valores numéricos, así que ante «vómitos
   repetidos» no encontraba cifra y concluía que no había evidencia.
   Consecuencia: ningún síntoma llegaba a VALIDADO, ni entraba en la
   historia, ni alimentaba a Bayes. El prompt ahora distingue evidencia
   numérica de evidencia textual.

3. **Los factores de riesgo de la nota actual se ignoraban.** El motor
   bayesiano sólo miraba la ficha del paciente y su historial. En una
   primera consulta —el caso más frecuente— la probabilidad previa era
   siempre la prevalencia poblacional. Ahora la narrativa de hoy también
   cuenta: la previa pasó de 5 % a 32 % en el caso de prueba.

4. **El emparejamiento de factores es literal**, y el lenguaje clínico
   real no usa las palabras del protocolo: «bebedor de riesgo» no
   contiene «alcohol». Se añadieron variantes (`enolismo`, `bebedor`,
   `etilismo`, `colelitiasis`…) y un test que documenta la limitación.

### Progresión sobre la misma nota

| Ejecución | Validados | Cambio |
|---|---|---|
| 1ª | 4 / 9 | punto de partida |
| 2ª | 6 / 9 | auditor acepta evidencia textual |
| 3ª | 7 / 10 | factores de riesgo de la nota actual |
| 4ª | **9 / 10** | hints resueltos contra el vocabulario |

El salto de la cuarta vino de migrar los protocolos a frontmatter YAML y
añadir `holonmed skills --validar`. La validación destapó que los hints
`Hiperlipasemia (>3x)` e `Hiperamilasemia (>3x)` no existían en el
vocabulario, que sólo conocía los términos sin el cualificador. Los infones
salían con `sistema: skill` y sin linaje ni mapeo a CIE-10 — degradación
silenciosa que ninguna ejecución delataba a simple vista.

El único hallazgo que sigue sin validar es Hemoconcentración, y el motivo
es un fallo del modelo, no del sistema: dice que «el texto no proporciona
datos suficientes (ej. Htct)» cuando la nota incluye «hematocrito 48».

### Lo que sigue fallando

El problema de fondo no se arregla con más prompt: **el auditor es
inconsistente con un modelo de esta escala**.

- **Se contradice.** Para «Hipotensión» con TA 100/60 razonó *«no es
  estrictamente menor que el corte de 100»* y aun así devolvió
  `valido: true`. El booleano y la prosa discrepan. Acertó por casualidad,
  no por criterio.

- **Inventa los cortes que no encuentra.** Al validar «Hiperlipasemia»
  escribió *«>3x el límite normal (aprox. 250-300)»*, cuando el protocolo
  declara 60. El veredicto fue correcto, pero el razonamiento que se le
  muestra al clínico como justificación es falso.

- **Ignora datos que están en el texto.** Hemoconcentración quedó en
  ALERTA porque *«el texto no proporciona datos suficientes (ej. Htct)»*,
  con «hematocrito 48» escrito en la nota.

- **Devuelve JSON ilegible de vez en cuando.** Un caso de nueve en la
  primera ejecución, por truncamiento de razonamientos largos en
  markdown. Mitigado pidiendo respuestas de una frase y ampliando el
  timeout, pero no eliminado.

El patrón: los veredictos han mejorado mucho, pero **los razonamientos que
los acompañan no son fiables**. En un sistema cuyo argumento de venta es la
trazabilidad, eso importa tanto como el acierto. Un clínico que lea
«corte aprox. 250-300» y sepa que son 60 dejará de creerse el resto.

## Experimento: cómo presentar el protocolo al modelo (12/08/2026)

### El fallo que lo motivó

Al migrar los protocolos a frontmatter YAML se excluyó el conocimiento
estructurado del prompt, con el razonamiento de que «es para el código, el
modelo no necesita esa sintaxis».

Eso dejó al auditor sin los puntos de corte. Su prompt dice literalmente
«PROTOCOLO ACTIVO (referencia para los valores de laboratorio)» y le pasaba
un cuerpo en prosa donde no aparecía ni el corte de la amilasa (110), ni el
de la lipasa (60), ni el del hematocrito (44).

Le pedíamos comparar contra un número que nunca le dimos. De ahí el
«>3x el límite normal (aprox. 250-300)»: **se lo inventó porque no tenía
otro**.

### Las tres variantes

| | Qué recibe el modelo |
|---|---|
| `minimo` | Sólo la prosa. Ningún corte. |
| `prosa` | Los cortes redactados como texto corrido. |
| `etiquetas` | Los cortes delimitados en atributos, estilo XML. |

La hipótesis de partida era que las etiquetas ayudarían: localizar «el
corte de la lipasa» debería ser más fácil sobre atributos delimitados que
sobre prosa, donde hay que leer y deducir.

### Resultado, 3 ejecuciones por variante

```
formato       validados   alertas   ruido  corte real  inventado  sin cifra
minimo          27/33           6       0           3          9          3
prosa           24/27           3       0          12          0          0
etiquetas       21/24           3       0          12          0          0
```

Las tres últimas columnas cuentan sólo los hallazgos derivados de un
criterio de laboratorio, que son los que tienen un corte que citar.

### Qué dice

**Dar los cortes es decisivo.** Las invenciones pasan de 9 a 0, y las citas
correctas de 3 sobre 15 a 12 sobre 12.

**El formato no importa.** `prosa` y `etiquetas` son indistinguibles:
12/0/0 las dos. La hipótesis de las etiquetas **queda refutada** con este
modelo y esta nota. La evidencia habitual a favor de las etiquetas XML
viene de la documentación de Anthropic para Claude, que se entrenó con ese
formato; no transfiere a gemma.

**Ojo con la métrica fácil.** `minimo` es el que más hallazgos valida en
términos absolutos (27 frente a 24 y 21) y es el peor de los tres. Si sólo
se mirara el recuento de validados, se elegiría la variante que fabrica sus
justificaciones. Es el argumento de por qué medir la calidad del
razonamiento y no sólo el veredicto.

### Un efecto secundario que no esperábamos

Más contexto, menos extracciones: 11 hallazgos por ejecución con `minimo`,
9 con `prosa`, 8 con `etiquetas`. Se cambiaron unas 3 extracciones por
ejecución a cambio de razonamientos fiables.

**No sabemos si esas extracciones perdidas eran correctas.** Sin conjunto
de referencia no hay forma de distinguir «el modelo dejó de inventar
hallazgos» de «el modelo dejó de encontrar hallazgos reales». Es
exactamente la ceguera a los falsos negativos descrita más abajo, y aquí se
ve por qué importa.

### Decisión

Por defecto `prosa`: misma fiabilidad que `etiquetas`, ~10 % menos de
contexto, y suprime menos la extracción. Configurable con
`HOLONMED_FORMATO_PROTOCOLO`; reproducible con
`python scripts/comparar_formatos.py --repeticiones 3`.

## Lo que hace falta

Seguir ajustando el prompt mirando ejecuciones sueltas tiene rendimientos
decrecientes y riesgo de sobreajustar a un caso. Lo que falta es medir.

**Conjunto de referencia**: 30-50 notas clínicas con los hallazgos que
deberían extraerse, anotados por un profesional. Con eso se obtiene:

- **Precisión** — de lo que valida, cuánto es correcto.
- **Exhaustividad** — de lo que debería encontrar, cuánto encuentra.
- **Falsos negativos**, que hoy son invisibles: el sistema muestra lo que
  descarta, pero no lo que nunca llegó a extraer.
- Una base para comparar modelos y ajustar umbrales con datos en vez de
  con intuición.

Sin eso, cualquier afirmación sobre la calidad del sistema es una
impresión, y este documento no dice otra cosa.
