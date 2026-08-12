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

Con 9 de 10 validados, Los tres restantes
apuntan al mismo sitio: **el auditor es inconsistente con un modelo de
esta escala**.

- **Se contradice.** Para «Hipotensión» con TA 100/60 razonó *«no es
  estrictamente menor que el corte de 100»* y aun así devolvió
  `valido: true`. El booleano y la prosa discrepan. Es un falso positivo.

- **Es arbitrariamente estricto.** «Dolor epigástrico» quedó en ALERTA
  con el motivo de que, aun estando en el texto, *«es más seguro marcarlo
  como inválido sin una conexión directa con un parámetro medible»*.
  Igual con «Hemoconcentración», derivada correctamente de Hto 48 > 44
  pero rechazada por no estar «explícitamente mencionada».

- **Devuelve JSON ilegible de vez en cuando.** Un caso de nueve en la
  primera ejecución, por truncamiento de razonamientos largos en
  markdown. Mitigado pidiendo respuestas de una frase y ampliando el
  timeout, pero no eliminado.

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
