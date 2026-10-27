---
titulo: Protocolo de trombosis venosa profunda
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Trombosis venosa profunda (TVP, trombosis venosa profunda de
  miembros inferiores, trombosis de venas profundas).
version: 0.1.0-borrador

condicion:
  nombre: Trombosis venosa profunda
  codigos:
    holonmed: HM:6035

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0710   # Alteración hematológica

modelo_bayesiano:
  # Prevalencia en la población que atiendes, no en la literatura mundial.
  # El valor del índice queda abajo como referencia.
  probabilidad_base: 0.19
  # medida en: pacientes ambulatorios consecutivos y no seleccionados con
  # sospecha clínica de TVP, sin antecedente de TVP previa salvo que el
  # modelo lo incorporase
  # Wells PS et al. JAMA 2006;295:199--207. PMID 16403932.
  # doi:10.1001/jama.295.2.199.

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Dímero D elevado
    codigos: { holonmed: "HM:3144" }
    rol: prueba_sensible
    efecto: evidencia
    lr_negativo: 0.1
    fuente: >-
      Wells PS et al. JAMA 2006;295:199--207. PMID 16403932.
      doi:10.1001/jama.295.2.199. IC95% [0.03, 0.37]. Población: sospecha
      clínica baja, ensayo de alta sensibilidad. Es la lectura que la
      conclusión de la fuente convierte en decisión. Un dímero D normal
      descarta la TVP con fuerza, pero cuánta depende de dos cosas que hay
      que saber antes de aplicarlo: qué ensayo se usó y en qué estrato de
      probabilidad previa está el paciente.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6035
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE TROMBOSIS VENOSA PROFUNDA

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

### Regla de predicción clínica para TVP

Componentes: el abstract no los enumera; catorce estudios con más de 8000 pacientes aplicaron una regla de predicción clínica antes del dímero D o la imagen.

- **probabilidad clínica baja**: 
- **probabilidad clínica moderada**: 
- **probabilidad clínica alta**: 

Estimar la probabilidad clínica antes de pedir pruebas es lo que mejora la exactitud diagnóstica, según la conclusión de la fuente.

## Lo que la fuente concluye

La exactitud diagnóstica de la TVP mejora cuando se estima la probabilidad
clínica antes de las pruebas. Los pacientes con probabilidad baja en la
regla de predicción tienen una prevalencia de TVP menor del 5%. En
pacientes con probabilidad baja y dímero D negativo, el diagnóstico de TVP
puede excluirse sin ecografía; en pacientes con sospecha clínica alta, el
resultado no debería modificar las decisiones clínicas.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
