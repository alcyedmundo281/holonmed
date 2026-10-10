---
titulo: Protocolo de trastorno de pánico
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Trastorno de pánico (crisis de angustia, ataques de pánico,
  ansiedad paroxística episódica).
version: 0.1.0-borrador

condicion:
  nombre: Trastorno de pánico
  codigos:
    holonmed: HM:6032

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:3138   # Cuestionario PHQ de pánico positivo

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.085
  # medida en: pacientes adultos atendidos en consultas de atención primaria
  # Herr NR et al. JAMA 2014;312:78-84. PMID 25058220.
  # doi:10.1001/jama.2014.5950.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Cuestionario PHQ de pánico positivo
    codigos: { holonmed: "HM:3138" }
    rol: prueba_especifica
    lr: 78.0
    lr_negativo: 0.2
    fuente: >-
      Herr NR et al. JAMA 2014;312:78-84. PMID 25058220.
      doi:10.1001/jama.2014.5950. LR+ IC95% [29.0, 210.0]. LR− IC95%
      [0.11, 0.37]. El módulo de pánico del PHQ tiene un cociente positivo
      masivo (LR+ 78) y permite descartar eficazmente cuando es negativo
      (LR- 0.20).

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6032
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE TRASTORNO DE PÁNICO

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

El módulo de pánico del Patient Health Questionnaire (PHQ) es el
instrumento de autoinforme más potente para detectar el trastorno de
pánico en atención primaria (LR+ 78, LR- 0.20).

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
