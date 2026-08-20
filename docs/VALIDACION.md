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

## Evidencia negativa y criterios de clasificación (12/08/2026)

### El fallo de partida

El motor sólo sabía sumar. El prompt de extracción decía literalmente
«NEGACIONES: ignora los hallazgos negados», así que una lipasa normal
—la evidencia más potente **en contra** de una pancreatitis— no llegaba a
ninguna parte. El sistema únicamente podía subir la probabilidad.

### Lo que cambia

| Caso | Antes | Ahora |
|---|---|---|
| Hallazgo presente | LR+ | LR+ |
| Ausencia documentada | *se descartaba* | **LR−** |
| No consta | nada | **se pregunta** |

Sobre el mismo paciente, cambiando sólo la lipasa de 890 a 45:

```
posterior 49.76 %  →  9.01 %
→ Hiperlipasemia [ausente] → LR 0.1 (en contra)
```

### El prompt de ausencia necesitó dos intentos

La primera versión enumeraba casos válidos e inválidos, con un aviso muy
enfático sobre no confundir el silencio con una negación. El modelo aplicó
ese aviso por encima de todo lo demás:

> «un valor de lipasa (45) por debajo del corte, pero no niega
> explícitamente su ausencia. Un silencio sobre el hallazgo es inválido.»

Es decir: confundió **una cifra medida** con **un silencio**, que es
exactamente lo contrario de lo que el aviso pretendía.

La segunda versión no enumera reglas sino un **procedimiento ordenado** —
¿hay cifra? compárala; ¿hay negación explícita?; ¿no aparece por ningún
lado? entonces sí es silencio — con una única frase de cierre: «un dato
medido nunca cae en el paso 3». Con eso acierta.

**Lección general**: un prompt con dos reglas de fuerza parecida produce
comportamiento inestable, y gana la que esté escrita con más énfasis. Los
procedimientos ordenados se comportan mejor que las listas de advertencias.

### Pedir lo que ya se hizo

Al principio, una ausencia que no superaba la auditoría caía en «sin
datos», y el sistema pedía una prueba **ya realizada y normal**. Eso
erosiona la confianza en dos consultas.

Ahora se distinguen cuatro estados por criterio, porque exigen conductas
distintas: satisfecho, descartado, sin confirmar —hay dato, revísalo— y
sin datos, que es el único que genera una petición nueva.

### Criterios de clasificación

Los criterios publicados —Atlanta, Duke, ACR/EULAR— parecen booleanos y
son bayesianos: la manifestación fija la probabilidad pre-test, la prueba
sensible descarta si es negativa y la específica confirma si es positiva.
El «2 de 3» es la abreviatura de que el posterior cruza el umbral.

El sistema los evalúa en Python sobre hallazgos ya validados y acuña un
**infón de nivel 2**: un trastorno cuya procedencia no es una cita de la
nota sino la lista de hallazgos que lo satisfacen, con la cita del panel
que definió los criterios.

Dos salvaguardas: un hallazgo en ALERTA no puede satisfacer un criterio, y
el trastorno hereda la confianza más baja de la evidencia que lo sostiene.
Un diagnóstico no puede ser más firme que su hallazgo peor sostenido, por
mucho que venga con criterios y cita.

## Cómo se verifica aquí (20/08/2026)

Este documento registra **qué se ha medido**. Esta sección registra **cómo se
comprueba lo medido**, que resultó ser un problema aparte y con su propio modo
de fallo.

La regla, en una frase:

> **Verde no significa comprobado si nadie miró qué camino se recorrió.**

No es un principio general sobre pruebas: es el resumen de cinco casos reales
de este repositorio, todos con la suite en verde y todos con la verificación
recorriendo un camino distinto del que decía recorrer.

### Los cinco casos

**1. Una mutación que no se aplica.** Al comprobar un guarda por mutación, el
parche no llegó al archivo por una diferencia de indentación y el resultado
fue «20 passed». Una mutación que no se aplica se lee **exactamente igual** que
un guarda que funciona.

