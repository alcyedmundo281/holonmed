---
titulo: Protocolo de cáncer de mama
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Cáncer de mama (carcinoma mamario, neoplasia maligna de mama).
version: 0.1.0-borrador

condicion:
  nombre: Cáncer de mama
  codigos:
    holonmed: HM:6034

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0600   # Signo de exploración

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
  - nombre: Masa mamaria palpable o hallazgo sospechoso en la exploración
    codigos: { holonmed: "HM:3142" }
    rol: prueba_especifica
    lr: 10.6
    fuente: >-
      Barton MB et al. JAMA 1999;282:1270-80. PMID 10517431.
      doi:10.1001/jama.282.13.1270. IC95% [5.8, 19.2]. El hallazgo de una
      masa dominante o nódulo sospechoso en el examen clínico eleva
      marcadamente la probabilidad (LR+ 10.6).

  - nombre: Examen clínico de mama reglado normal
    codigos: { holonmed: "HM:3143" }
    rol: prueba_sensible
    lr_negativo: 0.47
    fuente: >-
      Barton MB et al. JAMA 1999;282:1270-80. PMID 10517431.
      doi:10.1001/jama.282.13.1270. IC95% [0.4, 0.56]. Una palpación
      normal reduce la probabilidad de forma modesta (LR- 0.47) pero no
      excluye la necesidad de mamografía de cribado.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6034
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE CÁNCER DE MAMA

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

La exploración clínica mamaria (CBE) reglada y minuciosa de al menos 3
minutos por mama es una herramienta diagnóstica complementaria relevante:
un resultado positivo tiene un cociente de 10.6 (especificidad 94%),
aunque un examen normal no descarta la enfermedad (LR- 0.47).

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
