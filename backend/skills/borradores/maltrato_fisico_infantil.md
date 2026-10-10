---
titulo: Protocolo de maltrato físico infantil
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Maltrato físico infantil (traumatismo no accidental en niños,
  violencia física infantil, síndrome del niño maltratado).
version: 0.1.0-borrador

condicion:
  nombre: Maltrato físico infantil
  codigos:
    holonmed: HM:6024

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0600   # Signo de exploración

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
  - nombre: Hemorragias retinianas en niño pequeño
    codigos: { holonmed: "HM:3104" }
    rol: prueba_especifica
    lr: 11.0
    fuente: >-
      Shah SN et al. JAMA 2025;334:160-170. PMID 40257808.
      doi:10.1001/jama.2025.2216. IC95% [5.2, 23.0]. El signo
      oftalmológico clásico más específico de traumatismo craneoencefálico
      abusivo (AHT).

  - nombre: Lesión oral o desgarro del frenillo
    codigos: { holonmed: "HM:3100" }
    rol: prueba_especifica
    lr: 6.6
    fuente: >-
      Shah SN et al. JAMA 2025;334:160-170. PMID 40257808.
      doi:10.1001/jama.2025.2216. IC95% [2.8, 16.0]. Traumatismo centrado
      en la cavidad bucal por alimentación forzada o impacto directo.

  - nombre: Fracturas múltiples en serie esquelética
    codigos: { holonmed: "HM:3108" }
    rol: prueba_especifica
    lr: 5.9
    fuente: >-
      Shah SN et al. JAMA 2025;334:160-170. PMID 40257808.
      doi:10.1001/jama.2025.2216. IC95% [3.3, 10.0]. Hallazgo en el examen
      radiológico esquelético altamente discriminativo.

  - nombre: Equimosis con patrón
    codigos: { holonmed: "HM:3102" }
    rol: prueba_especifica
    lr: 5.6
    fuente: >-
      Shah SN et al. JAMA 2025;334:160-170. PMID 40257808.
      doi:10.1001/jama.2025.2216. IC95% [2.1, 15.0]. Hematomas con forma
      de objeto o marca anatómica incompatible con caídas accidentales.

  - nombre: Equimosis en nalgas o cuello
    codigos: { holonmed: "HM:3101" }
    rol: apoyo
    lr: 5.1
    fuente: >-
      Shah SN et al. JAMA 2025;334:160-170. PMID 40257808.
      doi:10.1001/jama.2025.2216. IC95% [1.8, 14.0]. Localización
      anatómica protegida indicativa de lesión infligida intencionalmente.

  - nombre: Hematoma subdural en lactante
    codigos: { holonmed: "HM:3106" }
    rol: apoyo
    lr: 3.2
    fuente: >-
      Shah SN et al. JAMA 2025;334:160-170. PMID 40257808.
      doi:10.1001/jama.2025.2216. IC95% [2.1, 4.8]. Complicación
      intracraneal frecuente en traumatismos por sacudida o impacto.

  - nombre: Fractura única en serie esquelética
    codigos: { holonmed: "HM:3107" }
    rol: apoyo
    lr: 1.8
    fuente: >-
      Shah SN et al. JAMA 2025;334:160-170. PMID 40257808.
      doi:10.1001/jama.2025.2216. IC95% [1.2, 2.7]. Incrementa
      modestamente el riesgo de maltrato pero requiere correlación con el
      mecanismo referido.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6024
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE MALTRATO FÍSICO INFANTIL

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

La presencia de hemorragias retinianas (LR+ 11.0), desgarro del frenillo
labial (LR+ 6.6), fracturas múltiples (LR+ 5.9) y hematomas con patrón o
en localizaciones protegidas (LR+ 5.1-5.6) son las banderas rojas con
mayor capacidad discriminativa para maltrato físico.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
