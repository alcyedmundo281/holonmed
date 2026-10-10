---
titulo: Protocolo de hipovolemia
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Hipovolemia (depleción de volumen, hipovolemia aguda).
version: 0.1.0-borrador

condicion:
  nombre: Hipovolemia
  codigos:
    snomed: 816082000
    cie10: E86
    holonmed: HM:6008

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0104   # Taquicardia
  - HM:0500   # Síntoma neurológico
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
  - nombre: Mareo postural intenso
    codigos: { holonmed: "HM:3019" }
    rol: prueba_especifica
    # no_medido: la fuente publica sensibilidad y especificidad pero no el
    # cociente. Es derivable por aritmética, pero no se anota como medido
    # porque el autor no lo calculó: la forma de agrupar entre estudios
    # cambia el resultado.
    # población: adultos con sospecha de pérdida sanguínea
    # especificidad publicada: 0.98
    # la fuente lo evalúa junto con el incremento postural del pulso como un
    # solo hallazgo compuesto: basta con que esté presente uno de los dos.

  - nombre: Incremento postural del pulso
    codigos: { holonmed: "HM:3020" }
    rol: prueba_especifica
    # no_medido: componente del hallazgo compuesto con el mareo postural
    # intenso; la fuente no publica cociente aislado
    # población: adultos con sospecha de pérdida sanguínea
    # especificidad publicada: 0.98
    # McGee S et al. JAMA 1999;281:1022-9. PMID 10086438.
    # doi:10.1001/jama.281.11.1022.

  - nombre: Hipotensión arterial
    codigos: { holonmed: "HM:0109" }
    rol: apoyo
    # no_medido: la fuente publica sensibilidad sin especificidad
    # población: adultos con sospecha de pérdida sanguínea
    # sensibilidad publicada: 0.33
    # ADVERTENCIA: la hipotensión en decúbito y la taquicardia FALTAN con
    # frecuencia incluso tras perder 1150 mL. Su ausencia no tranquiliza.
    # McGee S et al. JAMA 1999;281:1022-9. PMID 10086438.
    # doi:10.1001/jama.281.11.1022.

  - nombre: Axila seca
    codigos: { holonmed: "HM:3021" }
    rol: prueba_especifica
    lr: 2.8
    fuente: >-
      McGee S et al. JAMA 1999;281:1022-9. PMID 10086438.
      doi:10.1001/jama.281.11.1022. IC95% [1.4, 5.4]. Población: pacientes
      con vómitos, diarrea o descenso de la ingesta. Apoya el diagnóstico,
      con fuerza modesta.

  - nombre: Mucosas húmedas
    codigos: { holonmed: "HM:3022" }
    rol: prueba_sensible
    lr_negativo: 0.3
    fuente: >-
      McGee S et al. JAMA 1999;281:1022-9. PMID 10086438.
      doi:10.1001/jama.281.11.1022. IC95% [0.1, 0.6]. Población: pacientes
      con vómitos, diarrea o descenso de la ingesta. Su PRESENCIA
      argumenta en contra de la hipovolemia. Es el hallazgo invertido: lo
      que ayuda es encontrarlo, no echarlo en falta.

  - nombre: Lengua sin surcos longitudinales
    codigos: { holonmed: "HM:3023" }
    rol: prueba_sensible
    lr_negativo: 0.3
    fuente: >-
      McGee S et al. JAMA 1999;281:1022-9. PMID 10086438.
      doi:10.1001/jama.281.11.1022. IC95% [0.1, 0.6]. Población: pacientes
      con vómitos, diarrea o descenso de la ingesta. Igual que las mucosas
      húmedas, su presencia argumenta en contra.

  - nombre: Relleno capilar prolongado
    codigos: { holonmed: "HM:3024" }
    rol: apoyo
    lr: 1.0
    # sin_efecto en el índice: se reconoce el término pero no desplaza la
    # probabilidad. La fuente concluye que no tiene valor diagnóstico
    # demostrado en adultos
    # población: adultos
    # McGee S et al. JAMA 1999;281:1022-9. PMID 10086438.
    # doi:10.1001/jama.281.11.1022.

  - nombre: Turgencia cutánea disminuida
    codigos: { holonmed: "HM:3025" }
    rol: apoyo
    lr: 1.0
    # sin_efecto en el índice: se reconoce el término pero no desplaza la
    # probabilidad. La fuente concluye que no tiene valor diagnóstico
    # demostrado en adultos
    # población: adultos
    # McGee S et al. JAMA 1999;281:1022-9. PMID 10086438.
    # doi:10.1001/jama.281.11.1022.

laboratorio:
  - parametro: Incremento de la frecuencia cardíaca al incorporarse
    corte_superior: 30
    termino_si_alto: Incremento postural del pulso
    codigos: { holonmed: "HM:3020" }

  - parametro: Presión arterial sistólica
    corte_inferior: 90
    termino_si_bajo: Hipotensión arterial
    codigos: { holonmed: "HM:0109" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6008
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE HIPOVOLEMIA

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
   - «Incremento de la frecuencia cardíaca al incorporarse 39» → *Incremento postural del pulso*
   - «Presión arterial sistólica 76.5» → *Hipotensión arterial*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

Para diagnosticar hipovolemia por pérdida sanguínea hace falta un
incremento postural del pulso de 30 latidos por minuto o más, o un mareo
postural intenso, aunque ambos faltan a menudo tras pérdidas moderadas. En
pacientes con vómitos, diarrea o descenso de la ingesta pocos hallazgos
han demostrado utilidad, y conviene medir electrolitos, urea y creatinina
cuando se necesita certeza diagnóstica.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
