---
titulo: Protocolo de luxación de cadera en el lactante
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Luxación de cadera en el lactante (displasia del desarrollo de la
  cadera, luxación congénita de cadera, displasia de cadera del lactante).
version: 0.1.0-borrador

condicion:
  nombre: Luxación de cadera en el lactante
  codigos:
    holonmed: HM:6019

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0600   # Signo de exploración

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.0094
  # medida en: lactantes de 3 meses o menores cribados con examen clínico y
  # ecografía (n = 37 859 caderas)
  # Singh A et al. JAMA 2024;331:1576-1585. PMID 38619828.
  # doi:10.1001/jama.2024.2404.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  # El índice declara «Presentación podálica al nacer» sin peso.
  # nota: OR 4.14 (IC95% 3.09-5.54) para el parto de nalgas; metaanálisis de
  # cohortes
  # Chen X et al. Orthop Traumatol Surg Res 2024;110:103836. PMID 38355007.
  # doi:10.1016/j.otsr.2024.103836.
  # El índice declara «Sexo femenino» sin peso.
  # nota: OR 6.97 (IC95% 5.18-9.39); metaanálisis de cohortes
  # Chen X et al. Orthop Traumatol Surg Res 2024;110:103836. PMID 38355007.
  # doi:10.1016/j.otsr.2024.103836.
  # El índice declara «Antecedente familiar de displasia de cadera» sin
  # peso.
  # nota: OR 4.07 (IC95% 2.20-7.52); metaanálisis de cohortes
  # Chen X et al. Orthop Traumatol Surg Res 2024;110:103836. PMID 38355007.
  # doi:10.1016/j.otsr.2024.103836.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Maniobras de Barlow y Ortolani positivas
    codigos: { holonmed: "HM:3075" }
    rol: prueba_especifica
    lr: 52.0
    lr_negativo: 0.55
    fuente: >-
      Singh A et al. JAMA 2024;331:1576-1585. PMID 38619828.
      doi:10.1001/jama.2024.2404. LR+ IC95% [21, 127]. LR− IC95% [0.37,
      0.82]. Población: lactantes de 3 meses o menores (n = 44 827 caderas
      en 8 estudios). Maniobras de Barlow y Ortolani positivas: el signo
      que confirma la luxación inestable. Cuando es positiva eleva la
      probabilidad pretest de 0.94% a más del 33% (LR+ 52); su negatividad
      no descarta la displasia (LR- 0.55).

  - nombre: Limitación de la abducción de la cadera en el lactante
    codigos: { holonmed: "HM:3076" }
    rol: apoyo
    lr: 3.6
    lr_negativo: 0.91
    fuente: >-
      Singh A et al. JAMA 2024;331:1576-1585. PMID 38619828.
      doi:10.1001/jama.2024.2404. LR+ IC95% [0.72, 18]. LR− IC95% [0.76,
      1.1]. Población: lactantes de 3 meses o menores (n = 22 472 caderas
      en 3 estudios). Limitación de la abducción: no concluyente por sí
      sola en menores de 3 meses; el intervalo de confianza abarca el 1.0
      y la sensibilidad es de apenas 13%.

  - nombre: Chasquido o click articular de cadera en el lactante
    codigos: { holonmed: "HM:3077" }
    rol: apoyo
    lr: 1.6
    lr_negativo: 0.95
    fuente: >-
      Singh A et al. JAMA 2024;331:1576-1585. PMID 38619828.
      doi:10.1001/jama.2024.2404. LR+ IC95% [0.91, 2.8]. LR− IC95% [0.88,
      1.0]. Población: lactantes de 3 meses o menores (n = 13 096 caderas
      en 1 estudio). Chasquido o click articular aislado: hallazgo
      inespecífico sin valor discriminativo para luxación o displasia (el
      intervalo cruza el neutro).

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6019
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE LUXACIÓN DE CADERA EN EL LACTANTE

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

En lactantes evaluados para displasia del desarrollo de la cadera, la
prevalencia de luxación es de 0.94%. Las maniobras de Barlow y Ortolani
positivas son el hallazgo más fuertemente asociado (LR+ 52). La abducción
limitada o el chasquido aislado carecen de utilidad diagnóstica clara.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
