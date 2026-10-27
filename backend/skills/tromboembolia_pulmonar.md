---
titulo: Protocolo de tromboembolia pulmonar
# Frase con la que el triaje elige este protocolo. Descríbelo por lo que el
# paciente trae, no por el diagnóstico: el triaje sólo ha leído el texto de
# hoy.
descripcion: >-
  Disnea súbita o dolor torácico pleurítico con taquicardia o hipoxemia,
  en un paciente con factores trombóticos (cirugía, ingreso, cáncer,
  anticonceptivos hormonales) o con una dilatación del ventrículo derecho.
version: "1.0.0"

condicion:
  nombre: Tromboembolia pulmonar
  codigos:
    snomed: 59282003
    cie10: I26.9
    holonmed: HM:6044

# Ramas del grafo sobre las que actúa este protocolo: los padres de
# los conceptos enlazados. Poda las que sean demasiado generales.
ambito_grafo:
  - HM:0206   # Dolor torácico
  - HM:0400   # Síntoma respiratorio
  - HM:0710   # Alteración hematológica
  - HM:0900   # Hallazgo de imagen

modelo_bayesiano:
  # Prevalencia entre pacientes con SOSPECHA de TEP en urgencias, no en la
  # población general. 0.09 es el valor central del rendimiento de la angio-TC:
  #   · 9% (IC95% 6-12) sin regla de decisión y 12% (IC95% 11-14) con Wells,
  #     revisión sistemática de 4 estudios. Ann Emerg Med 2016. PMID 26747217.
  #     doi:10.1016/j.annemergmed.2015.11.005.
  #   · 3.4-5.9%, 9-10% y 6-8% en tres sistemas de urgencias de EE. UU.
  #     Vasc Med 2025. PMID 40521851. doi:10.1177/1358863X251337456.
  # Es el rendimiento sobre quienes llegaron a la tomografía, no sobre todos
  # los sospechosos, y no hay dato de Ecuador: sustitúyelo por el de tu
  # servicio en cuanto lo midas. Una serie de ecografía (39.9%, Falster,
  # Thorax 2021, PMID 34497138) sale de pacientes más seleccionados y no se usa.
  probabilidad_base: 0.09

  # OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las
  # variantes que un clínico escribe de verdad — «bebedor de riesgo» no
  # contiene «alcohol», y sin la variante el factor nunca se aplica.
  # El índice declara «Trombosis venosa profunda previa o concomitante» sin
  # peso.
  # nota: tras suspender la anticoagulación de una primera enfermedad
  # tromboembólica no provocada, la recurrencia es de 10.3 por 100 personas-
  # año el primer año (IC95% 8.6-12.1) y la incidencia acumulada del 36% a
  # los 10 años (IC95% 28-45). Metaanálisis de 18 estudios con 7515
  # pacientes; sin grupo sin antecedente, así que es un riesgo absoluto. La
  # fuente no trata la trombosis concomitante
  # Khan F et al. BMJ 2019;366:l4363. PMID 31340984. doi:10.1136/bmj.l4363.
  # El índice declara «Ingreso hospitalario o en residencia» sin peso.
  # nota: OR 8.0 (IC95% 4.5-14.2), independiente de los demás factores.
  # Casos y controles poblacional anidado de Olmsted County, 625 casos y 625
  # controles
  # Heit JA et al. Arch Intern Med 2000;160:809-15. PMID 10737280.
  # doi:10.1001/archinte.160.6.809.
  # El índice declara «Cirugía reciente» sin peso.
  # nota: OR 21.7 (IC95% 9.4-49.9); el resumen no la desglosa por tipo.
  # Traumatismo, OR 12.7 (IC95% 4.1-39.7)
  # Heit JA et al. Arch Intern Med 2000;160:809-15. PMID 10737280.
  # doi:10.1001/archinte.160.6.809.
  # El índice declara «Neoplasia maligna activa» sin peso.
  # nota: OR 4.1 (IC95% 1.9-8.5) sin quimioterapia y 6.5 (IC95% 2.1-20.2)
  # con ella
  # Heit JA et al. Arch Intern Med 2000;160:809-15. PMID 10737280.
  # doi:10.1001/archinte.160.6.809.
  # El índice declara «Anticonceptivos orales» sin peso.
  # nota: OR 5.0 (IC95% 4.2-5.8) frente a no usarlos; de 3.6 con
  # levonorgestrel a 7.3 con desogestrel. Casos y controles MEGA: mujeres
  # premenopáusicas menores de 50 años, 1524 casos y 1760 controles
  # van Hylckama Vlieg A et al. BMJ 2009;339:b2921. PMID 19679614.
  # doi:10.1136/bmj.b2921.
  # El índice declara «Terapia hormonal de la menopausia» sin peso.
  # nota: RR 1.86 (IC95% 1.39-2.50) frente a placebo o ningún tratamiento,
  # sin diferencia entre estrógeno solo y combinado con progestágeno.
  # Metaanálisis de 33 ensayos con 44 639 posmenopáusicas
  # Gu Y et al. BMC Womens Health 2024;24:60. PMID 38263123.
  # doi:10.1186/s12905-023-02788-0.
  #
  # NINGUNO DE ESTOS ODDS RATIO ENTRA AL CÁLCULO, y es una decisión, no un
  # olvido. Los de arriba (cirugía 21.7, ingreso 8.0, neoplasia 4.1 sin
  # quimioterapia / 6.5 con ella, anticonceptivos 5.0) proceden de casos y
  # controles contra población general. La probabilidad base de arriba ya es
  # la de pacientes con SOSPECHA de TEP, entre los cuales la cirugía reciente
  # es muy frecuente y es una de las razones de la sospecha: multiplicarla
  # otra vez cuenta dos veces lo mismo. Con ellos activos, «cirugía de cadera
  # hace 5 días y disnea» daba 68% (PROBABLE) sin un solo hallazgo con LR.
  # Para que vuelvan hace falta un cociente medido EN población con sospecha.
  #
  # Tampoco serían utilizables tal cual:
  #   · TVP/ETV previa: la fuente da una tasa absoluta de recurrencia
  #     (10.3 por 100 personas-año), no un cociente de odds.
  #   · Terapia hormonal de la menopausia: es un RR de ensayos, no un OR de
  #     casos y controles; mezclarlos en un producto de odds sería inventar.
  #
  # El efecto de quitarlos es que la probabilidad sólo se mueve con
  # hallazgos que tienen LR medido, y hoy son pocos: el protocolo lo dice en
  # voz alta en vez de sostener la cifra con un OR ajeno.
  factores_riesgo: {}

