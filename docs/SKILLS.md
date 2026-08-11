# Escribir un protocolo clínico

Un protocolo (*skill*) es un archivo Markdown en `backend/skills/`. Añadir
uno es añadir un archivo: no se toca el código.

El Markdown cumple dos funciones a la vez. El texto narrativo entra en el
prompt e instruye al modelo. Los bloques JSON los parsea el código y los
usa directamente. Ese doble uso es intencionado: el conocimiento vive en un
solo sitio y no puede desincronizarse.

## Estructura mínima

```markdown
# SKILL: NOMBRE DEL PROTOCOLO

ROL: quién debe creerse el modelo al leer esto.
OBJETIVO: qué debe extraer.

BASE DE CONOCIMIENTO (JSON-LD):

{
  "@context": "https://schema.org",
  "@type": "MedicalCondition",
  "name": "Nombre de la condición",
  "snomed_id": "197456007"
}

INSTRUCCIONES CLÍNICAS:
1. …
```

La **primera línea** es la descripción que ve el triaje al elegir
protocolo. Escríbela pensando en eso.

## Los tres bloques que consume el código

### `signDetected` — signos y sus likelihood ratios

```json
"signDetected": [
  {
    "name": "Hiperlipasemia (>3x)",
    "snomed_id": "10443000",
    "bayes_lr": 24.0,
    "description": "Criterio diagnóstico principal, alta especificidad."
  }
]
```

Cada entrada aporta dos cosas: un **skill-hint** (el par nombre→código que
gana a cualquier búsqueda difusa) y un **likelihood ratio** para el motor
bayesiano.

El código puede pertenecer a cualquier sistema. Si el vocabulario que lo
contiene no está cargado, el hint sigue valiendo — lo revisó un humano —
pero el infón no podrá ofrecer linaje ni mapeo a CIE-10, y eso se ve en el
resultado.

Sobre los LR:

- Un LR de 1.0 no aporta información y se ignora.
- Un LR > 1 apoya la hipótesis; < 1 la debilita.
- El sistema recorta cualquier LR por encima de 100 y lo registra. Un LR de
  1000 en un protocolo casi siempre es un error de transcripción.
- **Cita la fuente** en `description`. Un LR sin procedencia es un número
  inventado con formato científico.

También se acepta la forma anidada `"code": {"codeValue": "..."}` para
compatibilidad con JSON-LD más formal.

### `criterios_laboratorio` — de números a conceptos

```json
"criterios_laboratorio": {
  "instruccion": "Compara los valores con estos rangos.",
  "reglas": [
    {
      "parametro": "Calcio sérico",
      "corte_inferior": 8.5,
      "termino_si_bajo": "Hipocalcemia",
      "snomed_id": "5291005"
    },
    {
      "parametro": "Amilasa",
      "corte_superior": 110,
      "multiplicador_pancreatitis": 3,
      "termino_si_alto": "Hiperamilasemia (>3x)",
      "snomed_id": "10427000"
    }
  ]
}
```

Esto es lo que convierte «Calcio 6.8» en el concepto *Hipocalcemia* con su
código, en vez de dejar un número suelto. Los términos declarados aquí
también se convierten en skill-hints.

Es además el material contra el que trabaja la auditoría lógica: el modelo
recibe estos cortes y debe mostrar la comparación numérica explícita antes
de dar un hallazgo por válido.

Declara `termino_si_alto` y `termino_si_bajo` por separado. Un mismo
parámetro fuera de rango en direcciones opuestas es un cuadro distinto, y
confundir la dirección es uno de los errores que el validador vigila.

### `modelo_bayesiano` — la probabilidad a priori

```json
"modelo_bayesiano": {
  "probabilidad_base": 0.05,
  "factores_riesgo_a_priori": {
    "alcoholismo": 2.8,
    "litiasis": 3.2
  }
}
```

`probabilidad_base` es la prevalencia en la población que atiendes, no la
de la literatura mundial. Cambiarla mueve todos los resultados del
protocolo.

Los factores de riesgo se buscan como subcadena en los antecedentes del
paciente y en su historia de infones validados. Por eso conviene declarar
variantes (`"alcohol"`, `"alcoholismo"`) — el emparejamiento es literal, no
semántico.

**Si omites este bloque, no hay inferencia bayesiana.** Es lo correcto para
un protocolo de triaje general, que no estima la probabilidad de ninguna
enfermedad concreta. El sistema no inventa un modelo que no declaraste.

## Escribir las instrucciones narrativas

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

## Comprobar el resultado

```bash
holonmed skills
```

```bash
holonmed skills --nombre mi_protocolo
```

Muestra el diccionario de hints extraído. Si sale vacío, tu JSON no está
parseando: revisa las comas y las comillas.

```bash
holonmed tic "narrativa de prueba" --skill mi_protocolo
```

Fuerza el protocolo y salta el triaje, que es como conviene depurar: si el
resultado es malo, quieres saber si falla la extracción o la selección.

## Añadirlo a los tests

`tests/test_skills.py::test_los_skills_del_repositorio_son_validos` recorre
todos los protocolos del repositorio y comprueba que parsean y aportan
hints. Si añades uno, entra en esa comprobación automáticamente.
