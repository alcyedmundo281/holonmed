---
titulo: Protocolo de esplenomegalia
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Esplenomegalia (bazo aumentado de tamaño, hipertrofia esplénica,
  bazo palpable).
version: 0.1.0-borrador

condicion:
  nombre: Esplenomegalia
  codigos:
    snomed: 16294009
    cie10: R16.1
    holonmed: HM:6047

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
  - nombre: Esplenomegalia
    codigos: { holonmed: "HM:0603" }
    rol: prueba_especifica
    lr: 8.2
    lr_negativo: 0.41
    fuente: >-
      Grover SA et al. JAMA 1993;270:2218-21. PMID 8411607. Población:
      adultos evaluados mediante palpación abdominal supina o bimanual
      frente a ecografía o gammagrafía esplénica como estándar de
      referencia (pmid:8411607). Un polo esplénico palpable por debajo del
      reborde costal en adultos sin deformidad torácica previa confirma
      esplenomegalia con alta probabilidad (LR+ 8.2).

  - nombre: Matidez en el espacio de Traube
    codigos: { holonmed: "HM:3184" }
    rol: apoyo
    lr: 2.3
    lr_negativo: 0.48
    fuente: >-
      Grover SA et al. JAMA 1993;270:2218-21. PMID 8411607. Población:
      adultos evaluados mediante percusión del espacio semilunar de Traube
      frente a estándar de referencia por imagen (pmid:8411607). La
      matidez en el espacio de Traube eleva la sospecha de bazo agrandado
      e indica proceder a palpación orientada o ecografía.

  - nombre: Signo de percusión de Castell
    codigos: { holonmed: "HM:3185" }
    rol: prueba_sensible
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Grover SA et al. JAMA 1993;270:2218-21. PMID 8411607. Población:
    # adultos evaluados mediante percusión en el espacio intercostal más
    # inferior en la línea axilar anterior durante inspiración profunda
    # frente a estándar de imagen. El viraje de timpanismo espiratorio a
    # matidez inspiratoria en la línea axilar anterior es la maniobra
    # percutoria más sensible para detectar esplenomegalia incipiente.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6047
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ESPLENOMEGALIA

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

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
