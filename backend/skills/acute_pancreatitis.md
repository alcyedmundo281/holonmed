---
titulo: Protocolo de pancreatitis aguda
descripcion: >-
  Dolor epigástrico en cinturón, enzimas pancreáticas elevadas, factores
  de riesgo biliares o enólicos.
version: "2.0.0"

condicion:
  nombre: Pancreatitis aguda
  codigos:
    snomed: "197456007"

# Ramas del grafo sobre las que actúa este protocolo. Permite preguntar
# qué protocolos aplican a un paciente a partir de los hallazgos que ya
# tiene, en vez de que el triaje decida sólo con el texto de hoy.
ambito_grafo:
  - HM:0730   # Alteración enzimática
  - HM:0201   # Dolor abdominal
  - HM:0720   # Alteración electrolítica

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  probabilidad_base: 0.05

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — "bebedor de riesgo" no
  # contiene "alcohol", y sin la variante el factor nunca se aplica.
  factores_riesgo:
    alcohol: 2.8
    alcoholismo: 2.8
    enolismo: 2.8
    etilismo: 2.8
    bebedor: 2.8
    litiasis: 3.2
    colelitiasis: 3.2
    coledocolitiasis: 3.2
    cálculos biliares: 3.2
    calculos biliares: 3.2
    hipertrigliceridemia: 2.2
    cpre: 2.5

# El `rol` no es decorativo: dice en qué dirección mueve la probabilidad.
#   prueba_especifica  su LR+ confirma cuando es positiva
#   prueba_sensible    su LR- descarta cuando es negativa
#   manifestacion      fija la sospecha de partida
#   apoyo              aporta poco por sí solo
#
# Cada LR debe citar su fuente. Un likelihood ratio sin procedencia es un
# número inventado con formato científico.
#
# `lr_negativo` sólo tiene sentido donde la ausencia sea informativa. Que
# no haya signo de Cullen no dice nada: es raro incluso en la enfermedad.
signos:
  - nombre: Hiperlipasemia (>3x)
    codigos: { holonmed: "HM:0732", snomed: "10443000" }
    rol: prueba_especifica
    lr: 26.6
    lr_negativo: 0.1
    fuente: >-
      JAMA Rational Clinical Examination. Criterio de referencia; el LR más
      alto de la serie. Una lipasa normal descarta con fuerza.

  - nombre: Hiperamilasemia (>3x)
    codigos: { holonmed: "HM:0731", snomed: "10427000" }
    rol: prueba_especifica
    lr: 12.5
    lr_negativo: 0.3
    fuente: >-
      JAMA Rational Clinical Examination. Fuerte, pero menos específica que
      la lipasa: se eleva también en patología salival y otras causas, y
      se normaliza antes.

  - nombre: Dolor epigástrico
    codigos: { holonmed: "HM:0202", snomed: "79922009" }
    rol: manifestacion
    lr: 2.1
    lr_negativo: 0.2
    fuente: >-
      GetTheDiagnosis.org. Sensible pero poco específico; su ausencia hace
      la pancreatitis bastante improbable.

  - nombre: Vómitos
    codigos: { holonmed: "HM:0302", snomed: "422400008" }
    rol: apoyo
    lr: 1.6
    fuente: GetTheDiagnosis.org. Síntoma común, aporta poca certeza solo.

  - nombre: Irritación peritoneal
    codigos: { holonmed: "HM:0601", snomed: "271956003" }
    rol: apoyo
    lr: 2.2
    fuente: GetTheDiagnosis.org. Signo de irritación peritoneal (Blumberg).

  - nombre: Signo de Cullen
    codigos: { holonmed: "HM:0611", snomed: "45002005" }
    rol: apoyo
    lr: 8.0
    fuente: >-
      Raro pero específico de pancreatitis necrotizante o hemorrágica. Su
      ausencia no descarta nada, y por eso no declara lr_negativo.

  - nombre: Hallazgos de imagen compatibles con pancreatitis
    codigos: { holonmed: "HM:0901" }
    rol: imagen
    lr: 9.0
    fuente: >-
      Tercer criterio de Atlanta. La TC con contraste es la referencia; la
      ecografía sirve sobre todo para buscar la causa biliar.

