---
titulo: Protocolo de infarto agudo de miocardio
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Infarto agudo de miocardio (IAM, ataque cardíaco, infarto de
  miocardio).
version: 0.1.0-borrador

condicion:
  nombre: Infarto agudo de miocardio
  codigos:
    holonmed: HM:6030

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0206   # Dolor torácico
  - HM:0600   # Signo de exploración
  - HM:0608   # Soplo cardíaco

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
  - nombre: Elevación nueva del segmento ST en el ECG
    codigos: { holonmed: "HM:3130" }
    rol: prueba_especifica
    lr: 22.0
    fuente: >-
      Panju AA et al. JAMA 1998;280:1256-63. PMID 9786377.
      doi:10.1001/jama.280.14.1256. IC95% [5.7, 53.9]. El hallazgo
      electrocardiográfico individual más potente para confirmar IAM con
      indicación de reperfusión.

  - nombre: Nueva onda Q patológica en el ECG
    codigos: { holonmed: "HM:3131" }
    rol: prueba_especifica
    lr: 11.0
    fuente: >-
      Panju AA et al. JAMA 1998;280:1256-63. PMID 9786377.
      doi:10.1001/jama.280.14.1256. IC95% [5.3, 24.8]. Signo
      electrocardiográfico de necrosis miocárdica transmisible.

  - nombre: Dolor torácico irradiado a ambos brazos
    codigos: { holonmed: "HM:3014" }
    rol: prueba_especifica
    lr: 7.1
    fuente: >-
      Panju AA et al. JAMA 1998;280:1256-63. PMID 9786377.
      doi:10.1001/jama.280.14.1256. IC95% [3.5, 14.2]. El síntoma de
      irradiación dolorosa con mayor rendimiento discriminativo positivo.

  - nombre: Tercer tono cardíaco (R3)
    codigos: { holonmed: "HM:3132" }
    rol: apoyo
    lr: 3.2
    fuente: >-
      Panju AA et al. JAMA 1998;280:1256-63. PMID 9786377.
      doi:10.1001/jama.280.14.1256. IC95% [1.6, 6.5]. Signo auscultatorio
      de disfunción ventricular izquierda aguda.

  - nombre: Hipotensión arterial
    codigos: { holonmed: "HM:0109" }
    rol: apoyo
    lr: 3.1
    fuente: >-
      Panju AA et al. JAMA 1998;280:1256-63. PMID 9786377.
      doi:10.1001/jama.280.14.1256. IC95% [1.6, 6.2]. Marcador
      hemodinámico de compromiso miocárdico o shock cardiogénico.

laboratorio:
  - parametro: Presión arterial sistólica
    corte_inferior: 90
    termino_si_bajo: Hipotensión arterial
    codigos: { holonmed: "HM:0109" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6030
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE INFARTO AGUDO DE MIOCARDIO

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
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

La anamnesis dirigida, la exploración física y el ECG son fundamentales
para evaluar a pacientes con dolor torácico agudo. La nueva elevación del
ST (LR+ 22.0) y la irradiación a ambos brazos (LR+ 7.1) confirman
fuertemente el IAM, mientras que el dolor pleurítico, posicional o
reproducible a la palpación lo hacen muy improbable (LR 0.2-0.3).

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
