---
titulo: Protocolo de conmoción cerebral pediátrica
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Conmoción cerebral pediátrica (traumatismo craneoencefálico leve
  pediátrico, concusión cerebral en niños).
version: 0.1.0-borrador

condicion:
  nombre: Conmoción cerebral pediátrica
  codigos:
    holonmed: HM:6023

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0200   # Dolor
  - HM:0400   # Síntoma respiratorio
  - HM:0600   # Signo de exploración

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
  - nombre: Niebla mental
    codigos: { holonmed: "HM:3094" }
    rol: prueba_especifica
    lr: 11.9
    fuente: >-
      Shah SN et al. JAMA 2026. PMID 41941197. doi:10.1001/jama.2026.1233.
      IC95% [5.2, 27.0]. El síntoma cognitivo autoinformado con mayor LR
      positivo en la evaluación postraumática.

  - nombre: Punto próximo de convergencia anormal
    codigos: { holonmed: "HM:3097" }
    rol: prueba_especifica
    lr: 7.0
    fuente: >-
      Shah SN et al. JAMA 2026. PMID 41941197. doi:10.1001/jama.2026.1233.
      IC95% [3.1, 16.0]. El signo físico oculomotor más potente del examen
      vestibular/ocular motor (VOMS).

  - nombre: Fonofobia o sensibilidad al ruido
    codigos: { holonmed: "HM:3095" }
    rol: apoyo
    lr: 6.9
    fuente: >-
      Shah SN et al. JAMA 2026. PMID 41941197. doi:10.1001/jama.2026.1233.
      IC95% [3.4, 14.0]. Hipersensibilidad sensorial fuertemente
      indicativa de disfunción corticosensorial aguda.

  - nombre: Bradicardia
    codigos: { holonmed: "HM:0105" }
    rol: apoyo
    lr: 6.7
    fuente: >-
      Shah SN et al. JAMA 2026. PMID 41941197. doi:10.1001/jama.2026.1233.
      IC95% [3.5, 13.0]. Síntoma neurovegetativo precoz muy prevalente
      tras conmoción cerebral.

  - nombre: Fotofobia o sensibilidad a la luz
    codigos: { holonmed: "HM:3096" }
    rol: apoyo
    lr: 5.6
    fuente: >-
      Shah SN et al. JAMA 2026. PMID 41941197. doi:10.1001/jama.2026.1233.
      IC95% [2.9, 11.0]. Síntoma sensorial complementario de alta
      especificidad.

  - nombre: Movimientos de persecución suave anormales
    codigos: { holonmed: "HM:3098" }
    rol: apoyo
    lr: 4.5
    fuente: >-
      Shah SN et al. JAMA 2026. PMID 41941197. doi:10.1001/jama.2026.1233.
      IC95% [2.0, 10.0]. Signo exploratorio de afectación cerebelosa o de
      vías de seguimiento visual.

  - nombre: Sacadas oculares anormales
    codigos: { holonmed: "HM:3099" }
    rol: apoyo
    lr: 4.4
    fuente: >-
      Shah SN et al. JAMA 2026. PMID 41941197. doi:10.1001/jama.2026.1233.
      IC95% [2.0, 9.7]. Dismetría sacádica indicativa de alteración en la
      coordinación ocular rápida.

  - nombre: Dolor abdominal
    codigos: { holonmed: "HM:0201" }
    rol: prueba_sensible
    efecto: excluye
    dispara_si: ausente
    lr: 0.2
    fuente: >-
      Shah SN et al. JAMA 2026. PMID 41941197. doi:10.1001/jama.2026.1233.
      IC95% [0.1, 0.4]. La ausencia completa de cefalea reduce
      sustancialmente la probabilidad de conmoción cerebral (LR 0.20).

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6023
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE CONMOCIÓN CEREBRAL PEDIÁTRICA

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

Los síntomas referidos como sentirse 'en una niebla' (LR+ 11.9) y los
hallazgos del examen de motilidad ocular/convergencia (LR+ 7.0) son los
mejores predictores de conmoción cerebral pediátrica. La ausencia de
cefalea prácticamente descarta el cuadro (LR 0.20).

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
