---
titulo: Protocolo de rotura completa del manguito rotador
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Rotura completa del manguito rotador (rotura de espesor completo
  del manguito, desgarro transmural del manguito).
version: 0.1.0-borrador

condicion:
  nombre: Rotura completa del manguito rotador
  codigos:
    holonmed: HM:6014

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0500   # Síntoma neurológico

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
  - nombre: Signo de lag de rotación externa
    codigos: { holonmed: "HM:3056" }
    rol: prueba_especifica
    lr: 7.2
    fuente: >-
      Hermans J et al. JAMA 2013;310:837-47. PMID 23982370.
      doi:10.1001/jama.2013.276187. IC95% [1.7, 31]. El cociente más alto
      para la rotura completa, con intervalo muy ancho.

  - nombre: Signo de lag de rotación interna
    codigos: { holonmed: "HM:3057" }
    rol: prueba_sensible
    lr: 5.6
    lr_negativo: 0.04
    fuente: >-
      Hermans J et al. JAMA 2013;310:837-47. PMID 23982370.
      doi:10.1001/jama.2013.276187. LR+ IC95% [2.6, 12]. LR− IC95% [0.0,
      0.58]. Sirve en ambos sentidos y su normalidad es lo más preciso
      para descartar la rotura completa. Ojo con el extremo inferior del
      intervalo: llega a 0, lo que refleja series pequeñas, no certeza
      absoluta.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6014
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ROTURA COMPLETA DEL MANGUITO ROTADOR

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

La presencia de un signo de lag positivo, de rotación externa o interna,
fue lo más preciso para diagnosticar la rotura de espesor completo del
manguito rotador.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
