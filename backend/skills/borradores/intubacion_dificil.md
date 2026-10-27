---
titulo: Protocolo de intubación difícil
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Intubación difícil (vía aérea difícil, intubación orotraqueal
  dificultosa, laringoscopia difícil).
version: 0.1.0-borrador

condicion:
  nombre: Intubación difícil
  codigos:
    holonmed: HM:6020

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0600   # Signo de exploración

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.1
  # medida en: pacientes adultos quirúrgicos generales candidatos a
  # intubación (n = 33 559 en 62 estudios)
  # Detsky ME et al. JAMA 2019;321:493-503. PMID 30721300.
  # doi:10.1001/jama.2018.21413.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  # El índice declara «Obesidad con IMC elevado» sin peso.
  # nota: IMC de 35 o más, OR 1.34 (IC95% 1.19-1.51) ajustado por las demás
  # covariables; cohorte de 91 332 pacientes consecutivos del registro danés
  # de anestesia. La fuente lo califica de predictor débil
  # Lundstrøm LH et al. Anesthesiology 2009;110:266-74. PMID 19194154.
  # doi:10.1097/ALN.0b013e318194cac8.
  # El índice declara «Movilidad cervical limitada o artropatía cervical»
  # sin peso.
  # nota: aumento estadísticamente significativo de la intubación difícil en
  # las dos franjas de edad (menores y mayores de 60 años); cohorte
  # retrospectiva de 14 053 pacientes. El resumen no da su OR
  # Mashour GA et al. J Neurosurg Anesthesiol 2008;20:110-5. PMID 18362772.
  # doi:10.1097/ANA.0b013e318166dd00.
  # El índice declara «Antecedente personal de intubación difícil» sin peso.
  # nota: antecedente documentado; la fuente lo califica de predictor fuerte
  # e identifica al 30% de las intubaciones difíciles posteriores. 15 499
  # pacientes anestesiados más de una vez, registro danés de anestesia. El
  # resumen no da su OR
  # Lundstrøm LH et al. Anaesthesia 2009;64:1081-8. PMID 19735399.
  # doi:10.1111/j.1365-2044.2009.06057.x.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Test de mordida del labio superior clase 3
    codigos: { holonmed: "HM:3078" }
    rol: prueba_especifica
    lr: 14.0
    fuente: >-
      Detsky ME et al. JAMA 2019;321:493-503. PMID 30721300.
      doi:10.1001/jama.2018.21413. IC95% [8.9, 22]. Población: pacientes
      quirúrgicos adultos (n = 33 559). Test de mordida del labio superior
      clase 3: el predictor físico individual más potente. Con LR+ 14 y
      especificidad del 96%, eleva la probabilidad postest de 10% a más de
      60%.

  - nombre: Distancia hiodomentoniana o tiromentoniana corta
    codigos: { holonmed: "HM:3079" }
    rol: prueba_especifica
    lr: 6.4
    fuente: >-
      Detsky ME et al. JAMA 2019;321:493-503. PMID 30721300.
      doi:10.1001/jama.2018.21413. IC95% [4.1, 10]. Población: pacientes
      quirúrgicos adultos. Distancia hiodomentoniana o tiromentoniana
      corta (<3 a 5.5 cm): alta especificidad (97%) con LR+ 6.4.

  - nombre: Retrognatia o longitud mandibular reducida
    codigos: { holonmed: "HM:3080" }
    rol: prueba_especifica
    lr: 6.0
    fuente: >-
      Detsky ME et al. JAMA 2019;321:493-503. PMID 30721300.
      doi:10.1001/jama.2018.21413. IC95% [3.1, 11]. Población: pacientes
      quirúrgicos adultos. Retrognatia (mandíbula <9 cm): especificidad
      del 98% con LR+ 6.0.

  - nombre: Score de Wilson de riesgo aumentado
    codigos: { holonmed: "HM:3082" }
    rol: prueba_especifica
    lr: 9.1
    fuente: >-
      Detsky ME et al. JAMA 2019;321:493-503. PMID 30721300.
      doi:10.1001/jama.2018.21413. IC95% [5.1, 16]. Población: pacientes
      quirúrgicos adultos. Score de Wilson de riesgo aumentado:
      combinación de 5 factores anatómicos con LR+ 9.1 y especificidad del
      95%.

  - nombre: Escala de Mallampati modificada clase 3 o 4
    codigos: { holonmed: "HM:3081" }
    rol: prueba_especifica
    lr: 4.1
    fuente: >-
      Detsky ME et al. JAMA 2019;321:493-503. PMID 30721300.
      doi:10.1001/jama.2018.21413. IC95% [3.0, 5.6]. Población: pacientes
      quirúrgicos adultos. Escala de Mallampati modificada (clase 3 o 4):
      el test más difundido; aporta un LR+ de 4.1 pero con especificidad
      moderada (87%).

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6020
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE INTUBACIÓN DIFÍCIL

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

Varios hallazgos de exploración física simple permiten identificar a
pacientes con alta probabilidad de intubación difícil (especialmente el
test de mordida del labio superior, LR+ 14), pero ningún hallazgo clínico
permite excluir de forma fiable una vía aérea difícil.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
