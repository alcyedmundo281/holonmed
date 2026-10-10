---
titulo: Protocolo de melanoma cutáneo
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Melanoma cutáneo (melanoma maligno, cáncer de piel tipo melanoma).
version: 0.1.0-borrador

condicion:
  nombre: Melanoma cutáneo
  codigos:
    holonmed: HM:6033

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
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
  - nombre: Criterios ABCD de lesión pigmentada positivos
    codigos: { holonmed: "HM:3139" }
    rol: prueba_especifica
    lr: 46.0
    lr_negativo: 0.08
    fuente: >-
      Whited JD et al. JAMA 1998;279:696-701. PMID 9496989.
      doi:10.1001/jama.279.9.696. LR+ IC95% [18.4, 96.0]. LR− IC95% [0.04,
      0.18]. La regla clínica ABCD (Asimetría, Bordes, Color, Diámetro
      >6mm) es altamente sensible y específica.

  - nombre: Asimetría y bordes irregulares en lesión cutánea
    codigos: { holonmed: "HM:3140" }
    rol: apoyo
    # no_medido: componente de los criterios semiológicos combinados de
    # dermatología clínica

  - nombre: Color heterogéneo y diámetro mayor de 6 mm en lesión cutánea
    codigos: { holonmed: "HM:3141" }
    rol: apoyo
    # no_medido: componente de los criterios semiológicos combinados de
    # dermatología clínica

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6033
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE MELANOMA CUTÁNEO

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

La detección precoz del melanoma mediante la regla semiológica ABCD
(Asimetría, Bordes irregulares, Color heterogéneo y Diámetro >6 mm)
presenta una sensibilidad del 92-100% y una especificidad del 98%, siendo
la principal herramienta clínica de triaje y derivación para biopsia.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
