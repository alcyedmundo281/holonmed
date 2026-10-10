---
titulo: Protocolo de ascitis
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Ascitis (síndrome ascítico, ascitis abdominal, acumulación de
  líquido peritoneal, líquido libre intraabdominal).
version: 0.1.0-borrador

condicion:
  nombre: Ascitis
  codigos:
    snomed: 389026000
    cie10: R18
    holonmed: HM:6046

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0300   # Síntoma digestivo
  - HM:0600   # Signo de exploración
  - HM:0800   # Síntoma general
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
  - nombre: Líquido libre en receso hepatorrenal (espacio de Morrison)
    codigos: { holonmed: "HM:0902" }
    rol: imagen
    # no_medible: Estándar de referencia de la condición: la ecografía
    # abdominal define la presencia de líquido libre peritoneal frente a la
    # cual se calibran las maniobras físicas en la revisión sistemática de
    # Williams & Simel 1992 (sesgo de incorporación). Detecta desde 100 mL
    # de líquido libre peritoneal en recesos dependientes (Morrison,
    # esplenorrenal, Douglas), superando ampliamente el umbral de detección
    # de la exploración física clínica (> 1.5 L).

  - nombre: Signo de la onda líquida abdominal
    codigos: { holonmed: "HM:3178" }
    rol: prueba_especifica
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Williams JW Jr et al. JAMA 1992;267:2645-8. PMID 1573754.
    # doi:10.1001/jama.267.19.2645. Población: adultos con sospecha de
    # ascitis evaluados frente a ecografía abdominal como estándar de
    # referencia en la revisión sistemática JAMA RCE. La presencia de onda
    # líquida positiva confirma ascitis voluminosa (> 1.5-2 L) con la mayor
    # especificidad entre las maniobras físicas.

  - nombre: Matidez cambiante abdominal
    codigos: { holonmed: "HM:3179" }
    rol: prueba_especifica
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Williams JW Jr et al. JAMA 1992;267:2645-8. PMID 1573754.
    # doi:10.1001/jama.267.19.2645. Población: adultos con sospecha de
    # ascitis evaluados frente a ecografía abdominal como estándar de
    # referencia en la revisión sistemática JAMA RCE. El desplazamiento
    # gravitacional de la matidez hacia el lado dependiente al cambiar a
    # decúbito lateral confirma la presencia de líquido peritoneal libre.

  - nombre: Matidez en flancos abdominales
    codigos: { holonmed: "HM:3180" }
    rol: prueba_sensible
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Williams JW Jr et al. JAMA 1992;267:2645-8. PMID 1573754.
    # doi:10.1001/jama.267.19.2645. Población: adultos con sospecha de
    # ascitis evaluados frente a ecografía abdominal como estándar de
    # referencia en la revisión sistemática JAMA RCE. Maniobra de cribado
    # inicial por percusión: la ausencia de matidez en flancos reduce
    # fuertemente la probabilidad de ascitis (LR- 0.2-0.3).

  - nombre: Flancos abdominales abultados
    codigos: { holonmed: "HM:3181" }
    rol: apoyo
    # el índice trae cociente pero no se traslada ninguno todavía; ver el
    # informe.
    # Williams JW Jr et al. JAMA 1992;267:2645-8. PMID 1573754.
    # doi:10.1001/jama.267.19.2645. Población: adultos con sospecha de
    # ascitis evaluados frente a ecografía abdominal como estándar de
    # referencia en la revisión sistemática JAMA RCE.

  - nombre: Signo del charco
    codigos: { holonmed: "HM:3182" }
    rol: apoyo
    lr: 1.6
    lr_negativo: 0.8
    fuente: >-
      Williams JW Jr et al. JAMA 1992;267:2645-8. PMID 1573754.
      doi:10.1001/jama.267.19.2645. Población: adultos con sospecha de
      ascitis de bajo volumen evaluados en posición prona sobre codos y
      rodillas. Maniobra incómoda y de escasa ganancia diagnóstica; ante
      sospecha de ascitis mínima debe procederse directamente a ecografía
      abdominal.

  - nombre: Aumento del perímetro abdominal
    codigos: { holonmed: "HM:3183" }
    rol: manifestacion
    lr: 4.16
    lr_negativo: 0.17
    fuente: >-
      Williams JW Jr et al. JAMA 1992;267:2645-8. PMID 1573754.
      doi:10.1001/jama.267.19.2645. Población: adultos evaluados para
      detección de ascitis en la anamnesis clínica. La ausencia de aumento
      referido de la circunferencia abdominal o ropa apretada reduce
      significativamente la probabilidad de ascitis (LR- 0.17).

  - nombre: Ganancia de peso reciente
    codigos: { holonmed: "HM:3186" }
    rol: manifestacion
    lr: 3.2
    lr_negativo: 0.42
    fuente: >-
      Williams JW Jr et al. JAMA 1992;267:2645-8. PMID 1573754.
      doi:10.1001/jama.267.19.2645. Población: adultos evaluados para
      detección de ascitis en la anamnesis clínica.

  - nombre: Edema en miembros inferiores
    codigos: { holonmed: "HM:0604" }
    rol: manifestacion
    lr: 2.8
    lr_negativo: 0.1
    fuente: >-
      Williams JW Jr et al. JAMA 1992;267:2645-8. PMID 1573754.
      doi:10.1001/jama.267.19.2645. Población: adultos evaluados para
      detección de ascitis en exploración clínica. La ausencia de edema en
      tobillos o piernas descarta ascitis con gran poder excluyente (LR-
      0.10) en contexto de fallo sistémico o hipertensión portal.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6046
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE ASCITIS

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
