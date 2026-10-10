---
titulo: Protocolo de derrame pleural exudativo
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Derrame pleural exudativo (exudado pleural, derrame pleural tipo
  exudado).
version: 0.1.0-borrador

condicion:
  nombre: Derrame pleural exudativo
  codigos:
    snomed: 13841000119107
    cie10: J90
    holonmed: HM:6005

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0400   # Síntoma respiratorio
  - HM:0700   # Alteración analítica
  - HM:0730   # Alteración enzimática

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
  - nombre: Colesterol elevado en líquido pleural
    codigos: { holonmed: "HM:3008" }
    rol: prueba_especifica
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ None para colesterol pleural > 55 mg/dL
    # Wilcox ME et al. JAMA 2014;311:2422-31. PMID 24938565.
    # doi:10.1001/jama.2014.5552. umbral: colesterol pleural > 55 mg/dL.
    # Rango entre estudios, sin estimación agrupada ni intervalo de
    # confianza en el abstract. Se lee como «desplaza mucho», no como un
    # valor. El indicador aislado más potente para clasificar el derrame.

  - nombre: LDH elevada en líquido pleural
    codigos: { holonmed: "HM:3009" }
    rol: prueba_especifica
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ 18 para LDH pleural > 200 U/L
    # Wilcox ME et al. JAMA 2014;311:2422-31. PMID 24938565.
    # doi:10.1001/jama.2014.5552. IC95% [6.8, 46]; umbral: LDH pleural > 200
    # U/L. Confirma exudado con un intervalo estrecho y reproducible.

  - nombre: Cociente colesterol pleural/sérico elevado
    codigos: { holonmed: "HM:3010" }
    rol: prueba_especifica
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ 14 para cociente > 0.3
    # Wilcox ME et al. JAMA 2014;311:2422-31. PMID 24938565.
    # doi:10.1001/jama.2014.5552. IC95% [5.5, 38]; umbral: cociente > 0.3.
    # Alternativa al colesterol absoluto cuando se dispone del sérico.

  - nombre: Criterios de Light
    codigos: { holonmed: "HM:3011" }
    rol: prueba_sensible
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR− 0.04 para ausencia de los tres criterios
    # Wilcox ME et al. JAMA 2014;311:2422-31. PMID 24938565.
    # doi:10.1001/jama.2014.5552. IC95% [0.02, 0.11]; umbral: ausencia de
    # los tres criterios. Su valor está en el negativo: si no se cumple
    # ninguno de los tres, el exudado queda prácticamente descartado.

  - nombre: Derrame pleural
    codigos: { holonmed: "HM:3007" }
    rol: manifestacion
    # no_medible: es la condición previa, no una prueba: sin derrame no hay
    # nada que clasificar como exudado o trasudado

laboratorio:
  - parametro: Colesterol en líquido pleural
    corte_superior: 55
    termino_si_alto: Colesterol elevado en líquido pleural
    codigos: { holonmed: "HM:3008" }

  - parametro: LDH en líquido pleural
    corte_superior: 200
    termino_si_alto: LDH elevada en líquido pleural
    codigos: { holonmed: "HM:3009" }

  - parametro: Colesterol pleural / colesterol sérico
    corte_superior: 0.3
    termino_si_alto: Cociente colesterol pleural/sérico elevado
    codigos: { holonmed: "HM:3010" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6005
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE DERRAME PLEURAL EXUDATIVO

ROL: <!-- especialidad y postura: «cardiólogo experto, basado en evidencia» -->

## Contexto fisiopatológico

<!-- El índice no guarda prosa. Estas tres líneas son las que hacen que
     el modelo reconozca el cuadro y no sólo sus términos. -->

- **Dónde**: <!-- órgano, territorio, compartimento -->
- **Cómo**: <!-- mecanismo -->
- **Por qué**: <!-- causas frecuentes -->

## Instrucciones de extracción

1. Analiza los signos vitales, la exploración y el texto libre.
2. **Interpreta los valores numéricos** con los cortes declarados
   arriba. Extrae el hallazgo clínico, nunca la cifra suelta:
   - «Colesterol en líquido pleural 72» → *Colesterol elevado en líquido pleural*
   - «LDH en líquido pleural 260» → *LDH elevada en líquido pleural*
   - «Colesterol pleural / colesterol sérico 0» → *Cociente colesterol pleural/sérico elevado*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
