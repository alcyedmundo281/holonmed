---
titulo: Protocolo de faringitis estreptocócica
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Faringitis estreptocócica (faringoamigdalitis estreptocócica,
  faringitis por estreptococo del grupo A).
version: 0.1.0-borrador

condicion:
  nombre: Faringitis estreptocócica
  codigos:
    snomed: 43878008
    cie10: J02.0
    holonmed: HM:6009

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0200   # Dolor
  - HM:0600   # Signo de exploración
  - HM:0607   # Adenopatías
  - HM:3028   # Exposición reciente a faringitis estreptocócica

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.37
  # medida en: niños menores de 18 años que consultan por odinofagia;
  # metaanálisis de 29 estudios
  # Shaikh N et al. Pediatrics 2010;126:e557-64. PMID 20696723.
  # doi:10.1542/peds.2009-2648.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Exudado amigdalino
    codigos: { holonmed: "HM:3026" }
    rol: prueba_especifica
    lr: 3.4
    fuente: >-
      Ebell MH et al. JAMA 2000;284:2912-8. PMID 11147989.
      doi:10.1001/jama.284.22.2912. La fuente no publica intervalo de
      confianza en el abstract. El hallazgo aislado más útil, y aun así
      insuficiente por sí solo.

  - nombre: Exudado faríngeo
    codigos: { holonmed: "HM:3027" }
    rol: prueba_especifica
    lr: 2.1
    fuente: >-
      Ebell MH et al. JAMA 2000;284:2912-8. PMID 11147989.
      doi:10.1001/jama.284.22.2912. La fuente no publica intervalo de
      confianza en el abstract. Apoya menos que el exudado amigdalino, del
      que se distingue.

  - nombre: Exposición reciente a faringitis estreptocócica
    codigos: { holonmed: "HM:3028" }
    rol: apoyo
    lr: 1.9
    fuente: >-
      Ebell MH et al. JAMA 2000;284:2912-8. PMID 11147989.
      doi:10.1001/jama.284.22.2912. Exposición en las dos semanas previas;
      sin intervalo en el abstract. Dato de anamnesis con peso escaso.

  - nombre: Adenopatía cervical anterior dolorosa
    codigos: { holonmed: "HM:3029" }
    rol: prueba_sensible
    lr_negativo: 0.6
    fuente: >-
      Ebell MH et al. JAMA 2000;284:2912-8. PMID 11147989.
      doi:10.1001/jama.284.22.2912. La fuente no publica intervalo de
      confianza en el abstract. Su ausencia es lo que más reduce la
      probabilidad, y aun así la deja en más de la mitad de la previa.

  - nombre: Hipertrofia amigdalina
    codigos: { holonmed: "HM:3030" }
    rol: prueba_sensible
    lr_negativo: 0.63
    fuente: >-
      Ebell MH et al. JAMA 2000;284:2912-8. PMID 11147989.
      doi:10.1001/jama.284.22.2912. La fuente no publica intervalo de
      confianza en el abstract. Su ausencia reduce poco la probabilidad.

  - nombre: Odinofagia
    codigos: { holonmed: "HM:0211" }
    rol: manifestacion
    # no_medible: es el motivo de consulta que define la población
    # estudiada, no una prueba dentro de ella

laboratorio:
  - parametro: Ventana de exposición
    corte_superior: 14
    termino_si_alto: Exposición reciente a faringitis estreptocócica
    codigos: { holonmed: "HM:3028" }

# ── Propuesta de clasificación, sin activar ──────────────────────────
# El índice declara estas reglas con sus componentes y su fuente. Para
# activarlas hay que decidir dos cosas que el origen no dice: cuántos
# criterios se exigen y qué término se acuña al cumplirse. Descoméntalo
# cuando lo hayas resuelto.
#
# clasificacion:
#   nombre: Ausencia de exudado
#   fuente: Ebell MH et al. JAMA 2000;284:2912-8. PMID 11147989. doi:10.1001/jama.284.22.2912.
#   requiere: <cuántos criterios hacen falta>
#   criterios:
#     - nombre: Ausencia de exudado
#       rol: <manifestacion | prueba_sensible | prueba_especifica>
#       satisface_si: ["HM:3026", "HM:3027"]
#         # HM:3026  Exudado amigdalino
#         # HM:3027  Exudado faríngeo
#   produce:
#     termino: Faringitis estreptocócica
#     codigos: { holonmed: "HM:6009" }
#     semantica: trastorno

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6009
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE FARINGITIS ESTREPTOCÓCICA

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
   - «Ventana de exposición 18» → *Exposición reciente a faringitis estreptocócica*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Escalas

No son signos: combinan varios elementos y se leen por tramos.
holonmed no las calcula — si el texto trae la puntuación, úsala tal
como viene y aplica el tramo que corresponda.

### Criterios de Centor

Componentes: cuatro variables clínicas (1 punto cada una): fiebre referida o medida > 38 °C, ausencia de tos, exudado amigdalino o faríngeo y adenopatía cervical anterior dolorosa.

- **4 puntos (probabilidad alta)**: 
- **3 puntos (probabilidad intermedia-alta)**: 
- **2 puntos (probabilidad intermedia)**: 
- **1 punto (probabilidad baja)**: 
- **0 puntos (probabilidad mínima)**: 

### Escala de McIsaac (Centor modificada)

Componentes: criterios de Centor con ajuste por edad: fiebre > 38 °C (+1), ausencia de tos (+1), exudado o hipertrofia amigdalina (+1), adenopatía cervical anterior dolorosa (+1); edad 3 a 14 años (+1), edad 15 a 44 años (0), edad ≥ 45 años (-1).

- **4 a 5 puntos (riesgo alto)**: 
- **3 puntos (riesgo intermedio-alto)**: 
- **2 puntos (riesgo intermedio)**: 
- **1 punto (riesgo bajo)**: 
- **0 o menor (riesgo mínimo)**: 

## Lo que la fuente concluye

Ningún elemento aislado de la anamnesis o de la exploración física es lo
bastante preciso para excluir ni para diagnosticar la faringitis
estreptocócica. Una regla de predicción clínica bien validada sí resulta
útil y ayuda al médico a usar de forma más informada las pruebas rápidas
de antígeno y el cultivo faríngeo.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
