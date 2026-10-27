---
titulo: Protocolo de enfermedad de Parkinson
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Enfermedad de Parkinson (parkinson, EP, enfermedad de Parkinson
  idiopática).
version: 0.1.0-borrador

condicion:
  nombre: Enfermedad de Parkinson
  codigos:
    holonmed: HM:6015

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0500   # Síntoma neurológico

# Sin el núcleo el criterio ni siquiera se aplica: no es una
# exclusión, es que la pregunta todavía no se puede hacer.
nucleo:
  requiere: ["Bradicinesia"]
  y_al_menos_uno_de: ["Temblor de reposo", "Rigidez parkinsoniana"]
  fuente: >-
    Postuma RB et al. Mov Disord 2015;30:1591-601. PMID 26474316.
    doi:10.1002/mds.26424.

# Los niveles se evalúan EN ORDEN y gana el primero que se
# satisface: invertirlos rebajaría el grado en silencio.
balance:
  fuente: >-
    Postuma RB et al. Mov Disord 2015;30:1591-601. PMID 26474316.
    doi:10.1002/mds.26424.
  establecida: { apoyos_minimos: 2, banderas_maximas: 0 }
  probable: { contrapeso: 1, banderas_maximas: 2 }

modelo_bayesiano:
  # El índice no publica prevalencia para esta condición. Sin probabilidad
  # base el motor no arranca: pon la de tu población.
  probabilidad_base: 0.0

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Bradicinesia
    codigos: { holonmed: "HM:3061" }
    rol: manifestacion
    # no_medible: forma parte de la definición de parkinsonismo motor, que
    # es el patrón de referencia del propio criterio: sesgo de incorporación

  - nombre: Temblor de reposo
    codigos: { holonmed: "HM:3062" }
    rol: manifestacion
    # no_medible: componente del núcleo; sesgo de incorporación

  - nombre: Rigidez parkinsoniana
    codigos: { holonmed: "HM:3063" }
    rol: manifestacion
    # no_medible: componente del núcleo; sesgo de incorporación

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6015
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ENFERMEDAD DE PARKINSON

ROL: <!-- especialidad y postura: «cardiólogo experto, basado en evidencia» -->

## Contexto fisiopatológico

<!-- El índice no guarda prosa. Estas tres líneas son las que hacen que
     el modelo reconozca el cuadro y no sólo sus términos. -->

- **Dónde**: <!-- órgano, territorio, compartimento -->
- **Cómo**: <!-- mecanismo -->
- **Por qué**: <!-- causas frecuentes -->

## Instrucciones de extracción

1. Analiza los signos vitales, la exploración y el texto libre.
2. Extrae el hallazgo clínico, nunca la cifra suelta.
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
