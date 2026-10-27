---
titulo: Protocolo de neumonía infantil
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Neumonía infantil (neumonía pediátrica, neumonía radiográfica del
  niño, neumonía adquirida en la comunidad en la infancia).
version: 0.1.0-borrador

condicion:
  nombre: Neumonía infantil
  codigos:
    holonmed: HM:6036

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0200   # Dolor
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
  - nombre: Hipoxemia
    codigos: { holonmed: "HM:0110" }
    rol: apoyo
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ 2.8 para saturación de oxígeno ≤ 96%
    # LR− 0.47 para saturación de oxígeno > 96%
    # Shah SN et al. JAMA 2017;318:462-471. PMID 28763554.
    # doi:10.1001/jama.2017.9039. LR+ IC95% [2.1, 3.6]; umbral: saturación
    # de oxígeno ≤ 96%. LR− IC95% [0.32, 0.67]; umbral: saturación de
    # oxígeno > 96%. Junto con el aumento del trabajo respiratorio, es lo
    # que la fuente señala como más asociado a la neumonía, por encima de la
    # taquipnea y de la auscultación.

  - nombre: Aumento del trabajo respiratorio
    codigos: { holonmed: "HM:3145" }
    rol: apoyo
    lr: 2.1
    fuente: >-
      Shah SN et al. JAMA 2017;318:462-471. PMID 28763554.
      doi:10.1001/jama.2017.9039. IC95% [1.6, 2.7]. Quejido, aleteo y
      tiraje medidos en conjunto, no por separado. El otro signo que la
      fuente destaca; se mide como bloque y no admite desglose.

  - nombre: Dolor torácico
    codigos: { holonmed: "HM:0206" }
    rol: prueba_especifica
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Shah SN et al. JAMA 2017;318:462-471. PMID 28763554.
    # doi:10.1001/jama.2017.9039. Población: dos estudios que incluían
    # adolescentes.

  - nombre: Fiebre
    codigos: { holonmed: "HM:0101" }
    rol: apoyo
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ None para temperatura > 37.5 °C
    # Shah SN et al. JAMA 2017;318:462-471. PMID 28763554.
    # doi:10.1001/jama.2017.9039. umbral: temperatura > 37.5 °C.

  - nombre: Taquipnea
    codigos: { holonmed: "HM:0106" }
    rol: apoyo
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ 1.5 para frecuencia respiratoria > 40 por minuto
    # Shah SN et al. JAMA 2017;318:462-471. PMID 28763554.
    # doi:10.1001/jama.2017.9039. IC95% [1.3, 1.7]; umbral: frecuencia
    # respiratoria > 40 por minuto. La conclusión de la fuente es explícita
    # en que la taquipnea pesa MENOS que la hipoxemia y el trabajo
    # respiratorio, al contrario de lo que sugiere su papel en los
    # algoritmos de cribado.

  - nombre: Crepitantes
    codigos: { holonmed: "HM:0406" }
    rol: manifestacion
    lr: 1.0
    # sin_efecto en el índice: se reconoce el término pero no desplaza la
    # probabilidad. La fuente afirma que los hallazgos auscultatorios no se
    # asociaron al diagnóstico, pero no publica su cociente. Es un resultado
    # medido de ausencia de efecto, no una laguna: por eso sin_efecto y no
    # no_medido.

laboratorio:
  - parametro: Saturación de oxígeno
    corte_inferior: 92
    termino_si_bajo: Hipoxemia
    codigos: { holonmed: "HM:0110" }

  - parametro: Temperatura
    corte_superior: 38.0
    termino_si_alto: Fiebre
    codigos: { holonmed: "HM:0101" }

  - parametro: Frecuencia respiratoria
    corte_superior: 20
    termino_si_alto: Taquipnea
    codigos: { holonmed: "HM:0106" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6036
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE NEUMONÍA INFANTIL

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
   - «Saturación de oxígeno 78.2» → *Hipoxemia*
   - «Temperatura 49» → *Fiebre*
   - «Frecuencia respiratoria 26» → *Taquipnea*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

Aunque ningún hallazgo aislado diferencia de forma fiable la neumonía de
otras causas de enfermedad respiratoria infantil, la hipoxia y el aumento
del trabajo respiratorio son más importantes que la taquipnea y que los
hallazgos auscultatorios.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
