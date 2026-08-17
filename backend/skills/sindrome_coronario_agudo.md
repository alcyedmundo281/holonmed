---
titulo: Protocolo de síndrome coronario agudo
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  Dolor torácico agudo, con o sin cambios isquémicos en el
  electrocardiograma, irradiación a ambos brazos o antecedentes
  cardiovasculares. También el dolor atípico en quien ya tiene enfermedad
  coronaria conocida.
version: 1.0.0

condicion:
  nombre: Síndrome coronario agudo
  codigos:
    holonmed: HM:6007

# Ramas del grafo sobre las que actúa este protocolo.
#
# Podados HM:3017 (prueba de esfuerzo previa anormal) y HM:3018
# (enfermedad arterial periférica): el conversor los propuso porque su
# padre en el índice es una raíz, pero son antecedentes. Como ámbito
# ofrecerían este protocolo a cualquier paciente que los tenga
# registrados, sin dolor torácico ni nada agudo hoy.
ambito_grafo:
  - HM:0200   # Dolor
  - HM:0206   # Dolor torácico
  - HM:0500   # Síntoma neurológico

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.1
  # medida en: pacientes que acuden a urgencias con dolor torácico agudo
  # Fanaroff AC et al. JAMA 2015;314:1955-65. PMID 26547467.
  # doi:10.1001/jama.2015.12735.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Descenso del segmento ST
    codigos: { holonmed: "HM:3015" }
    rol: prueba_especifica
    lr: 5.3
    fuente: >-
      Fanaroff AC et al. JAMA 2015;314:1955-65. PMID 26547467.
      doi:10.1001/jama.2015.12735. IC95% [2.1, 8.6]. El hallazgo aislado
      más útil, pero insuficiente para confirmar.

  - nombre: Signos de isquemia en el electrocardiograma
    codigos: { holonmed: "HM:3016" }
    rol: prueba_especifica
    lr: 3.6
    fuente: >-
      Fanaroff AC et al. JAMA 2015;314:1955-65. PMID 26547467.
      doi:10.1001/jama.2015.12735. IC95% [1.6, 5.7]. Categoría más amplia
      que el descenso del ST y con menos peso.

  - nombre: Prueba de esfuerzo previa anormal
    codigos: { holonmed: "HM:3017" }
    rol: apoyo
    lr: 3.1
    fuente: >-
      Fanaroff AC et al. JAMA 2015;314:1955-65. PMID 26547467.
      doi:10.1001/jama.2015.12735. IC95% [2.0, 4.7]. Antecedente, no
      hallazgo actual; desplaza poco.

  - nombre: Enfermedad arterial periférica
    codigos: { holonmed: "HM:3018" }
    rol: apoyo
    lr: 2.7
    fuente: >-
      Fanaroff AC et al. JAMA 2015;314:1955-65. PMID 26547467.
      doi:10.1001/jama.2015.12735. IC95% [1.5, 4.8]. Factor de riesgo con
      cociente propio, modesto.

  - nombre: Dolor torácico irradiado a ambos brazos
    codigos: { holonmed: "HM:3014" }
    rol: apoyo
    lr: 2.6
    fuente: >-
      Fanaroff AC et al. JAMA 2015;314:1955-65. PMID 26547467.
      doi:10.1001/jama.2015.12735. IC95% [1.8, 3.7]. Alta especificidad
      pero cociente bajo: cuando aparece apoya, y su ausencia no dice
      nada.

  - nombre: Dolor torácico
    codigos: { holonmed: "HM:0206" }
    rol: manifestacion
    # no_medible: es el motivo de consulta que define la población
    # estudiada, no una prueba dentro de ella

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6007
  commit: d9464c6
  generado: 2026-08-17
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE SÍNDROME CORONARIO AGUDO

ROL: cardiólogo experto, basado en evidencia.

## Contexto fisiopatológico

