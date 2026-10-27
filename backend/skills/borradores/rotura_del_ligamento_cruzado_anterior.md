---
titulo: Protocolo de rotura del ligamento cruzado anterior
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Rotura del ligamento cruzado anterior (desgarro del LCA, rotura
  del ligamento cruzado de la rodilla).
version: 0.1.0-borrador

condicion:
  nombre: Rotura del ligamento cruzado anterior
  codigos:
    holonmed: HM:6027

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
  - nombre: Prueba de Lachman positiva
    codigos: { holonmed: "HM:3119" }
    rol: prueba_especifica
    lr: 25.0
    lr_negativo: 0.1
    fuente: >-
      Solomon DH et al. JAMA 2001;286:1610-20. PMID 11585485.
      doi:10.1001/jama.286.13.1610. LR+ IC95% [2.7, 250.0]. LR− IC95%
      [0.04, 0.2]. La prueba clínica individual de referencia; altamente
      sensible y específica para confirmar o descartar rotura del LCA.

  - nombre: Examen compuesto de rodilla positivo para ligamento cruzado anterior
    codigos: { holonmed: "HM:3123" }
    rol: prueba_especifica
    lr: 25.0
    lr_negativo: 0.04
    fuente: >-
      Solomon DH et al. JAMA 2001;286:1610-20. PMID 11585485.
      doi:10.1001/jama.286.13.1610. LR+ IC95% [2.7, 250.0]. LR− IC95%
      [0.01, 0.4]. La combinación de maniobras clínicas por un examinador
      entrenado descarta con fiabilidad casi absoluta (LR- 0.04).

  - nombre: Prueba del cajón anterior de rodilla positiva
    codigos: { holonmed: "HM:3120" }
    rol: apoyo
    lr: 3.8
    fuente: >-
      Solomon DH et al. JAMA 2001;286:1610-20. PMID 11585485.
      doi:10.1001/jama.286.13.1610. IC95% [0.7, 22.0]. Maniobra clásica
      pero con menor sensibilidad que la prueba de Lachman debido al
      bloqueo de isquiotibiales.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6027
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ROTURA DEL LIGAMENTO CRUZADO ANTERIOR

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

La prueba de Lachman es la maniobra con mayor exactitud diagnóstica para
confirmar (LR+ 25) o descartar (LR- 0.1) la rotura del ligamento cruzado
anterior, superando al cajón anterior.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
