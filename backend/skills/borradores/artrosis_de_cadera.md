---
titulo: Protocolo de artrosis de cadera
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Artrosis de cadera (coxartrosis, osteoartritis de cadera).
version: 0.1.0-borrador

condicion:
  nombre: Artrosis de cadera
  codigos:
    holonmed: HM:6012

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0208   # Lumbalgia
  - HM:0500   # Síntoma neurológico
  - HM:3047   # Antecedente familiar de artrosis
  - HM:3048   # Antecedente personal de artrosis de rodilla

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.34
  # medida en: pacientes que consultan en atención primaria por dolor de
  # cadera o inguinal
  # Metcalfe D et al. JAMA 2019;322:2323-2333. PMID 31846019.
  # doi:10.1001/jama.2019.19413.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Dolor posterior de cadera al ponerse en cuclillas
    codigos: { holonmed: "HM:3041" }
    rol: prueba_especifica
    lr: 6.1
    fuente: >-
      Metcalfe D et al. JAMA 2019;322:2323-2333. PMID 31846019.
      doi:10.1001/jama.2019.19413. IC95% [1.3, 29]. El cociente más alto,
      pero con intervalo muy ancho: el extremo inferior roza el 1.3, casi
      irrelevante.

  - nombre: Dolor inguinal a la abducción o aducción pasiva
    codigos: { holonmed: "HM:3042" }
    rol: prueba_especifica
    lr: 5.7
    fuente: >-
      Metcalfe D et al. JAMA 2019;322:2323-2333. PMID 31846019.
      doi:10.1001/jama.2019.19413. IC95% [1.6, 20].

  - nombre: Debilidad de los abductores de cadera
    codigos: { holonmed: "HM:3043" }
    rol: prueba_especifica
    lr: 4.5
    fuente: >-
      Metcalfe D et al. JAMA 2019;322:2323-2333. PMID 31846019.
      doi:10.1001/jama.2019.19413. IC95% [2.4, 8.4]. Intervalo más
      estrecho que los anteriores; en la práctica, más fiable pese a un
      cociente algo menor.

  - nombre: Aducción pasiva de cadera disminuida
    codigos: { holonmed: "HM:3044" }
    rol: prueba_sensible
    lr: 4.2
    lr_negativo: 0.25
    fuente: >-
      Metcalfe D et al. JAMA 2019;322:2323-2333. PMID 31846019.
      doi:10.1001/jama.2019.19413. LR+ IC95% [3.0, 6.0]. LR− IC95% [0.11,
      0.54]. La fuente lo expresa como el valor de encontrar una aducción
      pasiva NORMAL, que es el cociente negativo de este hallazgo. El
      hallazgo más equilibrado y el único que sirve en los dos sentidos:
      su presencia apoya y su normalidad es lo que mejor descarta.

  - nombre: Rotación interna de cadera disminuida
    codigos: { holonmed: "HM:3045" }
    rol: prueba_sensible
    lr: 3.2
    fuente: >-
      Metcalfe D et al. JAMA 2019;322:2323-2333. PMID 31846019.
      doi:10.1001/jama.2019.19413. IC95% [1.7, 6.0].

  - nombre: Dolor al subir escaleras o cuestas
    codigos: { holonmed: "HM:3046" }
    rol: apoyo
    lr: 2.1
    fuente: >-
      Metcalfe D et al. JAMA 2019;322:2323-2333. PMID 31846019.
      doi:10.1001/jama.2019.19413. IC95% [1.1, 3.8]. La fuente agrupa tres
      datos de anamnesis con idéntico cociente de 2.1; el intervalo citado
      es el más ancho de los tres.

  - nombre: Antecedente familiar de artrosis
    codigos: { holonmed: "HM:3047" }
    rol: apoyo
    lr: 2.1
    fuente: >-
      Metcalfe D et al. JAMA 2019;322:2323-2333. PMID 31846019.
      doi:10.1001/jama.2019.19413. IC95% [1.1, 3.8]. Mismo cociente
      agrupado que el dolor al subir escaleras.

  - nombre: Antecedente personal de artrosis de rodilla
    codigos: { holonmed: "HM:3048" }
    rol: apoyo
    lr: 2.1
    fuente: >-
      Metcalfe D et al. JAMA 2019;322:2323-2333. PMID 31846019.
      doi:10.1001/jama.2019.19413. IC95% [1.1, 3.8]. Mismo cociente
      agrupado que el dolor al subir escaleras.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6012
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ARTROSIS DE CADERA

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

Pruebas sencillas de movilidad de la cadera, observando si aparece dolor
durante el movimiento, distinguen a los pacientes con más probabilidad de
tener artrosis en la radiografía. Una combinación de hallazgos detecta con
eficiencia a quienes tienen artrosis grave.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
