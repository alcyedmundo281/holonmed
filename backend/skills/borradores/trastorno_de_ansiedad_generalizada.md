---
titulo: Protocolo de trastorno de ansiedad generalizada
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Trastorno de ansiedad generalizada (TAG, GAD, ansiedad crónica).
version: 0.1.0-borrador

condicion:
  nombre: Trastorno de ansiedad generalizada
  codigos:
    holonmed: HM:6031

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:3137   # Cuestionario GAD-7 positivo

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.092
  # medida en: pacientes adultos en centros de atención primaria
  # Herr NR et al. JAMA 2014;312:78-84. PMID 25058220.
  # doi:10.1001/jama.2014.5950.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Cuestionario GAD-7 positivo
    codigos: { holonmed: "HM:3137" }
    rol: prueba_especifica
    lr: 5.1
    lr_negativo: 0.13
    fuente: >-
      Herr NR et al. JAMA 2014;312:78-84. PMID 25058220.
      doi:10.1001/jama.2014.5950. LR+ IC95% [4.3, 6.0]. LR− IC95% [0.07,
      0.25]. La escala GAD-7 es el mejor instrumento de cribado en
      atención primaria, con alta capacidad tanto confirmatoria como de
      exclusión (LR- 0.13).

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6031
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE TRASTORNO DE ANSIEDAD GENERALIZADA

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

El cuestionario GAD-7 presenta excelentes características de rendimiento
diagnóstico para detectar el trastorno de ansiedad generalizada en
atención primaria (LR+ 5.1, LR- 0.13) y es factible de implementar en la
práctica clínica diaria.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
