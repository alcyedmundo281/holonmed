---
titulo: Protocolo de síncope cardíaco
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Síncope cardíaco (síncope de origen cardíaco, síncope arrítmico).
version: 0.1.0-borrador

condicion:
  nombre: Síncope cardíaco
  codigos:
    snomed: 788877005
    cie10: R55
    holonmed: HM:6010

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0200   # Dolor
  - HM:0500   # Síntoma neurológico
  - HM:0505   # Síncope
  - HM:0606   # Cianosis
  - HM:3032   # Fibrilación o flutter auricular
  - HM:3033   # Cardiopatía estructural grave conocida

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.095
  # medida en: 822 participantes del Framingham Heart Study que refirieron
  # síncope durante un seguimiento medio de 17 años (población general,
  # 1971-1998)
  # Soteriades ES et al. N Engl J Med 2002;347:878-85. PMID 12239256.
  # doi:10.1056/NEJMoa012407.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Fibrilación o flutter auricular
    codigos: { holonmed: "HM:3032" }
    rol: prueba_especifica
    lr: 7.3
    fuente: >-
      Albassam OT et al. JAMA 2019;321:2448-2457. PMID 31237649.
      doi:10.1001/jama.2019.8001. IC95% [2.4, 22]. El antecedente que más
      desplaza hacia el origen cardíaco.

  - nombre: Cianosis presenciada durante el episodio
    codigos: { holonmed: "HM:3034" }
    rol: prueba_especifica
    lr: 6.2
    fuente: >-
      Albassam OT et al. JAMA 2019;321:2448-2457. PMID 31237649.
      doi:10.1001/jama.2019.8001. IC95% [1.6, 24]. Rarísima pero casi
      definitiva cuando la hay: especificidad del 99%. Depende de que
      alguien presenciara el episodio.

  - nombre: Cardiopatía estructural grave conocida
    codigos: { holonmed: "HM:3033" }
    rol: prueba_especifica
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Albassam OT et al. JAMA 2019;321:2448-2457. PMID 31237649.
    # doi:10.1001/jama.2019.8001. Rango entre 2 estudios; sensibilidad
    # 0.35-0.51, especificidad 0.84-0.93. Antecedente que apoya con fuerza
    # moderada.

  - nombre: Primer síncope a los 35 años o más
    codigos: { holonmed: "HM:3031" }
    rol: prueba_sensible
    lr: 3.3
    lr_negativo: 0.13
    fuente: >-
      Albassam OT et al. JAMA 2019;321:2448-2457. PMID 31237649.
      doi:10.1001/jama.2019.8001. LR+ IC95% [2.6, 4.1]. LR− IC95% [0.06,
      0.25]. La fuente lo expresa como el cociente de la edad menor de 35
      años, que es el negativo de este hallazgo. El dato más útil para
      DESCARTAR: un primer síncope antes de los 35 prácticamente excluye
      el origen cardíaco.

  - nombre: Cambio de humor o preocupación prodrómica por los detalles
    codigos: { holonmed: "HM:3035" }
    rol: apoyo
    lr: 0.09
    fuente: >-
      Albassam OT et al. JAMA 2019;321:2448-2457. PMID 31237649.
      doi:10.1001/jama.2019.8001. IC95% [0.02, 0.38]. Su presencia aleja
      del origen cardíaco y orienta a vasovagal.

  - nombre: Sensación de frío previa al síncope
    codigos: { holonmed: "HM:3036" }
    rol: apoyo
    lr: 0.16
    fuente: >-
      Albassam OT et al. JAMA 2019;321:2448-2457. PMID 31237649.
      doi:10.1001/jama.2019.8001. IC95% [0.06, 0.64]. Pródromo vegetativo;
      su presencia aleja del origen cardíaco.

  - nombre: Cefalea
    codigos: { holonmed: "HM:0207" }
    rol: apoyo
    lr: 0.17
    fuente: >-
      Albassam OT et al. JAMA 2019;321:2448-2457. PMID 31237649.
      doi:10.1001/jama.2019.8001. IC95% [0.06, 0.55]. Su presencia aleja
      del origen cardíaco.

  - nombre: Cambio de humor tras el síncope
    codigos: { holonmed: "HM:3037" }
    rol: apoyo
    lr: 0.21
    fuente: >-
      Albassam OT et al. JAMA 2019;321:2448-2457. PMID 31237649.
      doi:10.1001/jama.2019.8001. IC95% [0.06, 0.65]. Su presencia aleja
      del origen cardíaco.

  - nombre: Incapacidad para recordar la conducta previa al síncope
    codigos: { holonmed: "HM:3038" }
    rol: apoyo
    lr: 0.25
    fuente: >-
      Albassam OT et al. JAMA 2019;321:2448-2457. PMID 31237649.
      doi:10.1001/jama.2019.8001. IC95% [0.09, 0.69]. Su presencia aleja
      del origen cardíaco.

  - nombre: Síncope
    codigos: { holonmed: "HM:0505" }
    rol: manifestacion
    # no_medible: es el motivo de consulta que define la población
    # estudiada; la pregunta no es si hubo síncope sino si fue cardíaco

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6010
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE SÍNCOPE CARDÍACO

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

## Escalas

No son signos: combinan varios elementos y se leen por tramos.
holonmed no las calcula — si el texto trae la puntuación, úsala tal
como viene y aplica el tramo que corresponda.

### EGSYS

Componentes: seis variables clínicas, electrocardiograma incluido.

- **menor de 3**: 

Una puntuación menor de 3 es lo que mejor descarta el origen cardíaco.

## Lo que la fuente concluye

La exploración clínica, con el electrocardiograma dentro de puntuaciones
multivariable, puede identificar con precisión a los pacientes con y sin
síncope cardíaco.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
