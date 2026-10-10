---
titulo: Protocolo de alergia a penicilina
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Alergia a penicilina (hipersensibilidad a penicilina mediada por
  IgE, reacción alérgica a betalactámicos).
version: 0.1.0-borrador

condicion:
  nombre: Alergia a penicilina
  codigos:
    holonmed: HM:6028

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0600   # Signo de exploración

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.15
  # medida en: pacientes que autorreportan antecedentes de alergia a
  # penicilina confirmados por pruebas cutáneas
  # Salkind AR et al. JAMA 2001;285:2498-505. PMID 11368703.
  # doi:10.1001/jama.285.19.2498.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Prueba cutánea a determinantes de penicilina
    codigos: { holonmed: "HM:3126" }
    rol: prueba_especifica
    # no_medible: es el estándar de referencia (gold standard) contra el que
    # se calculan los cocientes de la historia clínica

  - nombre: Antecedente referido de alergia a penicilina
    codigos: { holonmed: "HM:3125" }
    rol: apoyo
    lr: 1.9
    lr_negativo: 0.5
    fuente: >-
      Salkind AR et al. JAMA 2001;285:2498-505. PMID 11368703.
      doi:10.1001/jama.285.19.2498. LR+ IC95% [1.5, 2.5]. LR− IC95% [0.4,
      0.6]. El autorreporte de alergia tiene muy baja exactitud
      discriminativa (LR+ 1.9); solo un 10-20% son verdaderos alérgicos.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6028
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ALERGIA A PENICILINA

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

Solo el 10% al 20% de los pacientes que refieren antecedentes de alergia a
la penicilina son verdaderamente alérgicos al evaluarse mediante pruebas
cutáneas. La historia clínica referida desplaza poco la probabilidad (LR+
1.9), mientras que una prueba cutánea negativa descarta con seguridad
secuelas graves.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
