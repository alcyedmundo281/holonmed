---
titulo: Protocolo de meningitis aguda
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Meningitis aguda.
version: 0.1.0-borrador

condicion:
  nombre: Meningitis aguda
  codigos:
    snomed: 822031000000101
    cie10: G03.9
    holonmed: HM:6004

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0200   # Dolor
  - HM:0300   # Síntoma digestivo
  - HM:0500   # Síntoma neurológico

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
  - nombre: Acentuación de la cefalea con la sacudida cefálica
    codigos: { holonmed: "HM:3006" }
    rol: apoyo
    # no_medido: la revisión publica sensibilidad y especificidad agrupadas,
    # con certeza muy baja, pero no el cociente. No se calcula aquí
    # población: pacientes con sospecha de meningitis en urgencias, 9
    # estudios y 1161 participantes; patrón de referencia, la pleocitosis en
    # el LCR
    # sensibilidad publicada: 0.653
    # especificidad publicada: 0.704
    # sin alteración de la conciencia (8 estudios, 921 participantes), Se
    # 0.752 (IC95% 0.543-0.886) y Sp 0.608 (IC95% 0.434-0.759). Sustituye al
    # LR+ 2.2 y LR− 0 de Attia 1999 (pmid:10411200), que venían de un único
    # estudio de 1991
    # Iguchi M et al. Cochrane Database Syst Rev 2020;6:CD012824. PMID
    # 32524581. doi:10.1002/14651858.CD012824.pub2.

  - nombre: Cefalea
    codigos: { holonmed: "HM:0207" }
    rol: manifestacion
    # no_medido: la fuente publica sensibilidad agrupada pero no
    # especificidad, así que el cociente no es calculable desde el abstract
    # sensibilidad publicada: 0.5

  - nombre: Náuseas
    codigos: { holonmed: "HM:0301" }
    rol: manifestacion
    # no_medido: sensibilidad agrupada sin especificidad; LR no calculable
    # sensibilidad publicada: 0.3

  - nombre: Vómitos
    codigos: { holonmed: "HM:0302" }
    rol: manifestacion
    # no_medido: la fuente agrupa náuseas y vómitos en una sola estimación
    # sensibilidad publicada: 0.3

  - nombre: Fiebre
    codigos: { holonmed: "HM:0101" }
    rol: prueba_sensible
    # no_medido: forma parte de la tríada fiebre + rigidez de nuca +
    # alteración del estado mental, cuya presencia de al menos uno tiene
    # sensibilidad del 99-100%. La fuente no desglosa el cociente de cada
    # componente por separado.

  - nombre: Rigidez de nuca
    codigos: { holonmed: "HM:3005" }
    rol: apoyo
    lr: 0.94
    fuente: >-
      Thomas KE et al. Clin Infect Dis 2002;35:46-52. PMID 12060874.
      doi:10.1086/340979. Población: 297 adultos con sospecha de
      meningitis explorados antes de la punción lumbar; meningitis
      definida como ≥ 6 leucocitos en el LCR.

  - nombre: Signo de Kernig
    codigos: { holonmed: "HM:3238", snomed: "39051003" }
    rol: apoyo
    lr: 0.97
    fuente: >-
      Thomas KE et al. Clin Infect Dis 2002;35:46-52. PMID 12060874.
      doi:10.1086/340979. Población: 297 adultos con sospecha de
      meningitis explorados antes de la punción lumbar; meningitis
      definida como ≥ 6 leucocitos en el LCR.

  - nombre: Signo de Brudzinski
    codigos: { holonmed: "HM:3239", snomed: "82345001" }
    rol: apoyo
    lr: 0.97
    fuente: >-
      Thomas KE et al. Clin Infect Dis 2002;35:46-52. PMID 12060874.
      doi:10.1086/340979. Población: 297 adultos con sospecha de
      meningitis explorados antes de la punción lumbar; meningitis
      definida como ≥ 6 leucocitos en el LCR.

  - nombre: Alteración del nivel de conciencia
    codigos: { holonmed: "HM:0501" }
    rol: prueba_sensible
    # no_medido: componente de la tríada; la fuente no publica su cociente
    # aislado

laboratorio:
  - parametro: Temperatura
    corte_superior: 38.0
    termino_si_alto: Fiebre
    codigos: { holonmed: "HM:0101" }

# ── Propuesta de clasificación, sin activar ──────────────────────────
# El índice declara estas reglas con sus componentes y su fuente. Para
# activarlas hay que decidir dos cosas que el origen no dice: cuántos
# criterios se exigen y qué término se acuña al cumplirse. Descoméntalo
# cuando lo hayas resuelto.
#
# clasificacion:
#   nombre: Ausencia de la tríada clásica
#   fuente: Attia J et al. JAMA 1999;282:175-81. PMID 10411200. doi:10.1001/jama.282.2.175.
#   requiere: <cuántos criterios hacen falta>
#   criterios:
#     - nombre: Ausencia de la tríada clásica
#       rol: <manifestacion | prueba_sensible | prueba_especifica>
#       satisface_si: ["HM:0101", "HM:3005", "HM:0501"]
#         # HM:0101  Fiebre
#         # HM:3005  Rigidez de nuca
#         # HM:0501  Alteración del nivel de conciencia
#   produce:
#     termino: Meningitis aguda
#     codigos: { holonmed: "HM:6004" }
#     semantica: trastorno

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6004
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE MENINGITIS AGUDA

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
