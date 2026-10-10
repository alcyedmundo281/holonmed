---
titulo: Protocolo de colecistitis aguda
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Colecistitis aguda (colecistitis litiásica aguda, colecistitis
  aguda alitiásica, inflamación aguda de la vesícula biliar).
version: 0.1.0-borrador

condicion:
  nombre: Colecistitis aguda
  codigos:
    snomed: 76581006
    cie10: K81.0
    holonmed: HM:6042

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0201   # Dolor abdominal
  - HM:0600   # Signo de exploración
  - HM:0710   # Alteración hematológica
  - HM:0760   # Alteración inflamatoria
  - HM:0900   # Hallazgo de imagen

modelo_bayesiano:
  # El índice no publica prevalencia para esta condición. Sin probabilidad
  # base el motor no arranca: pon la de tu población.
  probabilidad_base: 0.0

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  # El índice declara «Colelitiasis conocida» sin peso.
  # nota: en la litiasis asintomática aparecen síntomas graves o
  # complicaciones en el 1-2% de los pacientes al año, y en la levemente
  # sintomática en el 1-3%; la colecistitis aguda es la complicación grave
  # más frecuente. Revisión de series de seguimiento sin grupo sin litiasis,
  # así que es un riesgo absoluto
  # Friedman GD. Am J Surg 1993;165:399-404. PMID 8480871.
  # doi:10.1016/s0002-9610(05)80930-4.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Signo ecográfico de colecistitis aguda
    codigos: { holonmed: "HM:3175" }
    rol: imagen
    lr: 12.7
    lr_negativo: 0.31
    fuente: >-
      Wilson SJ et al. Ann Emerg Med 2024;83:235-246. PMID 37855790.
      doi:10.1016/j.annemergmed.2023.09.005. LR+ IC95% [5.8, 27.5]. LR−
      IC95% [0.23, 0.41]. Población: adultos en el servicio de urgencias
      con sospecha clínica de colecistitis aguda; metaanálisis de 7
      estudios con diagnóstico final como estándar de referencia (1 772
      pacientes). Patrón ecográfico positivo (cálculo + pared > 3 mm +
      líquido perivesicular + Murphy ecográfico): confirma colecistitis
      aguda e indica interconsulta quirúrgica temprana para
      colecistectomía laparoscópica precoz (dentro de las primeras 24-72
      h).

  - nombre: Litiasis biliar en imagen
    codigos: { holonmed: "HM:0903" }
    rol: manifestacion
    # no_medido: el índice no publica cociente
    # Yokoe M et al. J Hepatobiliary Pancreat Sci 2018;25:41-54. PMID
    # 29032636. doi:10.1002/jhbp.515.

  - nombre: Dolor en hipocondrio derecho
    codigos: { holonmed: "HM:0203" }
    rol: manifestacion
    # no_medido: el índice no publica cociente
    # Yokoe M et al. J Hepatobiliary Pancreat Sci 2018;25:41-54. PMID
    # 29032636. doi:10.1002/jhbp.515.

  - nombre: Fiebre
    codigos: { holonmed: "HM:0101" }
    rol: apoyo
    # no_medido: el índice no publica cociente
    # Yokoe M et al. J Hepatobiliary Pancreat Sci 2018;25:41-54. PMID
    # 29032636. doi:10.1002/jhbp.515.

  - nombre: Leucocitosis
    codigos: { holonmed: "HM:0712" }
    rol: apoyo
    # no_medido: el índice no publica cociente
    # Yokoe M et al. J Hepatobiliary Pancreat Sci 2018;25:41-54. PMID
    # 29032636. doi:10.1002/jhbp.515.

  - nombre: Elevación de proteína C reactiva
    codigos: { holonmed: "HM:0761" }
    rol: apoyo
    # no_medido: el índice no publica cociente
    # Yokoe M et al. J Hepatobiliary Pancreat Sci 2018;25:41-54. PMID
    # 29032636. doi:10.1002/jhbp.515.

  - nombre: Irritación peritoneal
    codigos: { holonmed: "HM:0601" }
    rol: apoyo
    # no_medido: el índice no publica cociente
    # Yokoe M et al. J Hepatobiliary Pancreat Sci 2018;25:41-54. PMID
    # 29032636. doi:10.1002/jhbp.515.

laboratorio:
  - parametro: Grosor de la pared anterior vesicular
    corte_superior: 3.0
    termino_si_alto: Signo ecográfico de colecistitis aguda
    codigos: { holonmed: "HM:3175" }

  - parametro: Temperatura
    corte_superior: 38.0
    termino_si_alto: Fiebre
    codigos: { holonmed: "HM:0101" }

  - parametro: Leucocitos
    corte_superior: 11000
    termino_si_alto: Leucocitosis
    codigos: { holonmed: "HM:0712" }

  - parametro: Proteína C reactiva
    corte_superior: 10
    termino_si_alto: Elevación de proteína C reactiva
    codigos: { holonmed: "HM:0761" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6042
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE COLECISTITIS AGUDA

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
   - «Grosor de la pared anterior vesicular 4» → *Signo ecográfico de colecistitis aguda*
   - «Temperatura 49» → *Fiebre*
   - «Leucocitos 14,300» → *Leucocitosis*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

El POCUS en urgencias tiene alta especificidad (94.4%) y sensibilidad
moderada (70.9%) para confirmar colecistitis aguda en pacientes con
sospecha clínica, permitiendo acelerar la resolución quirúrgica
definitiva.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
