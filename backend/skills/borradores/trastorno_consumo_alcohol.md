---
titulo: Protocolo de trastorno por consumo de alcohol
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Trastorno por consumo de alcohol (alcoholismo, dependencia del
  alcohol, abuso de alcohol, consumo perjudicial de alcohol).
version: 0.1.0-borrador

condicion:
  nombre: Trastorno por consumo de alcohol
  codigos:
    holonmed: HM:6021

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
  # El índice declara «Antecedente parental de trastorno por consumo de
  # alcohol» sin peso.
  # nota: HR 2.21 (IC95% 2.07-2.36) si es el padre y 2.57 (IC95% 2.20-3.01)
  # si es la madre, sin otro trastorno mental asociado. Cohorte de registros
  # daneses: 15 477 hijos expuestos y 154 392 de referencia
  # Holst C et al. Acta Psychiatr Scand 2019;139:508-517. PMID 30689217.
  # doi:10.1111/acps.13002.
  # El índice declara «Inicio precoz del consumo de alcohol en la
  # adolescencia» sin peso.
  # nota: OR 11.83 en mujeres y 6.24 en varones para dependencia del
  # alcohol, sin intervalo de confianza en el resumen. Cohorte de 5170
  # universitarios con seguimiento de 3 años
  # Caamano-Isorna F et al. Int J Environ Res Public Health 2020;17. PMID
  # 32213910. doi:10.3390/ijerph17062159.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Cuestionario AUDIT con puntuación ≥ 8
    codigos: { holonmed: "HM:3083" }
    rol: prueba_especifica
    lr: 6.5
    fuente: >-
      Wood E et al. JAMA 2024;331:1215-1224. PMID 38592385.
      doi:10.1001/jama.2024.3101. IC95% [3.9, 11]. Población: adultos
      evaluados con cuestionario AUDIT frente a criterios diagnósticos
      DSM-5 (n = 79 633). En mujeres el LR+ es 6.9 (IC 95%: 3.9-12); en
      hombres es 3.8 (IC 95%: 2.6-5.5). AUDIT ≥ 8: el instrumento estándar
      de cribado. Con LR+ de 6.5 global (6.9 en mujeres y 3.8 en hombres),
      confirma alta probabilidad de trastorno por consumo de alcohol según
      DSM-5 y exige intervención breve o derivación.

  - nombre: Cuestionario AUDIT con puntuación < 8
    codigos: { holonmed: "HM:3085" }
    rol: prueba_sensible
    lr_negativo: 0.33
    fuente: >-
      Wood E et al. JAMA 2024;331:1215-1224. PMID 38592385.
      doi:10.1001/jama.2024.3101. IC95% [0.2, 0.52]. Población: adultos
      evaluados con AUDIT. AUDIT < 8: reduce la probabilidad de trastorno
      por consumo de alcohol (LR- 0.33) de forma consistente en mujeres y
      hombres.

  - nombre: Cuestionario AUDIT-C positivo (hombres ≥ 4, mujeres ≥ 3)
    codigos: { holonmed: "HM:3084" }
    rol: apoyo
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Wood E et al. JAMA 2024;331:1215-1224. PMID 38592385.
    # doi:10.1001/jama.2024.3101. Población: adultos en atención primaria.
    # Hombres LR+ 1.8 (IC 95%: 1.5-2.2); mujeres LR+ 2.0 (IC 95%: 1.8-2.3).
    # AUDIT-C positivo (hombres ≥4, mujeres ≥3): útil para detectar consumo
    # excesivo de riesgo rápido, pero modesto para confirmar trastorno por
    # consumo formal (LR+ ~1.9).

  - nombre: Cuestionario AUDIT con puntuación ≥ 4 en postparto
    codigos: { holonmed: "HM:3086" }
    rol: prueba_especifica
    lr: 6.4
    fuente: >-
      Wood E et al. JAMA 2024;331:1215-1224. PMID 38592385.
      doi:10.1001/jama.2024.3101. IC95% [5.1, 8.0]. Población: mujeres
      puérperas evaluadas en las primeras 48 horas postparto. AUDIT ≥ 4 en
      postparto: identifica eficazmente a puérperas con alta probabilidad
      de trastorno por consumo de alcohol (LR+ 6.4).

  - nombre: Cuestionario TWEAK o T-ACE con puntuación < 2 en postparto
    codigos: { holonmed: "HM:3087" }
    rol: prueba_sensible
    lr_negativo: 0.05
    fuente: >-
      Wood E et al. JAMA 2024;331:1215-1224. PMID 38592385.
      doi:10.1001/jama.2024.3101. IC95% [0.01, 0.2]. Población: mujeres
      puérperas evaluadas en las primeras 48 horas postparto. TWEAK o
      T-ACE < 2 en postparto: excelente poder de exclusión (LR- 0.05),
      descartando prácticamente el trastorno en esta población.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6021
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE TRASTORNO POR CONSUMO DE ALCOHOL

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

El cuestionario AUDIT (≥ 8) es la herramienta más útil para identificar
trastorno por consumo de alcohol según el DSM-5 en adultos (LR+ 6.5; LR-
0.33). El AUDIT-C es adecuado para consumo de riesgo. En el postparto
inmediato, el AUDIT ≥ 4 confirma (LR+ 6.4) y las herramientas TWEAK/T-ACE
< 2 descartan con gran exactitud (LR- 0.05).

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
