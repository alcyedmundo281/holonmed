---
titulo: Protocolo de glaucoma primario de ángulo abierto
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Glaucoma primario de ángulo abierto (GPAA, glaucoma crónico
  simple).
version: 0.1.0-borrador

condicion:
  nombre: Glaucoma primario de ángulo abierto
  codigos:
    holonmed: HM:6022

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0600   # Signo de exploración

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.02
  # medida en: adultos mayores de 40 años en cribado poblacional
  # Hollands H et al. JAMA 2013;309:2035-42. PMID 23677315.
  # doi:10.1001/jama.2013.5099.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Relación copa-disco aumentada
    codigos: { holonmed: "HM:3088" }
    rol: prueba_especifica
    lr: 14.0
    fuente: >-
      Hollands H et al. JAMA 2013;309:2035-42. PMID 23677315.
      doi:10.1001/jama.2013.5099. IC95% [6.3, 30.0]. El hallazgo
      oftalmoscópico aislado más potente para confirmar sospecha de
      glaucoma.

  - nombre: Asimetría de la relación copa-disco
    codigos: { holonmed: "HM:3089" }
    rol: prueba_especifica
    lr: 7.3
    fuente: >-
      Hollands H et al. JAMA 2013;309:2035-42. PMID 23677315.
      doi:10.1001/jama.2013.5099. IC95% [3.4, 16.0]. La diferencia de
      excavación entre ambos ojos aumenta marcadamente la probabilidad.

  - nombre: Hemorragia en astilla del disco óptico
    codigos: { holonmed: "HM:3090" }
    rol: prueba_especifica
    lr: 12.0
    fuente: >-
      Hollands H et al. JAMA 2013;309:2035-42. PMID 23677315.
      doi:10.1001/jama.2013.5099. IC95% [2.9, 48.0]. Signo patognomónico
      de daño microvascular y progresión activa de la neuropatía
      glaucomatosa.

  - nombre: Presión intraocular elevada
    codigos: { holonmed: "HM:3091" }
    rol: apoyo
    lr: 13.0
    lr_negativo: 0.65
    fuente: >-
      Hollands H et al. JAMA 2013;309:2035-42. PMID 23677315.
      doi:10.1001/jama.2013.5099. LR+ IC95% [8.2, 21.0]. LR− IC95% [0.55,
      0.76]. Confirma con fuerza pero una PIO normal no descarta (glaucoma
      de tensión normal).

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6022
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE GLAUCOMA PRIMARIO DE ÁNGULO ABIERTO

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

La evaluación del disco óptico (relación copa-disco >= 0.7, asimetría y
hemorragias en astilla) es más informativa que la tonometría aislada para
el diagnóstico de glaucoma.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
