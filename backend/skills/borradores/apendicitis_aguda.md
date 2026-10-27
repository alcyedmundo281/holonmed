---
titulo: Protocolo de apendicitis aguda
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  TODO. Apendicitis aguda (apendicitis, inflamación aguda del apéndice
  cecal).
version: 0.1.0-borrador

condicion:
  nombre: Apendicitis aguda
  codigos:
    snomed: 85189001
    cie10: K35.8
    holonmed: HM:6043

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0100   # Signo vital alterado
  - HM:0201   # Dolor abdominal
  - HM:0600   # Signo de exploración
  - HM:0710   # Alteración hematológica
  - HM:0900   # Hallazgo de imagen

modelo_bayesiano:
  # El índice no publica prevalencia para esta condición. Sin probabilidad
  # base el motor no arranca: pon la de tu población.
  probabilidad_base: 0.0

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  # El índice declara «Edad entre 10 y 19 años» sin peso.
  # nota: incidencia máxima de la vida, con 23.3 casos por 10 000 personas y
  # año
  # Addiss DG et al. Am J Epidemiol 1990;132:910-25. PMID 2239906.
  # doi:10.1093/oxfordjournals.aje.a115734.
  # El índice declara «Sexo masculino» sin peso.
  # nota: razón de tasas global de 1.4:1 frente a mujeres, mayor en todos
  # los grupos de edad; riesgo a lo largo de la vida del 8.6% en varones y
  # del 6.7% en mujeres
  # Addiss DG et al. Am J Epidemiol 1990;132:910-25. PMID 2239906.
  # doi:10.1093/oxfordjournals.aje.a115734.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Signo ecográfico de apendicitis aguda
    codigos: { holonmed: "HM:3177" }
    rol: imagen
    lr: 2.29
    lr_negativo: 0.24
    fuente: >-
      Becker BA et al. Acad Emerg Med 2022;29:164-173. PMID 34420255.
      doi:10.1111/acem.14378. LR+ IC95% [1.85, 2.84]. LR− IC95% [0.14,
      0.42]. Población: adultos que consultan en servicios de urgencias
      con dolor abdominal y sospecha de apendicitis evaluados mediante
      POCUS por médicos de urgencias (estudio prospectivo observacional
      multicéntrico, n = 256). Hallazgo positivo (apéndice no compresible
      > 6 mm en FID con dolor local): apoya fuertemente la sospecha de
      apendicitis e indica valoración quirúrgica inmediata.

  - nombre: Dolor en fosa ilíaca derecha
    codigos: { holonmed: "HM:0204" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Irritación peritoneal
    codigos: { holonmed: "HM:0601" }
    rol: prueba_especifica
    # no_medido: el índice no publica cociente

  - nombre: Leucocitosis
    codigos: { holonmed: "HM:0712" }
    rol: apoyo
    # no_medido: el índice no publica cociente

  - nombre: Fiebre
    codigos: { holonmed: "HM:0101" }
    rol: apoyo
    # no_medido: el índice no publica cociente

laboratorio:
  - parametro: Diámetro externo máximo anteroposterior del apéndice cecal
    corte_superior: 6.0
    termino_si_alto: Signo ecográfico de apendicitis aguda
    codigos: { holonmed: "HM:3177" }

  - parametro: Leucocitos
    corte_superior: 11000
    termino_si_alto: Leucocitosis
    codigos: { holonmed: "HM:0712" }

  - parametro: Temperatura
    corte_superior: 38.0
    termino_si_alto: Fiebre
    codigos: { holonmed: "HM:0101" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6043
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE APENDICITIS AGUDA

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
   - «Diámetro externo máximo anteroposterior del apéndice cecal 8» → *Signo ecográfico de apendicitis aguda*
   - «Leucocitos 14,300» → *Leucocitosis*
   - «Temperatura 49» → *Fiebre*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

La ecografía a pie de cama es moderadamente precisa para la sospecha de
apendicitis en urgencias; acelera la decisión quirúrgica ante hallazgo
positivo inequívoco pero requiere confirmación tomográfica cuando el
apéndice no es visualizado.

## Formato de salida

<!-- Cópialo del protocolo que más se le parezca de los ya escritos.
     Un formato distinto por protocolo rompe el pipeline de registro. -->
