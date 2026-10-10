---
titulo: Protocolo de mononucleosis infecciosa
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Mononucleosis infecciosa (mononucleosis, enfermedad del beso).
version: 0.1.0-borrador

condicion:
  nombre: Mononucleosis infecciosa
  codigos:
    snomed: 271558008
    cie10: B27
    holonmed: HM:6003

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0200   # Dolor
  - HM:0600   # Signo de exploración
  - HM:0607   # Adenopatías
  - HM:0710   # Alteración hematológica
  - HM:0800   # Síntoma general

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.077
  # medida en: pacientes de 16 a 20 años que consultan por odinofagia
  # Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266.
  # doi:10.1001/jama.2016.2111.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  # El índice declara «Edad entre 5 y 25 años» sin peso.
  # nota: máxima frecuencia entre los 16 y 20 años
  # Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266.
  # doi:10.1001/jama.2016.2111.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Adenopatía cervical posterior
    codigos: { holonmed: "HM:3001" }
    rol: prueba_especifica
    # varias aristas del índice publican cociente para este hallazgo
    # (poblaciones o estudios distintos). No se traslada ninguno: contarlos
    # todos duplicaría la evidencia y elegir uno es decidir qué población es
    # la tuya. Elige uno, escribe `lr`/`lr_negativo` y su `fuente`.
    # candidata 1: LR+ 3.1. Población: población no declarada. Ebell MH et
    # al. JAMA 2016;315:1502-9. PMID 27115266. doi:10.1001/jama.2016.2111.
    # candidata 2: LR+ 3.16. Población: metaanálisis bivariado de 17
    # estudios en pacientes con sospecha de mononucleosis, con prevalencias
    # de 2.1% a 80% en las cohortes prospectivas. Cai X et al. J Am Board
    # Fam Med 2021;34:1141-1156. PMID 34772769.
    # doi:10.3122/jabfm.2021.06.210217.

  - nombre: Adenopatía inguinal o axilar
    codigos: { holonmed: "HM:3002" }
    rol: prueba_especifica
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266.
    # doi:10.1001/jama.2016.2111. Rango entre estudios; la fuente no da
    # estimación resumida. Aumenta la probabilidad de forma similar a la
    # cervical posterior.

  - nombre: Adenopatía inguinal o axilar
    codigos: { holonmed: "HM:3002" }
    rol: prueba_especifica
    lr: 3.05
    fuente: >-
      Cai X et al. J Am Board Fam Med 2021;34:1141-1156. PMID 34772769.
      doi:10.3122/jabfm.2021.06.210217. IC95% [1.85, 4.7]. Población:
      metaanálisis bivariado de 17 estudios en pacientes con sospecha de
      mononucleosis, con prevalencias de 2.1% a 80% en las cohortes
      prospectivas. La fuente la denomina adenopatía axilar o inguinal.
      Moderadamente útil para confirmar; su ausencia apenas descarta.

  - nombre: Petequias en paladar
    codigos: { holonmed: "HM:3003" }
    rol: prueba_especifica
    lr: 5.3
    fuente: >-
      Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266.
      doi:10.1001/jama.2016.2111. IC95% [2.1, 13]. El hallazgo
      exploratorio que más aumenta la probabilidad.

  - nombre: Petequias en paladar
    codigos: { holonmed: "HM:3003" }
    rol: prueba_especifica
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Cai X et al. J Am Board Fam Med 2021;34:1141-1156. PMID 34772769.
    # doi:10.3122/jabfm.2021.06.210217. Población: metaanálisis bivariado de
    # 17 estudios en pacientes con sospecha de mononucleosis, con
    # prevalencias de 2.1% a 80% en las cohortes prospectivas. Rango entre
    # estudios en el abstract; no da estimación resumida. Moderadamente útil
    # para confirmar, con una incertidumbre mucho mayor que la medición
    # anterior.

  - nombre: Esplenomegalia
    codigos: { holonmed: "HM:0603" }
    rol: prueba_especifica
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266.
    # doi:10.1001/jama.2016.2111. Rango entre estudios, con especificidad de
    # 0.71 a 0.99. La amplitud refleja lo mucho que depende del explorador.
    # Apoya el diagnóstico y condiciona el consejo de evitar deporte de
    # contacto.

  - nombre: Esplenomegalia
    codigos: { holonmed: "HM:0603" }
    rol: prueba_especifica
    lr: 2.39
    fuente: >-
      Cai X et al. J Am Board Fam Med 2021;34:1141-1156. PMID 34772769.
      doi:10.3122/jabfm.2021.06.210217. IC95% [1.11, 5.51]. Población:
      metaanálisis bivariado de 17 estudios en pacientes con sospecha de
      mononucleosis, con prevalencias de 2.1% a 80% en las cohortes
      prospectivas. Moderadamente útil para confirmar; su ausencia apenas
      descarta.

  - nombre: Adenopatías
    codigos: { holonmed: "HM:0607" }
    rol: prueba_sensible
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266.
    # doi:10.1001/jama.2016.2111. La fuente lo expresa como el LR positivo
    # de la AUSENCIA de adenopatías, que es el cociente negativo del
    # hallazgo. Su ausencia reduce la probabilidad; es el hallazgo que más
    # descarta.

  - nombre: Odinofagia
    codigos: { holonmed: "HM:0211" }
    rol: manifestacion
    lr: 1.0
    # sin_efecto en el índice: se reconoce el término pero no desplaza la
    # probabilidad. «symptoms are of limited value»: sensible (0.81-0.83)
    # pero inespecífico. La fuente no publica cociente porque no discrimina.
    # sensibilidad publicada: 0.81

  - nombre: Astenia
    codigos: { holonmed: "HM:0801" }
    rol: manifestacion
    lr: 1.0
    # sin_efecto en el índice: se reconoce el término pero no desplaza la
    # probabilidad. Sensible (0.81-0.83) pero inespecífico; la fuente no
    # publica cociente

  - nombre: Linfocitosis atípica
    codigos: { holonmed: "HM:3004" }
    rol: prueba_especifica
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ 11.4 para linfocitos atípicos ≥ 10%
    # Ebell MH et al. JAMA 2016;315:1502-9. PMID 27115266.
    # doi:10.1001/jama.2016.2111. IC95% [2.7, 35]; umbral: linfocitos
    # atípicos ≥ 10%. A partir del 10% ya desplaza la probabilidad con
    # fuerza.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6003
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE MONONUCLEOSIS INFECCIOSA

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
