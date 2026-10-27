---
titulo: Protocolo de lesión intracraneal en el traumatismo craneal leve del adulto
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Lesión intracraneal en el traumatismo craneal leve del adulto
  (lesión intracraneal grave tras traumatismo craneal leve, hemorragia
  intracraneal postraumática del adulto, indicación de neuroimagen en el
  traumatismo craneal leve).
version: 0.1.0-borrador

condicion:
  nombre: Lesión intracraneal en el traumatismo craneal leve del adulto
  codigos:
    holonmed: HM:6038

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0302   # Vómitos
  - HM:0501   # Alteración del nivel de conciencia
  - HM:0600   # Signo de exploración
  - HM:3053   # Peatón atropellado por vehículo

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.071
  # medida en: adultos atendidos por traumatismo craneal leve, 23 079
  # pacientes
  # Easter JS et al. JAMA 2015;314:2672-81. PMID 26717031.
  # doi:10.1001/jama.2015.16316.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Signos de fractura de cráneo
    codigos: { holonmed: "HM:3049" }
    rol: prueba_especifica
    lr: 16.0
    fuente: >-
      Easter JS et al. JAMA 2015;314:2672-81. PMID 26717031.
      doi:10.1001/jama.2015.16316. IC95% [3.1, 59]. Con diferencia el
      cociente más alto de la serie: encontrarlos cambia la decisión por
      sí solo.

  - nombre: Puntuación de Glasgow de 13
    codigos: { holonmed: "HM:3050" }
    rol: prueba_especifica
    lr: 4.9
    fuente: >-
      Easter JS et al. JAMA 2015;314:2672-81. PMID 26717031.
      doi:10.1001/jama.2015.16316. IC95% [2.8, 8.5].

  - nombre: Vómitos en dos o más episodios
    codigos: { holonmed: "HM:3052" }
    rol: apoyo
    lr: 3.6
    fuente: >-
      Easter JS et al. JAMA 2015;314:2672-81. PMID 26717031.
      doi:10.1001/jama.2015.16316. IC95% [3.1, 4.1]. El cociente más
      preciso de la serie —intervalo de 3.1 a 4.1— y el más fácil de
      recoger en la anamnesis.

  - nombre: Puntuación de Glasgow menor de 14 a las dos horas del traumatismo
    codigos: { holonmed: "HM:3152" }
    rol: apoyo
    lr: 3.4
    fuente: >-
      Easter JS et al. JAMA 2015;314:2672-81. PMID 26717031.
      doi:10.1001/jama.2015.16316. IC95% [1.4, 8.4]. Un Glasgow que sigue
      por debajo de 14 dos horas después pesa por sí mismo, con
      independencia de la puntuación de llegada.

  - nombre: Descenso de la puntuación de Glasgow
    codigos: { holonmed: "HM:3051" }
    rol: apoyo
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Easter JS et al. JAMA 2015;314:2672-81. PMID 26717031.
    # doi:10.1001/jama.2015.16316. Población: entre los estudios que lo
    # midieron.

  - nombre: Peatón atropellado por vehículo
    codigos: { holonmed: "HM:3053" }
    rol: apoyo
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Easter JS et al. JAMA 2015;314:2672-81. PMID 26717031.
    # doi:10.1001/jama.2015.16316. Población: entre los estudios que lo
    # midieron. 3.0 a 4.3 es la dispersión entre estudios, no un intervalo
    # de confianza.

laboratorio:
  - parametro: Puntuación de Glasgow a las dos horas del traumatismo
    corte_inferior: 14
    termino_si_bajo: Puntuación de Glasgow menor de 14 a las dos horas del traumatismo
    codigos: { holonmed: "HM:3152" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6038
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE LESIÓN INTRACRANEAL EN EL TRAUMATISMO CRANEAL LEVE DEL ADULTO

ROL: <!-- especialidad y postura: «cardiólogo experto, basado en evidencia» -->

## Contexto fisiopatológico

<!-- El índice no guarda prosa. Estas tres líneas son las que hacen que
     el modelo reconozca el cuadro y no sólo sus términos. -->

- **Dónde**: <!-- órgano, territorio, compartimento -->
- **Cómo**: <!-- mecanismo -->
- **Por qué**: <!-- causas frecuentes -->

## Instrucciones de extracción

1. Analiza los signos vitales, la exploración y el texto libre.
2. **Interpreta los valores numéricos** con los cortes declarados
   arriba. Extrae el hallazgo clínico, nunca la cifra suelta:
   - «Puntuación de Glasgow a las dos horas del traumatismo 11.9» → *Puntuación de Glasgow menor de 14 a las dos horas del traumatismo*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Escalas

No son signos: combinan varios elementos y se leen por tramos.
holonmed no las calcula — si el texto trae la puntuación, úsala tal
como viene y aplica el tramo que corresponda.

### Canadian CT Head Rule

Componentes: el abstract no los enumera; el Glasgow menor de 14 a las dos horas es uno de ellos, y la corrección de este artículo cambió justo ese corte.

- **regla negativa (ningún criterio presente)**: LR− 0.04

Es el cociente negativo más fuerte de la condición: una regla canadiense negativa hace la lesión intracraneal muy improbable.

### New Orleans Criteria

Componentes: el abstract no los enumera; la amnesia de más de 30 minutos es uno de ellos.

- **criterios ausentes**: LR− 0.08

Descarta con fuerza, aunque algo menos que la regla canadiense y con un intervalo que llega hasta 0.84.

## Lo que la fuente concluye

En el adulto con traumatismo craneal leve, la probabilidad de lesión
intracraneal grave es del 7.1%. Los signos de fractura de cráneo, una
puntuación de Glasgow de 13, el descenso del Glasgow y dos o más episodios
de vómito aumentan esa probabilidad. Una Canadian CT Head Rule negativa o
unos New Orleans Criteria ausentes la hacen muy improbable.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
