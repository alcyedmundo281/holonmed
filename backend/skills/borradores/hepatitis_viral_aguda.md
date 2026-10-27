---
titulo: Protocolo de hepatitis viral aguda
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Hepatitis viral aguda (hepatitis aguda, hepatitis vírica aguda).
version: 0.1.0-borrador

condicion:
  nombre: Hepatitis viral aguda
  codigos:
    snomed: 57412004
    cie10: B17.9
    holonmed: HM:6001

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0201   # Dolor abdominal
  - HM:0300   # Síntoma digestivo
  - HM:0600   # Signo de exploración
  - HM:0730   # Alteración enzimática
  - HM:0740   # Alteración metabólica
  - HM:0800   # Síntoma general

modelo_bayesiano:
  # El índice publica prevalencia (0.09) pero ningún signo de este protocolo
  # trae un LR utilizable, así que el modelo bayesiano no se activa. Cuando
  # haya cocientes, pon aquí la de tu población.
  probabilidad_base: 0.0

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  # El índice declara «Consumo de almejas u ostras crudas en los tres meses
  # previos» sin peso.
  # nota: referido por 51 de 126 adultos con hepatitis A aguda (40.5%); la
  # fuente no tiene grupo control
  # Jeong CY et al. Sci Rep 2023;13:14271. PMID 37652984.
  # doi:10.1038/s41598-023-40775-5.
  # El índice declara «Conducta sexual de riesgo» sin peso.
  # nota: presente en el 79% de los casos de hepatitis A aguda de un
  # servicio de urgencias de Barcelona, 2014-2018; la fuente no tiene grupo
  # control
  # Llaneras J et al. Clin Gastroenterol Hepatol 2021;19:1030-1037. PMID
  # 32663522. doi:10.1016/j.cgh.2020.07.006.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Ictericia
    codigos: { holonmed: "HM:0305" }
    rol: manifestacion
    # no_medido: no se halló ningún estudio que la compare con hepatitis
    # agudas no víricas frente a un patrón serológico
    # población: adultos con hepatitis A aguda confirmada por serología en
    # 12 hospitales de Corea del Sur, 2020-2021; 84 de 126
    # sensibilidad publicada: 0.667
    # Roche SP et al. Am Fam Physician 2004;69:299-304. PMID 14765767.

  - nombre: Coluria
    codigos: { holonmed: "HM:0306" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Acolia
    codigos: { holonmed: "HM:0307" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Elevación de transaminasas
    codigos: { holonmed: "HM:0733" }
    rol: prueba_sensible
    # no_medible: forma parte de la definición de caso; sesgo de
    # incorporación

  - nombre: Hiperbilirrubinemia
    codigos: { holonmed: "HM:0745" }
    rol: apoyo
    # no_medible: forma parte de la definición de caso; sesgo de
    # incorporación

  - nombre: Dolor en hipocondrio derecho
    codigos: { holonmed: "HM:0203" }
    rol: apoyo
    # no_medido: el índice no publica cociente

  - nombre: Hepatomegalia
    codigos: { holonmed: "HM:0602" }
    rol: apoyo
    # no_medido: el índice no publica cociente

  - nombre: Fiebre
    codigos: { holonmed: "HM:0101" }
    rol: apoyo
    # no_medido: la fuente da la frecuencia en los casos pero no en las
    # hepatitis agudas no víricas, así que no hay especificidad ni cociente
    # población: adultos con hepatitis A aguda confirmada por serología en
    # 12 hospitales de Corea del Sur, 2020-2021; 77 de 126
    # sensibilidad publicada: 0.611
    # Jeong CY et al. Sci Rep 2023;13:14271. PMID 37652984.
    # doi:10.1038/s41598-023-40775-5.

  - nombre: Astenia
    codigos: { holonmed: "HM:0801" }
    rol: apoyo
    # no_medido: el índice no publica cociente

  - nombre: Anorexia
    codigos: { holonmed: "HM:0802" }
    rol: apoyo
    # no_medido: la fuente da la frecuencia en los casos pero no en las
    # hepatitis agudas no víricas, así que no hay especificidad ni cociente
    # población: adultos con hepatitis A aguda confirmada por serología en
    # 12 hospitales de Corea del Sur, 2020-2021; 87 de 126
    # sensibilidad publicada: 0.69
    # Jeong CY et al. Sci Rep 2023;13:14271. PMID 37652984.
    # doi:10.1038/s41598-023-40775-5.

laboratorio:
  - parametro: Temperatura
    corte_superior: 38.0
    termino_si_alto: Fiebre
    codigos: { holonmed: "HM:0101" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6001
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE HEPATITIS VIRAL AGUDA

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
   - «Temperatura 49» → *Fiebre*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
