---
titulo: Protocolo de taponamiento cardíaco
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Taponamiento cardíaco (taponamiento pericárdico, compromiso
  hemodinámico por derrame pericárdico).
version: 0.1.0-borrador

condicion:
  nombre: Taponamiento cardíaco
  codigos:
    snomed: 35304003
    cie10: I31.8
    holonmed: HM:6045

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0600   # Signo de exploración
  - HM:0900   # Hallazgo de imagen

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
  - nombre: Taponamiento cardíaco en ecografía
    codigos: { holonmed: "HM:3163" }
    rol: imagen
    # no_medido: el índice no publica cociente
    # población: pacientes con derrame pericárdico evaluados en urgencias o
    # cuidados críticos mediante ecocardiografía a pie de cama; revisión de
    # Alerhand 2022
    # ADVERTENCIA: la ausencia de colapso de cavidades derechas puede
    # ocurrir en hipertensión pulmonar grave o hipertrofia ventricular
    # derecha previa debido a presiones diastólicas basales elevadas (falso
    # negativo); no descarta taponamiento ante shock clínico evidente
    # Alerhand S et al. Am J Emerg Med 2022;58:159--174. PMID 35696801.
    # doi:10.1016/j.ajem.2022.05.001.

  - nombre: Derrame pericárdico en ecografía
    codigos: { holonmed: "HM:3155" }
    rol: prueba_sensible
    # no_medido: precondición fisiopatológica sine qua non: no puede existir
    # taponamiento cardíaco en ausencia de líquido o coágulo en el espacio
    # pericárdico que eleve la presión intrapericárdica

  - nombre: Hipotensión arterial
    codigos: { holonmed: "HM:0109" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Ingurgitación yugular
    codigos: { holonmed: "HM:3146" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Taquicardia
    codigos: { holonmed: "HM:0104" }
    rol: apoyo
    # no_medido: el índice no publica cociente

laboratorio:
  - parametro: Presión arterial sistólica
    corte_inferior: 90
    termino_si_bajo: Hipotensión arterial
    codigos: { holonmed: "HM:0109" }

  - parametro: Altura del punto máximo de pulsación sobre el ángulo esternal
    corte_superior: 3
    termino_si_alto: Ingurgitación yugular
    codigos: { holonmed: "HM:3146" }

  - parametro: Frecuencia cardíaca
    corte_superior: 100
    termino_si_alto: Taquicardia
    codigos: { holonmed: "HM:0104" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6045
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE TAPONAMIENTO CARDÍACO

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
   - «Presión arterial sistólica 76.5» → *Hipotensión arterial*
   - «Altura del punto máximo de pulsación sobre el ángulo esternal 4» → *Ingurgitación yugular*
   - «Frecuencia cardíaca 130» → *Taquicardia*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

El colapso de cavidades derechas y la pletora de la vena cava inferior en
presencia de derrame pericárdico son los pilares ecocardiográficos que
definen la fisiología de taponamiento; integrados con la inestabilidad
hemodinámica, guían la indicación de descompresión pericárdica urgente.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
