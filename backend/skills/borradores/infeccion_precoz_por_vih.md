---
titulo: Protocolo de infección precoz por VIH
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Infección precoz por VIH (primoinfección por VIH).
version: 0.1.0-borrador

condicion:
  nombre: Infección precoz por VIH
  codigos:
    snomed: 1142045004
    holonmed: HM:6011

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0300   # Síntoma digestivo
  - HM:0600   # Signo de exploración
  - HM:0607   # Adenopatías
  - HM:0800   # Síntoma general

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.063
  # medida en: hombres que tienen sexo con hombres movilizados para cribado
  # de infección aguda y precoz por VIH; metaanálisis de 5 estudios
  # Palmer S et al. J Int AIDS Soc 2020;23 Suppl 6:e25590. PMID 33000916.
  # doi:10.1002/jia2.25590.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Úlceras genitales
    codigos: { holonmed: "HM:3039" }
    rol: prueba_especifica
    lr: 5.4
    fuente: >-
      Wood E et al. JAMA 2014;312:278-85. PMID 25027143.
      doi:10.1001/jama.2014.5954. IC95% [2.5, 12]. El síntoma que más
      aumenta la probabilidad.

  - nombre: Pérdida de peso
    codigos: { holonmed: "HM:0803" }
    rol: prueba_especifica
    lr: 4.7
    fuente: >-
      Wood E et al. JAMA 2014;312:278-85. PMID 25027143.
      doi:10.1001/jama.2014.5954. IC95% [2.1, 7.2].

  - nombre: Vómitos
    codigos: { holonmed: "HM:0302" }
    rol: prueba_especifica
    lr: 4.6
    fuente: >-
      Wood E et al. JAMA 2014;312:278-85. PMID 25027143.
      doi:10.1001/jama.2014.5954. IC95% [2.5, 8.0].

  - nombre: Adenopatías referidas por el paciente
    codigos: { holonmed: "HM:3040" }
    rol: prueba_especifica
    lr: 4.6
    fuente: >-
      Wood E et al. JAMA 2014;312:278-85. PMID 25027143.
      doi:10.1001/jama.2014.5954. IC95% [1.3, 8.0]. Nótese que el síntoma
      referido pesa MÁS que el signo hallado en la exploración, que tiene
      LR 3.1.

  - nombre: Fiebre
    codigos: { holonmed: "HM:0101" }
    rol: prueba_sensible
    lr_negativo: 0.74
    fuente: >-
      Wood E et al. JAMA 2014;312:278-85. PMID 25027143.
      doi:10.1001/jama.2014.5954. IC95% [0.64, 0.84]. Su ausencia reduce
      la probabilidad muy poco; no sirve para descartar.

  - nombre: Adenopatías
    codigos: { holonmed: "HM:0607" }
    rol: prueba_especifica
    lr: 3.1
    lr_negativo: 0.7
    fuente: >-
      Wood E et al. JAMA 2014;312:278-85. PMID 25027143.
      doi:10.1001/jama.2014.5954. LR+ IC95% [1.0, 5.2]. LR− IC95% [0.49,
      0.92]. El signo exploratorio más útil, y aun así modesto. El extremo
      inferior de su intervalo toca 1.0, es decir, es compatible con no
      aportar nada.

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
#   nombre: Ausencia de todo hallazgo
#   fuente: Wood E et al. JAMA 2014;312:278-85. PMID 25027143. doi:10.1001/jama.2014.5954.
#   requiere: <cuántos criterios hacen falta>
#   criterios:
#     - nombre: Ausencia de todo hallazgo
#       rol: <manifestacion | prueba_sensible | prueba_especifica>
#       satisface_si: ["HM:3039", "HM:0803", "HM:0302", "HM:3040", "HM:0101", "HM:0607"]
#         # HM:3039  Úlceras genitales
#         # HM:0803  Pérdida de peso
#         # HM:0302  Vómitos
#         # HM:3040  Adenopatías referidas por el paciente
#         # HM:0101  Fiebre
#         # HM:0607  Adenopatías
#   produce:
#     termino: Infección precoz por VIH
#     codigos: { holonmed: "HM:6011" }
#     semantica: trastorno

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6011
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE INFECCIÓN PRECOZ POR VIH

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

## Lo que la fuente concluye

La utilidad limitada de la exploración clínica para detectar o descartar
la infección precoz por VIH subraya la importancia del cribado sistemático
en adultos.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
