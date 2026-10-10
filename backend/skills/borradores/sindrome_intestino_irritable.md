---
titulo: Protocolo de síndrome de intestino irritable
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Síndrome de intestino irritable (colon irritable, SII, intestino
  irritable).
version: 0.1.0-borrador

condicion:
  nombre: Síndrome de intestino irritable
  codigos:
    snomed: 10743008
    cie10: K58
    holonmed: HM:6002

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0200   # Dolor
  - HM:0300   # Síntoma digestivo
  - HM:0710   # Alteración hematológica
  - HM:0800   # Síntoma general

modelo_bayesiano:
  # El índice publica prevalencia (0.57) pero ningún signo de este protocolo
  # trae un LR utilizable, así que el modelo bayesiano no se activa. Cuando
  # haya cocientes, pon aquí la de tu población.
  probabilidad_base: 0.0

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  # El índice declara «Enteritis infecciosa en los 12 meses previos» sin
  # peso.
  # nota: riesgo relativo 4.2 (IC95% 3.1-5.7) frente a quien no la tuvo; 2.3
  # (IC95% 1.8-3.0) si fue hace más de 12 meses. Metaanálisis de 45 estudios
  # de cohortes
  # Klem F et al. Gastroenterology 2017;152:1042-1054.e1. PMID 28069350.
  # doi:10.1053/j.gastro.2016.12.039.
  # El índice declara «Sexo femenino» sin peso.
  # nota: OR 1.67 (IC95% 1.53-1.82) frente a varones en la población
  # general; 80 poblaciones, 260 960 adultos
  # Lovell RM et al. Clin Gastroenterol Hepatol 2012;10:712-721.e4. PMID
  # 22426087. doi:10.1016/j.cgh.2012.02.029.
  # El índice declara «Edad menor de 50 años» sin peso.
  # nota: en mayores de 50 años la prevalencia es menor, OR 0.75 (IC95%
  # 0.62-0.92) frente a menores de 50
  # Lovell RM et al. Clin Gastroenterol Hepatol 2012;10:712-721.e4. PMID
  # 22426087. doi:10.1016/j.cgh.2012.02.029.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Dolor abdominal
    codigos: { holonmed: "HM:0201" }
    rol: manifestacion
    # no_medido: el índice no publica cociente
    # Mearin F et al. Gastroenterology 2016. PMID 27144627.
    # doi:10.1053/j.gastro.2016.02.031.

  - nombre: Diarrea
    codigos: { holonmed: "HM:0303" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Estreñimiento
    codigos: { holonmed: "HM:0304" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Anemia
    codigos: { holonmed: "HM:0711" }
    rol: apoyo
    efecto: bandera_roja
    # no_medido: el índice no publica cociente
    # Park afirma que la anemia, pese a su sensibilidad pobre para
    # enfermedad orgánica, ofrece muy buena especificidad. No publica
    # cifras: ninguna sensibilidad, especificidad, OR ni cociente acompaña a
    # esa frase, así que se queda en consenso_con_afirmacion y no sube a
    # discriminacion_medida. Solo subiría si alguien lee el texto completo,
    # que está en coreano y no tiene versión en PMC. Registrado para que el
    # próximo no repita la búsqueda.
    # Park JH et al. Korean J Gastroenterol 2010;55:308-15. PMID 20697190.
    # doi:10.4166/kjg.2010.55.5.308.

  - nombre: Pérdida de peso
    codigos: { holonmed: "HM:0803" }
    rol: apoyo
    efecto: bandera_roja
    # no_medido: el índice no publica cociente
    # Misma afirmación de Park y mismas condiciones que la anemia: buena
    # especificidad para enfermedad orgánica, sin cifras publicadas.
    # Park JH et al. Korean J Gastroenterol 2010;55:308-15. PMID 20697190.
    # doi:10.4166/kjg.2010.55.5.308.

laboratorio:
  - parametro: Hemoglobina
    corte_inferior: 12.0
    termino_si_bajo: Anemia
    codigos: { holonmed: "HM:0711" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6002
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE SÍNDROME DE INTESTINO IRRITABLE

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
   - «Hemoglobina 10.2» → *Anemia*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Signos de alarma

Apuntan fuera de este cuadro y obligan a estudiar antes de etiquetar.
Si aparece alguno, dilo explícitamente en la valoración:

- **Anemia** (HM:0711)
- **Pérdida de peso** (HM:0803)

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
