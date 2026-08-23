---
titulo: Protocolo de embarazo ectópico
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  Dolor abdominal bajo o sangrado vaginal en la gestación precoz, con
  prueba de embarazo positiva y útero que no muestra gestación
  intrauterina en la ecografía.
version: 1.0.0

condicion:
  nombre: Embarazo ectópico
  codigos:
    holonmed: HM:6016

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0200   # Dolor
  - HM:0600   # Signo de exploración
  - HM:0900   # Hallazgo de imagen
  - HM:3069   # Sangrado vaginal en la gestación precoz

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
  - nombre: Masa anexial sin gestación intrauterina en ecografía transvaginal
    codigos: { holonmed: "HM:3064" }
    rol: imagen
    lr: 111.0
    fuente: >-
      Crochet JR et al. JAMA 2013;309:1722-9. PMID 23613077.
      doi:10.1001/jama.2013.3914. IC95% [12, 1028]. Población: gestantes
      con dolor abdominal o sangrado vaginal en la gestación precoz (n =
      6885). El hallazgo que confirma. Con el útero vacío, una masa
      anexial mueve la probabilidad más que todo lo demás junto.

  - nombre: Anomalía anexial en ecografía transvaginal
    codigos: { holonmed: "HM:3065" }
    rol: imagen
    lr_negativo: 0.12
    fuente: >-
      Crochet JR et al. JAMA 2013;309:1722-9. PMID 23613077.
      doi:10.1001/jama.2013.3914. IC95% [0.03, 0.55]. Población: gestantes
      con dolor abdominal o sangrado vaginal en la gestación precoz (n =
      6885). La fuente lo expresa como el valor de NO encontrar anomalías
      anexiales, que es el cociente negativo de este hallazgo. La
      exploración anexial normal es lo que más baja la probabilidad, y es
      la otra mitad de por qué la ecografía transvaginal manda aquí.

  - nombre: Dolor a la movilización cervical
    codigos: { holonmed: "HM:3066" }
    rol: prueba_especifica
    lr: 4.9
    fuente: >-
      Crochet JR et al. JAMA 2013;309:1722-9. PMID 23613077.
      doi:10.1001/jama.2013.3914. IC95% [1.7, 14]. Población: gestantes
      con dolor abdominal o sangrado vaginal en la gestación precoz (n =
      1435).

  - nombre: Masa anexial en la exploración bimanual
    codigos: { holonmed: "HM:3067" }
    rol: apoyo
    lr: 2.4
    fuente: >-
      Crochet JR et al. JAMA 2013;309:1722-9. PMID 23613077.
      doi:10.1001/jama.2013.3914. IC95% [1.6, 3.7]. Población: gestantes
      con dolor abdominal o sangrado vaginal en la gestación precoz (n =
      1378). La misma masa vista en la ecografía vale 111 y palpada vale
      2.4. No es incoherencia: son dos pruebas distintas sobre el mismo
      órgano.

  - nombre: Dolor a la palpación anexial
    codigos: { holonmed: "HM:3068" }
    rol: apoyo
    lr: 1.9
    fuente: >-
      Crochet JR et al. JAMA 2013;309:1722-9. PMID 23613077.
      doi:10.1001/jama.2013.3914. IC95% [1.0, 3.5]. Población: gestantes
      con dolor abdominal o sangrado vaginal en la gestación precoz (n =
      1435).

  - nombre: Dolor abdominal
    codigos: { holonmed: "HM:0201" }
    rol: manifestacion
    # no_medido: es criterio de entrada del estudio, así que dentro de esa
    # población no hay contraste que medir. La fuente sí acota la anamnesis
    # entera: ningún componente pasa de un LR+ de 1.5
    # Crochet JR et al. JAMA 2013;309:1722-9. PMID 23613077.
    # doi:10.1001/jama.2013.3914.

  - nombre: Sangrado vaginal en la gestación precoz
    codigos: { holonmed: "HM:3069" }
    rol: manifestacion
    # no_medido: el otro criterio de entrada, con la misma acotación: ningún
    # componente de la anamnesis alcanza un LR+ de 1.5
    # Crochet JR et al. JAMA 2013;309:1722-9. PMID 23613077.
    # doi:10.1001/jama.2013.3914.

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6016
  commit: 22f8b9c
  generado: 2026-08-23
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE EMBARAZO ECTÓPICO

ROL: ginecólogo experto, basado en evidencia.

## Contexto fisiopatológico

- **Dónde**: trompa de Falopio en la gran mayoría de los casos;
  ocasionalmente ovario, cérvix o cavidad abdominal.
- **Cómo**: implantación del blastocisto fuera de la cavidad endometrial.
  El trofoblasto invade un tejido no preparado para sostener la
  gestación, que se distiende y puede romperse, con hemorragia hacia la
  cavidad peritoneal.
- **Por qué**: daño tubárico previo (enfermedad pélvica inflamatoria,
  cirugía tubárica, embarazo ectópico anterior), técnicas de
  reproducción asistida, dispositivo intrauterino in situ, tabaquismo.

## Instrucciones de extracción

1. Analiza los signos vitales, la exploración y el texto libre.
2. Extrae el hallazgo clínico, nunca la cifra suelta.
3. **La masa anexial por ecografía y la masa anexial por palpación son
   dos pruebas distintas, no la misma extraída dos veces.** La primera
   vale mucho más (LR 111) que la segunda (LR 2.4) precisamente porque
   son métodos diferentes sobre el mismo órgano: si el texto trae ambas,
   extrae ambas.
4. **Distingue el motivo de consulta del hallazgo que confirma.** Dolor
   abdominal y sangrado vaginal en la gestación precoz son lo que trae a
   la paciente a consulta, no lo que diagnostica: no tienen cociente
   propio en este modelo.
5. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.

## Lo que la fuente concluye

La ecografía transvaginal es la mejor prueba diagnóstica aislada para
evaluar a una mujer con sospecha de embarazo ectópico. La presencia de
dolor abdominal o sangrado vaginal en la gestación precoz debe llevar a
solicitar una ecografía transvaginal y una hCG sérica cuantitativa.

## Banderas rojas

No son un diagnóstico: son motivos para que un humano mire ahora, porque
sugieren rotura con hemoperitoneo.

- Hipotensión, taquicardia o signos de mala perfusión
- Dolor abdominal súbito e intenso, con o sin signos peritoneales
- Dolor referido al hombro (irritación diafragmática por hemoperitoneo)
- Síncope o presíncope
