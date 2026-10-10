---
titulo: Protocolo de bocio
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Bocio (tiromegalia, agrandamiento tiroideo, hipertrofia de la
  glándula tiroides, bocio tiroideo).
version: 0.1.0-borrador

condicion:
  nombre: Bocio
  codigos:
    snomed: 3716002
    cie10: E04.9
    holonmed: HM:6048

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
  # El índice declara «Gestación o periodo puerperal» sin peso.
  # nota: en Bruselas, con aporte de yodo en el límite bajo, cerca del 10%
  # de las gestantes tenía bocio en el parto, solo en parte reversible en el
  # posparto. Sin grupo de no gestantes, así que es un riesgo absoluto en
  # una zona con poco yodo
  # Glinoer D. J Endocrinol Invest 1993;16:374-8. PMID 8320430.
  # doi:10.1007/BF03348861.
  # El índice declara «Edad avanzada» sin peso.
  # nota: asociación independiente con el bocio ecográfico en varones y en
  # mujeres; el resumen no da su OR. SHIP, 3915 adultos de 20 a 79 años de
  # una región antes deficiente en yodo
  # Völzke H et al. Exp Clin Endocrinol Diabetes 2005;113:507-15. PMID
  # 16235152. doi:10.1055/s-2005-865741.
  # El índice declara «Tabaquismo actual» sin peso.
  # nota: asociación independiente y, según la fuente, fuerte en varones y
  # en mujeres; el resumen no da su OR. SHIP, 3915 adultos
  # Völzke H et al. Exp Clin Endocrinol Diabetes 2005;113:507-15. PMID
  # 16235152. doi:10.1055/s-2005-865741.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Agrandamiento tiroideo palpable en posición neutra
    codigos: { holonmed: "HM:3187" }
    rol: prueba_especifica
    lr: 26.3
    lr_negativo: 0.4
    fuente: >-
      Siminoski K. JAMA 1995;273:813-7. PMID 7861577. Población: adultos
      evaluados mediante inspección y palpación con el cuello en posición
      neutra frente a ecografía tiroidea como estándar de referencia. Un
      tiroides netamente visible o palpable con el cuello en posición
      neutra confirma bocio con muy alta probabilidad clínica (LR+ 26.3).

  - nombre: Lóbulo tiroideo palpable mayor que la falange distal del pulgar
    codigos: { holonmed: "HM:3188" }
    rol: prueba_sensible
    # varias aristas del índice publican cociente para este hallazgo
    # (poblaciones o estudios distintos). No se traslada ninguno: contarlos
    # todos duplicaría la evidencia y elegir uno es decidir qué población es
    # la tuya. Elige uno, escribe `lr`/`lr_negativo` y su `fuente`.
    # candidata 1: LR+ 3.0 · LR− 0.3. Población: niños en edad escolar
    # evaluados según el criterio de falange distal del pulgar de la OMS
    # frente a ecografía tiroidea. Siminoski K. JAMA 1995;273:813-7. PMID
    # 7861577.
    # candidata 2: LR+ 4.7 · LR− 0.08. Población: mujeres gestantes
    # evaluadas según el criterio de falange distal del pulgar de la OMS
    # frente a ecografía tiroidea. Siminoski K. JAMA 1995;273:813-7. PMID
    # 7861577.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6048
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE BOCIO

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
