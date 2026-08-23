---
titulo: Protocolo de apnea obstructiva del sueño
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  Somnolencia diurna, ronquido habitual o episodios de ahogo o jadeo
  nocturno, antes de decidir si derivar a estudio del sueño.
version: 1.0.0

condicion:
  nombre: Apnea obstructiva del sueño
  codigos:
    holonmed: HM:6018

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0400   # Síntoma respiratorio

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
  - nombre: Ahogo o jadeo nocturno
    codigos: { holonmed: "HM:3072" }
    rol: prueba_especifica
    lr: 3.3
    fuente: >-
      Myers KA et al. JAMA 2013;310:731-41. PMID 23989984.
      doi:10.1001/jama.2013.276185. IC95% [2.1, 4.6]. La observación
      aislada más útil de la revisión para identificar apnea obstructiva
      del sueño.

  - nombre: Ronquido
    codigos: { holonmed: "HM:3073" }
    rol: apoyo
    lr: 1.1
    fuente: >-
      Myers KA et al. JAMA 2013;310:731-41. PMID 23989984.
      doi:10.1001/jama.2013.276185. IC95% [1.0, 1.1]. Frecuente en la
      enfermedad, pero el cociente pegado a 1.0 significa que no sirve
      para establecer el diagnóstico por sí solo.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6018
  commit: 22f8b9c
  generado: 2026-08-23
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE APNEA OBSTRUCTIVA DEL SUEÑO

ROL: médico de atención primaria experto, basado en evidencia.

## Contexto fisiopatológico

- **Dónde**: vía aérea superior — orofaringe, base de la lengua, paladar
  blando.
- **Cómo**: colapso repetido de la vía aérea superior durante el sueño,
  con hipopneas y apneas que producen desaturación intermitente y
  fragmentación del sueño.
- **Por qué**: obesidad, retrognatia o micrognatia, hipertrofia
  amigdalina, consumo de alcohol o sedantes antes de dormir, congestión
  nasal crónica.

## Instrucciones de extracción

1. Analiza los signos vitales, la exploración y el texto libre.
2. Extrae el hallazgo clínico, nunca la cifra suelta.
3. **No confundas ronquido con ahogo o jadeo nocturno.** Son hallazgos
   distintos con pesos muy distintos: el ronquido es casi universal en la
   sospecha clínica y por eso no discrimina (LR cercano a 1); el ahogo o
   jadeo nocturno es el hallazgo que sí desplaza la probabilidad. Que un
   paciente ronque no implica que se ahogue durmiendo.
4. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

El ahogo o jadeo nocturno es el indicador clínico aislado más fiable de
apnea obstructiva del sueño; el ronquido, en cambio, es poco específico.
La exploración clínica es útil para seleccionar a quién derivar a pruebas
diagnósticas definitivas.

## Banderas rojas

No son un diagnóstico: son motivos para acelerar la derivación a estudio
del sueño o a evaluación urgente.

- Apneas presenciadas por un tercero, con desaturación importante
- Somnolencia diurna severa, en especial al conducir
- Hipertensión arterial resistente al tratamiento
- Arritmias nocturnas o signos de cor pulmonale
