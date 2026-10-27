---
titulo: Protocolo de hipertensión arterial secundaria pediátrica
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Hipertensión arterial secundaria pediátrica (HTA secundaria en
  niños, hipertensión renovascular o renal pediátrica).
version: 0.1.0-borrador

condicion:
  nombre: Hipertensión arterial secundaria pediátrica
  codigos:
    holonmed: HM:6025

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0600   # Signo de exploración

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.15
  # medida en: niños y adolescentes con confirmación de hipertensión
  # arterial
  # Nugent JT et al. JAMA 2023;329:1012-1021. PMID 36976276.
  # doi:10.1001/jama.2023.3184.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Microalbuminuria
    codigos: { holonmed: "HM:3113" }
    rol: prueba_especifica
    lr: 13.0
    fuente: >-
      Nugent JT et al. JAMA 2023;329:1012-1021. PMID 36976276.
      doi:10.1001/jama.2023.3184. IC95% [3.2, 53.0]. El marcador de daño
      orgánico o nefropatía subyacente con mayor LR positivo en niños
      hipertensos.

  - nombre: Carga tensional aumentada en monitorización ambulatoria (MAPA)
    codigos: { holonmed: "HM:3115" }
    rol: prueba_especifica
    lr: 4.8
    fuente: >-
      Nugent JT et al. JAMA 2023;329:1012-1021. PMID 36976276.
      doi:10.1001/jama.2023.3184. IC95% [1.8, 13.0]. Alteración en la
      monitorización ambulatoria que orienta fuertemente hacia etiología
      secundaria.

  - nombre: Antecedente familiar de hipertensión secundaria
    codigos: { holonmed: "HM:3109" }
    rol: apoyo
    lr: 4.7
    fuente: >-
      Nugent JT et al. JAMA 2023;329:1012-1021. PMID 36976276.
      doi:10.1001/jama.2023.3184. IC95% [1.5, 15.0]. Historia familiar de
      nefropatía o trastornos vasculares orienta al diagnóstico
      etiológico.

  - nombre: Peso menor o igual al percentil 10 en niño con hipertensión
    codigos: { holonmed: "HM:3110" }
    rol: apoyo
    lr: 4.5
    fuente: >-
      Nugent JT et al. JAMA 2023;329:1012-1021. PMID 36976276.
      doi:10.1001/jama.2023.3184. IC95% [1.8, 11.0]. La delgadez o bajo
      peso contrasta con la HTA primaria pediátrica típica asociada a
      obesidad.

  - nombre: Ácido úrico sérico menor de 5.5 mg/dL
    codigos: { holonmed: "HM:3114" }
    rol: apoyo
    lr: 3.6
    fuente: >-
      Nugent JT et al. JAMA 2023;329:1012-1021. PMID 36976276.
      doi:10.1001/jama.2023.3184. IC95% [1.5, 8.6]. Niveles de ácido úrico
      no elevados aumentan la sospecha de causa secundaria frente a
      primaria.

  - nombre: Antecedente de prematuridad
    codigos: { holonmed: "HM:3111" }
    rol: apoyo
    lr: 3.0
    fuente: >-
      Nugent JT et al. JAMA 2023;329:1012-1021. PMID 36976276.
      doi:10.1001/jama.2023.3184. IC95% [1.2, 7.5]. Antecedente perinatal
      asociado a oligonefronía o trombosis de arteria renal por catéter.

  - nombre: Edad menor o igual a 6 años con hipertensión arterial
    codigos: { holonmed: "HM:3112" }
    rol: apoyo
    lr: 2.8
    fuente: >-
      Nugent JT et al. JAMA 2023;329:1012-1021. PMID 36976276.
      doi:10.1001/jama.2023.3184. IC95% [1.3, 6.0]. A menor edad de
      presentación, mucho mayor probabilidad de hipertensión secundaria.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6025
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE HIPERTENSIÓN ARTERIAL SECUNDARIA PEDIÁTRICA

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

## Lo que la fuente concluye

En niños hipertensos, la microalbuminuria (LR+ 13.0), una elevada carga
tensional en el MAPA (LR+ 4.8), el bajo peso para la edad (LR+ 4.5) y el
debut en menores de 6 años (LR+ 2.8) son las principales claves clínicas
para sospechar hipertensión secundaria.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
