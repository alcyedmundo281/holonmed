---
titulo: Protocolo de aneurisma de aorta abdominal
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Aneurisma de aorta abdominal (AAA, aneurisma aórtico abdominal).
version: 0.1.0-borrador

condicion:
  nombre: Aneurisma de aorta abdominal
  codigos:
    snomed: 233985008
    cie10: I71.4
    holonmed: HM:6006

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0600   # Signo de exploración

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.014
  # medida en: 73 451 veteranos de 50 a 79 años sin aneurisma conocido,
  # cribados con ecografía en 15 centros de Estados Unidos; 1031 de ellos
  # Lederle FA et al. Ann Intern Med 1997;126:441-9. PMID 9072929.
  # doi:10.7326/0003-4819-126-6-199703150-00004.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  # El índice declara «Tabaquismo» sin peso.
  # nota: OR 5.57 (IC95% 4.24-7.31) para aneurisma de 4.0 cm o mayor frente
  # a aorta normal, en análisis multivariable. Crece con los años fumados y
  # baja con los años sin fumar
  # Lederle FA et al. Ann Intern Med 1997;126:441-9. PMID 9072929.
  # doi:10.7326/0003-4819-126-6-199703150-00004.
  # El índice declara «Antecedente familiar de aneurisma de aorta abdominal»
  # sin peso.
  # nota: OR 1.95 (IC95% 1.56-2.43) en análisis multivariable
  # Lederle FA et al. Ann Intern Med 1997;126:441-9. PMID 9072929.
  # doi:10.7326/0003-4819-126-6-199703150-00004.
  # El índice declara «Edad» sin peso.
  # nota: asociación independiente; el resumen no da su OR
  # Lederle FA et al. Ann Intern Med 1997;126:441-9. PMID 9072929.
  # doi:10.7326/0003-4819-126-6-199703150-00004.
  # El índice declara «Talla alta» sin peso.
  # nota: asociación independiente; el resumen no da su OR
  # Lederle FA et al. Ann Intern Med 1997;126:441-9. PMID 9072929.
  # doi:10.7326/0003-4819-126-6-199703150-00004.
  # El índice declara «Enfermedad coronaria o aterosclerosis en otro
  # territorio» sin peso.
  # nota: asociación independiente; el resumen no da su OR
  # Lederle FA et al. Ann Intern Med 1997;126:441-9. PMID 9072929.
  # doi:10.7326/0003-4819-126-6-199703150-00004.
  # El índice declara «Hipercolesterolemia» sin peso.
  # nota: asociación independiente; el resumen no da su OR
  # Lederle FA et al. Ann Intern Med 1997;126:441-9. PMID 9072929.
  # doi:10.7326/0003-4819-126-6-199703150-00004.
  # El índice declara «Hipertensión arterial» sin peso.
  # nota: asociación independiente; el resumen no da su OR
  # Lederle FA et al. Ann Intern Med 1997;126:441-9. PMID 9072929.
  # doi:10.7326/0003-4819-126-6-199703150-00004.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Pulsación aórtica ensanchada a la palpación
    codigos: { holonmed: "HM:3012" }
    rol: prueba_especifica
    lr: 12.0
    lr_negativo: 0.72
    fuente: >-
      Lederle FA et al. JAMA 1999;281:77-82. PMID 9892455.
      doi:10.1001/jama.281.1.77. LR+ IC95% [7.4, 19.5]. LR− IC95% [0.65,
      0.81]. La palpación positiva desplaza con fuerza hacia el
      diagnóstico, pero la negativa apenas descarta: un LR− de 0.72 deja
      la probabilidad casi intacta.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6006
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ANEURISMA DE AORTA ABDOMINAL

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
