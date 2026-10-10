---
titulo: Protocolo de hipertensión arterial en adultos
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Hipertensión arterial en adultos (HTA esencial, hipertensión
  arterial primaria en adultos).
version: 0.1.0-borrador

condicion:
  nombre: Hipertensión arterial en adultos
  codigos:
    holonmed: HM:6029

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0109   # Hipotensión arterial

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
  - nombre: Presión arterial en consulta mayor o igual a 140/90 mmHg
    codigos: { holonmed: "HM:3127" }
    rol: prueba_especifica
    lr: 4.2
    lr_negativo: 0.56
    fuente: >-
      Viera AJ et al. JAMA 2021;326:339-347. PMID 34313682.
      doi:10.1001/jama.2021.4533. LR+ IC95% [2.9, 6.1]. LR− IC95% [0.46,
      0.68]. Una cifra elevada en consulta quintuplica aproximadamente la
      odds pero exige confirmación fuera de consulta por bata blanca.

  - nombre: Automonitorización domiciliaria (AMPA) mayor o igual a 135/85 mmHg
    codigos: { holonmed: "HM:3128" }
    rol: prueba_especifica
    lr: 3.1
    lr_negativo: 0.33
    fuente: >-
      Viera AJ et al. JAMA 2021;326:339-347. PMID 34313682.
      doi:10.1001/jama.2021.4533. LR+ IC95% [2.3, 4.2]. LR− IC95% [0.24,
      0.46]. La automonitorización domiciliaria presenta un excelente
      cociente negativo (LR- 0.33) para descartar hipertensión mantenida.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6029
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE HIPERTENSIÓN ARTERIAL EN ADULTOS

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

La medición de la presión arterial en consulta es una prueba de cribado
útil (LR+ 4.2), pero la automonitorización domiciliaria (AMPA) o el MAPA
son necesarios para confirmar el diagnóstico definitivo y descartar la
hipertensión de bata blanca.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
