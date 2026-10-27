---
titulo: Protocolo de trastorno de estrés postraumático
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Trastorno de estrés postraumático (TEPT, PTSD, estrés
  postraumático).
version: 0.1.0-borrador

condicion:
  nombre: Trastorno de estrés postraumático
  codigos:
    holonmed: HM:6039

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:3153   # Trauma Screening Questionnaire positivo

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
  - nombre: Trauma Screening Questionnaire positivo
    codigos: { holonmed: "HM:3153" }
    rol: prueba_sensible
    efecto: evidencia
    lr: 1.3
    lr_negativo: 0.2
    fuente: >-
      Spoont MR et al. JAMA 2015;314:501-10. PMID 26241601.
      doi:10.1001/jama.2015.7877. LR+ IC95% [1.2, 1.4]. LR− IC95% [0.1,
      0.41]. Población: 152 pacientes, los de la fila del Trauma Screening
      Questionnaire; la corrección publica además VPP 44 y VPN 89 para esa
      misma fila. Solo decide cuando es NEGATIVO. Con sensibilidad del 95%
      y LR− 0.20, un TSQ negativo hace el trastorno bastante improbable.
      Un TSQ positivo no decide nada: LR+ 1.3 sobre una especificidad del
      26% apenas mueve la probabilidad, así que cribar positivo obliga a
      la entrevista diagnóstica y no la sustituye.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6039
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE TRASTORNO DE ESTRÉS POSTRAUMÁTICO

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

Dos instrumentos de cribado, el PC-PTSD y el PTSD Checklist, muestran
características de rendimiento razonables para su uso en consultas de
atención primaria o en entornos comunitarios con poblaciones de alto
riesgo. Ambos son fáciles de administrar e interpretar y pueden
incorporarse sin dificultad a una práctica clínica con poco tiempo.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