**2. Una mutación que muta un comentario.** Al verificar el emparejamiento del
núcleo se renombró `emparejar_termino` en `skills.py`, se confirmó que la
cadena había cambiado en el archivo, y los tests siguieron pasando. La única
aparición de ese nombre en ese archivo estaba en un docstring: el código real
vivía en `veredicto.py`. Comprobar que la mutación *se aplicó* no basta; hay
que comprobar que **alcanzó el camino que el test ejecuta**.

**3. Una aserción con salida de emergencia.** El test que debía garantizar que
Φ categórico funciona sin likelihood ratios decía:

```python
assert res is None or res.phi_categorico is not None
```

Como el protocolo de la fixture no declaraba ningún LR, `res is None` era
siempre cierto, el `or` cortocircuitaba y la segunda mitad no se evaluaba
nunca. El test pasaba **por la misma razón por la que debía fallar**.

El problema no es el operador sino de dónde sale. Un `or` que expresa una
disyunción real del dominio es legítimo; aquél expresaba la incertidumbre de
quien escribía el test, y la rama defensiva resultó ser justo la que el fallo
toma. Un `or` que describe al autor y no al dominio es decoración.

**4. Una condición de salto sobre un campo sin lista blanca.** El salto de
`test_los_protocolos_clinicos_aportan_hints` era `if skill.tipo != "clinico"`,
una negación abierta, y `tipo` era el único campo taxonómico del parseador sin
normalizar contra un conjunto conocido —`rol`, `efecto` y `dispara_si` sí lo
hacían—. Cualquier cadena distinta de `clinico` eximía al protocolo de declarar
signos **y** saltaba la comprobación de hints:

```
'clinico' → 1 problema, no salta      'clínico' → 0 problemas, SALTA
'Clinico' → 0 problemas, SALTA        ''        → 0 problemas, SALTA
```

Un acento mal puesto, en un repositorio escrito en español, dejaba un protocolo
clínico sin validar y la build en verde.

**5. Una muestra que hace cierto el resultado.** Fuera de las pruebas, el mismo
patrón: en el estudio de la fase 2, una medición correcta sobre cuatro
configuraciones disfrazadas de veinte, donde la cantidad que se decía variar se
movía un 0.5 %. Ver `FASE2-ACOPLAMIENTO.md` §9, que indexa cada cifra con la
muestra sobre la que se midió.

### La comprobación, que no necesita juicio

**Si una de las ramas nunca se ejecuta, la aserción no prueba lo que dice.**

Se mide, no se opina, y generaliza más allá del `or`: vale igual para un `if`
dentro de un test, un `pytest.skip` condicional o una mutación que se creyó
aplicada. Las preguntas concretas son tres:

1. ¿Qué rama toma este test **de verdad**, hoy, con el código como está?
2. Si es una mutación: ¿tocó la línea que el test ejecuta, o una homónima?
3. Si salta: ¿hay algo que **sí** debería afirmarse sobre lo que salta, y lo
   afirma algún otro test?

La tercera es la que encontró el caso 4. Los tres saltos que quedan en la suite
son legítimos —dos protocolos operativos y uno de documento, que por definición
no extraen hallazgos, y que sí se validan por la rama `operativo` de
`problemas()`— pero la condición que enrutaba hacia ellos no lo era.

### Dirección del respaldo

Cuando algo no se reconoce, el valor por defecto debe ser **el más estricto y
no el más permisivo**. `tipo` caía al más permisivo por accidente: al no
coincidir con ninguna rama, escapaba de todas. Hoy se normaliza a `clinico`, y
`problemas()` denuncia el valor declarado.

La normalización y el informe cubren frentes distintos y hacen falta los dos:
`problemas()` sólo corre bajo `skills --validar`, que CI ejecuta para los
protocolos del repositorio pero **nadie ejecuta en producción**. La
normalización es la única defensa que actúa siempre; el informe es lo que hace
que alguien corrija la errata en vez de convivir con ella.

---

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
