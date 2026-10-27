---
titulo: Protocolo de enfermedad del manguito rotador
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Enfermedad del manguito rotador (patología del manguito rotador,
  tendinopatía del manguito).
version: 0.1.0-borrador

condicion:
  nombre: Enfermedad del manguito rotador
  codigos:
    holonmed: HM:6013

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0208   # Lumbalgia
  - HM:0500   # Síntoma neurológico

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
  - nombre: Arco doloroso
    codigos: { holonmed: "HM:3055" }
    rol: prueba_especifica
    lr: 3.7
    lr_negativo: 0.36
    fuente: >-
      Hermans J et al. JAMA 2013;310:837-47. PMID 23982370.
      doi:10.1001/jama.2013.276187. LR+ IC95% [1.9, 7.0]. LR− IC95% [0.23,
      0.54]. La única prueba de provocación de dolor con cociente positivo
      por encima de 2, y la que mejor descarta cuando es normal.

  - nombre: Signo del brazo caído
    codigos: { holonmed: "HM:3058" }
    rol: apoyo
    lr: 3.3
    fuente: >-
      Hermans J et al. JAMA 2013;310:837-47. PMID 23982370.
      doi:10.1001/jama.2013.276187. IC95% [1.0, 11]. Puede ayudar a
      identificar la enfermedad, pero su intervalo toca 1.0: es compatible
      con no aportar nada.

  - nombre: Dolor de hombro
    codigos: { holonmed: "HM:3059" }
    rol: manifestacion
    # no_medible: es el motivo de consulta que define la población
    # estudiada, no una prueba dentro de ella

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6013
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ENFERMEDAD DEL MANGUITO ROTADOR

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

## Lo que la fuente concluye

El arco doloroso positivo y la prueba de resistencia a la rotación externa
fueron los hallazgos más precisos para detectar la enfermedad del
manguito. Como todas las maniobras las realizaron especialistas, se
desconoce hasta qué punto los resultados se generalizan a población no
derivada.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
