---
titulo: Protocolo de insuficiencia aórtica
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Insuficiencia aórtica (regurgitación aórtica, valvulopatía aórtica
  incompetente).
version: 0.1.0-borrador

condicion:
  nombre: Insuficiencia aórtica
  codigos:
    holonmed: HM:6026

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0109   # Hipotensión arterial
  - HM:0600   # Signo de exploración
  - HM:0608   # Soplo cardíaco

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
  - nombre: Soplo diastólico precoz
    codigos: { holonmed: "HM:3116" }
    rol: prueba_especifica
    lr: 8.8
    lr_negativo: 0.2
    fuente: >-
      Choudhry NK et al. JAMA 1999;281:2231-8. PMID 10376577.
      doi:10.1001/jama.281.23.2231. LR+ IC95% [7.3, 11.0]. LR− IC95% [0.1,
      0.3]. El signo físico cardinal; su presencia confirma fuertemente
      (LR+ 8.8) y su ausencia reduce marcadamente la probabilidad (LR-
      0.20).

  - nombre: Maniobra de oclusión arterial transitoria
    codigos: { holonmed: "HM:3118" }
    rol: apoyo
    lr: 8.4
    lr_negativo: 0.3
    fuente: >-
      Choudhry NK et al. JAMA 1999;281:2231-8. PMID 10376577.
      doi:10.1001/jama.281.23.2231. LR+ IC95% [3.9, 18.0]. LR− IC95% [0.1,
      0.7]. La maniobra de oclusión con manguito acentúa el soplo
      diastólico con excelente rendimiento diagnóstico.

  - nombre: Presión de pulso amplia
    codigos: { holonmed: "HM:3117" }
    rol: apoyo
    # no_medido: signo hemodinámico clásico de regurgitación aórtica
    # moderada o severa

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6026
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE INSUFICIENCIA AÓRTICA

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

La auscultación de un soplo diastólico precoz es el signo más potente para
diagnosticar o descartar la insuficiencia aórtica (LR+ 8.8, LR- 0.20).
Maniobras como la oclusión arterial transitoria aumentan la sensibilidad
de la auscultación en casos dudosos.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
