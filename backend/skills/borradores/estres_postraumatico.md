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
