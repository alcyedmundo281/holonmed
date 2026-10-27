---
titulo: Protocolo de absceso de partes blandas
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Absceso de partes blandas (absceso cutáneo, absceso de piel y
  partes blandas).
version: 0.1.0-borrador

condicion:
  nombre: Absceso de partes blandas
  codigos:
    holonmed: HM:6041

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0900   # Hallazgo de imagen

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
  - nombre: Colección de partes blandas en ecografía
    codigos: { holonmed: "HM:3166" }
    rol: imagen
    lr: 10.9
    lr_negativo: 0.01
    fuente: >-
      Gottlieb M et al. Ann Emerg Med 2020;76:67-77. PMID 32081383.
      doi:10.1016/j.annemergmed.2020.01.004. LR+ IC95% [6.2, 19.2]. LR−
      IC95% [0.001, 0.06]. Población: adultos en urgencias con infección
      de piel y partes blandas, sospecha de absceso o celulitis; subgrupo
      de adultos de un metaanálisis de 14 estudios prospectivos (2 656
      pacientes en total). Colección confirmada: drena o deriva para
      drenaje. Sin colección, solo empedrado: antibiótico y control, no
      incisión a ciegas. Y antes de cortar, Doppler color: un
      seudoaneurisma o un vaso pueden verse como una colección.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6041
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ABSCESO DE PARTES BLANDAS

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

El POCUS tiene buena exactitud diagnóstica para distinguir absceso de
celulitis y llevó a un cambio correcto de manejo en el 10% de los casos.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