# Cada LR conserva la procedencia con la que entró en el índice.
# Un cociente sin fuente es un número inventado con formato científico.
signos:
  - nombre: Ventrículo derecho dilatado en ecografía
    codigos: { holonmed: "HM:3162" }
    rol: imagen
    lr: 3.12
    lr_negativo: 0.57
    fuente: >-
      Fields JM et al. J Am Soc Echocardiogr 2017;30:714--723. PMID
      28495379. doi:10.1016/j.echo.2017.03.004. LR+ IC95% [1.96, 4.97].
      LR− IC95% [0.47, 0.68]. Población: pacientes con sospecha clínica de
      embolia pulmonar evaluados mediante ecocardiografía transtorácica a
      pie de cama; metaanálisis de estudios de exactitud diagnóstica
      (Fields 2017). En el paciente inestable hemodinámicamente (shock o
      hipotensión arterial), el hallazgo inequívoco de sobrecarga del VD
      (relación VD/VI ≥ 1, aplanamiento septal o McConnell) apoya
      fuertemente la embolia pulmonar masiva y justifica considerar
      tratamiento de reperfusión de emergencia si la angio-TC es inviable.

  - nombre: Dímero D elevado
    codigos: { holonmed: "HM:3144" }
    rol: prueba_sensible
    lr_negativo: 0.1
    fuente: >-
      Wells PS et al. JAMA 2006;295:199--207. PMID 16403932.
      doi:10.1001/jama.295.2.199. Población: pacientes con sospecha de TEP
      y baja o intermedia probabilidad clínica pretest. Un valor de dímero
      D por debajo del umbral de corte ajustado por edad descarta el
      diagnóstico sin necesidad de angiografía por tomografía.

  - nombre: Disnea
    codigos: { holonmed: "HM:0401" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Taquicardia
    codigos: { holonmed: "HM:0104" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Dolor torácico pleurítico
    codigos: { holonmed: "HM:3133" }
    rol: manifestacion
    # no_medido: el índice no publica cociente

  - nombre: Hipoxemia
    codigos: { holonmed: "HM:0110" }
    rol: apoyo
    # no_medido: el índice no publica cociente

laboratorio:
  - parametro: Frecuencia cardíaca
    corte_superior: 100
    termino_si_alto: Taquicardia
    codigos: { holonmed: "HM:0104" }

  - parametro: Saturación de oxígeno
    corte_inferior: 92
    termino_si_bajo: Hipoxemia
    codigos: { holonmed: "HM:0110" }

# De dónde salió este archivo. No lo edites a mano: si vuelves a
# pasar el conversor, se regenera y el PR queda auditable.
procedencia:
  indice: medsemiotics-db
  condicion: HM:6044
  commit: 9505ae0
  generado: 2026-10-10
  herramienta: scripts/convertir_condicion.py
---

# PROTOCOLO DE TROMBOEMBOLIA PULMONAR

ROL: internista experto en enfermedad tromboembólica, basado en evidencia.

## Contexto fisiopatológico

- **Dónde**: arterias pulmonares, ventrículo derecho.
- **Cómo**: un trombo obstruye el lecho arterial pulmonar; desajuste
  ventilación-perfusión y aumento de la poscarga del ventrículo derecho.
- **Por qué**: trombosis venosa profunda, cirugía o ingreso reciente, cáncer
  activo, anticonceptivos u hormonas, tromboembolia previa.
## Instrucciones de extracción

1. Analiza los signos vitales, la exploración y el texto libre.
2. **Interpreta los valores numéricos** con los cortes declarados
   arriba. Extrae el hallazgo clínico, nunca la cifra suelta:
   - «Frecuencia cardíaca 130» → *Taquicardia*
   - «Saturación de oxígeno 78.2» → *Hipoxemia*
3. No infieras lo que no está escrito. Un dato que falta se pide, no
   se supone.
4. **Un dímero D no medido no es un dímero D normal.** Sólo se registra con
   un valor delante, y su utilidad para descartar es la de la fuente: en
   probabilidad clínica baja o intermedia, con corte ajustado por edad.
5. **No saltes del síntoma al diagnóstico.** «Disnea» y «dolor pleurítico»
   son hallazgos; «tromboembolia pulmonar» es la hipótesis que este
   protocolo evalúa, no algo que se extraiga del texto.
6. Ignora los hallazgos negados: «sin disnea» no genera ningún infón.

## Lo que la fuente concluye

La ecocardiografía a pie de cama muestra especificidad útil y sensibilidad
baja (53%) para la sospecha de TEP; su mayor utilidad reside en guiar el
manejo inmediato del paciente en shock o con contraindicación para
tomografía.

## Banderas rojas

Si aparecen, señálalas: sugieren embolia de alto riesgo y cambian la conducta.

- Hipotensión o signos de shock
- Síncope
- Hipoxemia marcada
- Ventrículo derecho dilatado o aplanamiento septal en la ecografía