- **Dónde**: arterias coronarias, miocardio, tórax anterior.
- **Cómo**: rotura o erosión de una placa aterosclerótica, trombosis
  sobre ella y desequilibrio entre el aporte y la demanda de oxígeno,
  que lleva a isquemia y, si se mantiene, a necrosis.
- **Por qué**: aterosclerosis coronaria, y con menor frecuencia espasmo,
  disección coronaria o anemia grave que descompensa una estenosis
  estable.

## Instrucciones de extracción

1. Analiza los signos vitales, la exploración, el electrocardiograma y el
   texto libre.
2. Extrae el hallazgo clínico, nunca la cifra suelta.
3. **No cuentes dos veces el mismo electrocardiograma.** *Descenso del
   segmento ST* es un hallazgo concreto dentro de *Signos de isquemia en
   el electrocardiograma*, que es la categoría amplia. Cada uno tiene su
   propio cociente: extraer los dos para un solo trazado multiplica una
   evidencia que sólo se observó una vez. Si el ST está descendido, ése
   es el término.
4. **La irradiación cuenta cuando es a los dos brazos.** El cociente
   declarado es el del dolor irradiado a ambos, no a uno. «Dolor que baja
   por el brazo izquierdo» no sustenta *Dolor torácico irradiado a ambos
   brazos*.
5. **Distingue el antecedente del hallazgo de hoy.** *Prueba de esfuerzo
   previa anormal* y *Enfermedad arterial periférica* son historia del
   paciente y desplazan poco; no los conviertas en hallazgos actuales ni
   los omitas cuando consten.
6. **No saltes del síntoma al diagnóstico.** «Dolor torácico» es un
   hallazgo; «infarto» o «síndrome coronario agudo» es la hipótesis que
   este protocolo evalúa, no algo que se extraiga del texto.
7. **La troponina no está en este modelo.** Si el texto la trae, regístrala
   como dato, pero la probabilidad que calcula este protocolo no la
   incorpora: no la leas como si la incluyera.
8. Ignora los hallazgos negados: «sin dolor irradiado» no genera ningún
   infón.

## Escalas

No son signos: combinan varios elementos y se leen por tramos.
holonmed no las calcula — si el texto trae la puntuación, úsala tal
como viene y aplica el tramo que corresponda.

### HEART

Componentes: anamnesis, electrocardiograma, edad, factores de riesgo y primera troponina.

- **7 a 10 (riesgo alto)**: LR+ 13, IC95% [7.0, 24]
- **0 a 3 (riesgo bajo)**: LR− 0.2, IC95% [0.13, 0.3]

El instrumento más potente en ambos sentidos: confirma en el tramo alto y descarta en el bajo.

### TIMI

- **5 a 7 (riesgo alto)**: LR+ 6.8, IC95% [5.2, 8.9]
- **0 a 1 (riesgo bajo)**: LR− 0.31, IC95% [0.23, 0.43]

### Algoritmo de la Heart Foundation of Australia y la Cardiac Society of Australia and New Zealand

- **riesgo bajo a intermedio**: LR− 0.24, IC95% [0.19, 0.31]

## Lo que la fuente concluye

Entre los pacientes con sospecha de SCA en urgencias, la anamnesis, la
exploración física y el electrocardiograma por sí solos no confirmaron ni
excluyeron el diagnóstico. Las escalas HEART o TIMI, que incorporan la
primera troponina, aportaron más información diagnóstica.

Eso gobierna cómo se lee todo lo anterior: los cocientes de este protocolo
son reales pero modestos, y ninguno decide. **Una probabilidad baja aquí no
descarta nada.**

## Banderas rojas

No son un diagnóstico: son motivos para que un humano mire ahora.

- Elevación del segmento ST o bloqueo de rama nuevo
- Hipotensión, mala perfusión o signos de shock
- Dolor torácico con síncope
- Disnea aguda o signos de insuficiencia cardíaca
- Arritmia sostenida
- Dolor persistente que no cede pese al tratamiento inicial
