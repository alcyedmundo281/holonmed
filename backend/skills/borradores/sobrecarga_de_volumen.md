---
titulo: Protocolo de sobrecarga de volumen
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Sobrecarga de volumen (sobrecarga hídrica, hipervolemia,
  congestión volémica).
version: 0.1.0-borrador

condicion:
  nombre: Sobrecarga de volumen
  codigos:
    holonmed: HM:6037

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0400   # Síntoma respiratorio
  - HM:0600   # Signo de exploración
  - HM:0700   # Alteración analítica
  - HM:0900   # Hallazgo de imagen

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
  - nombre: Congestión vascular en la radiografía de tórax
    codigos: { holonmed: "HM:3147" }
    rol: imagen
    lr: 5.8
    fuente: >-
      Drum B et al. JAMA 2026;335:1159-1168. PMID 41729549.
      doi:10.1001/jama.2026.0446. IC95% [2.9, 11.5]. Con las cifras
      corregidas es el cociente positivo más alto de los doce, por encima
      del BNP. La conclusión de la fuente los nombra juntos como las dos
      pruebas más útiles para identificar la sobrecarga.

  - nombre: Péptido natriurético cerebral elevado
    codigos: { holonmed: "HM:3151" }
    rol: prueba_sensible
    efecto: excluye
    dispara_si: ausente
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ 4.2 para BNP ≥ 100 ng/mL
    # LR− 0.09 para BNP < 100 ng/mL
    # Drum B et al. JAMA 2026;335:1159-1168. PMID 41729549.
    # doi:10.1001/jama.2026.0446. LR+ IC95% [1.8, 10]; umbral: BNP ≥ 100
    # ng/mL. LR− IC95% [0.06, 0.16]; umbral: BNP < 100 ng/mL. La conclusión
    # de la fuente lo señala, junto con la ausencia de líneas B, como lo más
    # útil para EXCLUIR la sobrecarga: un BNP normal la hace muy poco
    # probable.

  - nombre: Ingurgitación yugular
    codigos: { holonmed: "HM:3146" }
    rol: apoyo
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ 4.1 para punto máximo de pulsación > 3 cm sobre el ángulo esternal
    # Drum B et al. JAMA 2026;335:1159-1168. PMID 41729549.
    # doi:10.1001/jama.2026.0446. IC95% [2.9, 5.6]; umbral: punto máximo de
    # pulsación > 3 cm sobre el ángulo esternal. El hallazgo de exploración
    # física con mejor rendimiento de la serie, y el más específico de los
    # doce.

  - nombre: Líneas B pulmonares bilaterales
    codigos: { holonmed: "HM:3148" }
    rol: imagen
    efecto: excluye
    dispara_si: ausente
    lr: 4.0
    lr_negativo: 0.09
    fuente: >-
      Drum B et al. JAMA 2026;335:1159-1168. PMID 41729549.
      doi:10.1001/jama.2026.0446. LR+ IC95% [2.7, 6.1]. LR− IC95% [0.04,
      0.23]. Su AUSENCIA es lo que la conclusión de la fuente convierte en
      decisión: junto con un BNP normal, es lo más útil para excluir la
      sobrecarga.

  - nombre: Colapsabilidad reducida de la vena cava inferior
    codigos: { holonmed: "HM:3149" }
    rol: imagen
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ 3.9 para índice de colapsabilidad < 50%
    # LR− 0.22 para índice de colapsabilidad ≥ 50%
    # Drum B et al. JAMA 2026;335:1159-1168. PMID 41729549.
    # doi:10.1001/jama.2026.0446. LR+ IC95% [2.5, 6.1]; umbral: índice de
    # colapsabilidad < 50%. LR− IC95% [0.11, 0.45]; umbral: índice de
    # colapsabilidad ≥ 50%.

  - nombre: Presión venosa yugular elevada por ecografía
    codigos: { holonmed: "HM:3150" }
    rol: imagen
    # el índice publica este cociente PARA UN UMBRAL y el motor no evalúa el
    # valor medido: aplicado tal cual, cualquier mención de la prueba
    # recibiría el cociente. No se traslada. Modela el corte como criterio
    # de `laboratorio` y cuelga el cociente del hallazgo umbralizado.
    # LR+ 2.9 para PVY ecográfica > 8 cm
    # LR− 0.27 para PVY ecográfica ≤ 8 cm
    # Drum B et al. JAMA 2026;335:1159-1168. PMID 41729549.
    # doi:10.1001/jama.2026.0446. LR+ IC95% [2.3, 3.7]; umbral: PVY
    # ecográfica > 8 cm. LR− IC95% [0.21, 0.34]; umbral: PVY ecográfica ≤ 8
    # cm.

  - nombre: Crepitantes
    codigos: { holonmed: "HM:0406" }
    rol: apoyo
    lr: 2.7
    fuente: >-
      Drum B et al. JAMA 2026;335:1159-1168. PMID 41729549.
      doi:10.1001/jama.2026.0446. IC95% [0.7, 4.5].

  - nombre: Edema en miembros inferiores
    codigos: { holonmed: "HM:0604" }
    rol: apoyo
    lr: 2.2
    fuente: >-
      Drum B et al. JAMA 2026;335:1159-1168. PMID 41729549.
      doi:10.1001/jama.2026.0446. IC95% [1.5, 3.1]. El más débil de los
      hallazgos de exploración con efecto medible: mueve la probabilidad,
      pero poco.

laboratorio:
  - parametro: Péptido natriurético cerebral en plasma
    corte_superior: 100
    termino_si_alto: Péptido natriurético cerebral elevado
    codigos: { holonmed: "HM:3151" }

  - parametro: Altura del punto máximo de pulsación sobre el ángulo esternal
    corte_superior: 3
    termino_si_alto: Ingurgitación yugular
    codigos: { holonmed: "HM:3146" }

  - parametro: Líneas B por espacio intercostal
    corte_superior: 3
    termino_si_alto: Líneas B pulmonares bilaterales
    codigos: { holonmed: "HM:3148" }

  - parametro: Índice de colapsabilidad de la vena cava inferior
    corte_inferior: 50
    termino_si_bajo: Colapsabilidad reducida de la vena cava inferior
    codigos: { holonmed: "HM:3149" }

  - parametro: Presión venosa yugular medida por ecografía
    corte_superior: 8
    termino_si_alto: Presión venosa yugular elevada por ecografía
    codigos: { holonmed: "HM:3150" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6037
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE SOBRECARGA DE VOLUMEN

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
   - «Péptido natriurético cerebral en plasma 130» → *Péptido natriurético cerebral elevado*
   - «Altura del punto máximo de pulsación sobre el ángulo esternal 4» → *Ingurgitación yugular*
   - «Líneas B por espacio intercostal 4» → *Líneas B pulmonares bilaterales*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

Un BNP de 100 ng/mL o más y la presencia de congestión vascular en la
radiografía de tórax pueden ser las pruebas más útiles para identificar a
los pacientes con sobrecarga de volumen. La ausencia de líneas B
pulmonares en la ecografía a pie de cama, o un BNP menor de 100 ng/mL,
pueden ser lo más útil para excluirla.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