# Criterios de clasificación de Atlanta 2012.
#
# Parecen booleanos y son bayesianos: la manifestación fija la
# probabilidad pre-test, la prueba específica la confirma, y el «2 de 3»
# es la abreviatura de que el posterior cruza el umbral de tratamiento.
#
# Un criterio del que no hay información NO es un criterio negativo: es un
# vacío, y el sistema lo señala para que se pida.
clasificacion:
  nombre: Criterios de Atlanta 2012
  fuente: >-
    Banks PA, Bollen TL, Dervenis C, et al. Classification of acute
    pancreatitis 2012. Gut. 2013;62(1):102-111.
  requiere: 2
  criterios:
    - nombre: Dolor abdominal característico
      rol: manifestacion
      satisface_si: ["HM:0205", "HM:0202"]

    - nombre: Enzimas pancreáticas más de 3 veces el límite
      rol: prueba_especifica
      satisface_si: ["HM:0731", "HM:0732"]

    - nombre: Hallazgos de imagen compatibles
      rol: imagen
      satisface_si: ["HM:0901"]

  produce:
    termino: Pancreatitis aguda
    codigos: { holonmed: "HM:1002", snomed: "197456007" }
    semantica: trastorno

laboratorio:
  - parametro: Amilasa
    corte_superior: 110
    multiplicador: 3
    termino_si_alto: Hiperamilasemia (>3x)
    codigos: { holonmed: "HM:0731", snomed: "10427000" }

  - parametro: Lipasa
    corte_superior: 60
    multiplicador: 3
    termino_si_alto: Hiperlipasemia (>3x)
    codigos: { holonmed: "HM:0732", snomed: "10443000" }

  - parametro: Leucocitos
    corte_superior: 11000
    termino_si_alto: Leucocitosis
    codigos: { holonmed: "HM:0712", snomed: "767002" }

  - parametro: Calcio sérico
    corte_inferior: 8.5
    termino_si_bajo: Hipocalcemia
    codigos: { holonmed: "HM:0721", snomed: "5291005" }

  - parametro: Hematocrito
    corte_superior: 44
    termino_si_alto: Hemoconcentración
    codigos: { holonmed: "HM:0716", snomed: "45643008" }

  - parametro: Frecuencia cardíaca
    corte_superior: 100
    termino_si_alto: Taquicardia
    codigos: { holonmed: "HM:0104", snomed: "3424008" }

  - parametro: Presión arterial sistólica
    corte_inferior: 90
    termino_si_bajo: Hipotensión arterial
    codigos: { holonmed: "HM:0109", snomed: "45007003" }
---

# PROTOCOLO DE PANCREATITIS AGUDA

ROL: gastroenterólogo experto, basado en evidencia.

## Contexto fisiopatológico

- **Dónde**: páncreas, epigastrio, retroperitoneo.
- **Cómo**: inflamación, necrosis, respuesta inflamatoria sistémica.
- **Por qué**: litiasis biliar, consumo de alcohol, hipertrigliceridemia,
  post-CPRE.

## Instrucciones de extracción

1. Analiza los signos vitales, la exploración y el texto libre.
2. **Interpreta los valores numéricos** con los cortes declarados arriba.
   Extrae el hallazgo clínico, nunca la cifra suelta:
   - «Calcio 7.5» → *Hipocalcemia*
   - «Leucocitos 18.500» → *Leucocitosis*
   - «FC 115» → *Taquicardia*
3. Para enzimas, prioriza los términos con **(>3x)** cuando el valor
   supere tres veces el límite alto. Es el umbral que distingue una
   elevación inespecífica de una compatible con pancreatitis.
4. **No confundas amilasa con lipasa.** Son enzimas distintas con
   especificidad distinta, y el validador bloquea el emparejamiento.
5. **No saltes del síntoma al diagnóstico.** «Dolor epigástrico» es un
   hallazgo; «pancreatitis» es la hipótesis que este protocolo evalúa, no
   algo que se extraiga del texto.
6. Ignora los hallazgos negados: «sin fiebre» no genera ningún infón.

## Banderas rojas

Si aparecen, señálalas: sugieren pancreatitis grave y cambian la conducta.

- Hipotensión o signos de hipoperfusión
- Oliguria
- Hipoxemia o taquipnea marcada
- Alteración del nivel de conciencia
- Hemoconcentración persistente pese a fluidoterapia
- Signo de Cullen o de Grey-Turner
