---
titulo: Triaje general
descripcion: >-
  Protocolo por defecto. Extrae hallazgos, signos vitales y banderas rojas
  cuando ningún protocolo específico encaja.
version: "2.0.0"

# Sin ámbito de grafo: este protocolo no se circunscribe a ninguna rama.
ambito_grafo: []

# Sin modelo bayesiano a propósito: el triaje general no estima la
# probabilidad de ninguna enfermedad concreta.

signos:
  - nombre: Fiebre
    codigos: { holonmed: "HM:0101" }
  - nombre: Taquicardia
    codigos: { holonmed: "HM:0104" }
  - nombre: Bradicardia
    codigos: { holonmed: "HM:0105" }
  - nombre: Taquipnea
    codigos: { holonmed: "HM:0106" }
  - nombre: Disnea
    codigos: { holonmed: "HM:0401" }
  - nombre: Ortopnea
    codigos: { holonmed: "HM:0407" }
  - nombre: Hipotensión arterial
    codigos: { holonmed: "HM:0109" }
  - nombre: Hipertensión arterial
    codigos: { holonmed: "HM:0108" }
  - nombre: Hipoxemia
    codigos: { holonmed: "HM:0110" }
  - nombre: Alteración del nivel de conciencia
    codigos: { holonmed: "HM:0501" }
  - nombre: Confusión
    codigos: { holonmed: "HM:0502" }
  - nombre: Síncope
    codigos: { holonmed: "HM:0505" }
  - nombre: Dolor torácico
    codigos: { holonmed: "HM:0206" }
  - nombre: Dolor abdominal
    codigos: { holonmed: "HM:0201" }
  - nombre: Cefalea
    codigos: { holonmed: "HM:0207" }
  - nombre: Náuseas
    codigos: { holonmed: "HM:0301" }
  - nombre: Vómitos
    codigos: { holonmed: "HM:0302" }
  - nombre: Diarrea
    codigos: { holonmed: "HM:0303" }
  - nombre: Tos
    codigos: { holonmed: "HM:0402" }
  - nombre: Astenia
    codigos: { holonmed: "HM:0801" }
  - nombre: Anemia
    codigos: { holonmed: "HM:0711" }
  - nombre: Leucocitosis
    codigos: { holonmed: "HM:0712" }
  - nombre: Leucopenia
    codigos: { holonmed: "HM:0713" }
  - nombre: Hiperglucemia
    codigos: { holonmed: "HM:0741" }
  - nombre: Hipoglucemia
    codigos: { holonmed: "HM:0742" }
  - nombre: Ictericia
    codigos: { holonmed: "HM:0305" }
  - nombre: Edema en miembros inferiores
    codigos: { holonmed: "HM:0604" }
  - nombre: Adenopatías
    codigos: { holonmed: "HM:0607" }
  - nombre: Palidez cutánea
    codigos: { holonmed: "HM:0605" }
  - nombre: Cianosis
    codigos: { holonmed: "HM:0606" }
  - nombre: Deshidratación
    codigos: { holonmed: "HM:0610" }

laboratorio:
  - parametro: Temperatura
    corte_superior: 38.0
    termino_si_alto: Fiebre
    codigos: { holonmed: "HM:0101" }
  - parametro: Frecuencia cardíaca
    corte_superior: 100
    corte_inferior: 60
    termino_si_alto: Taquicardia
    termino_si_bajo: Bradicardia
    codigos: { holonmed: "HM:0104" }
  - parametro: Frecuencia respiratoria
    corte_superior: 20
    termino_si_alto: Taquipnea
    codigos: { holonmed: "HM:0106" }
  - parametro: Presión arterial sistólica
    corte_superior: 140
    corte_inferior: 90
    termino_si_alto: Hipertensión arterial
    termino_si_bajo: Hipotensión arterial
    codigos: { holonmed: "HM:0108" }
  - parametro: Saturación de oxígeno
    corte_inferior: 92
    termino_si_bajo: Hipoxemia
    codigos: { holonmed: "HM:0110" }
  - parametro: Leucocitos
    corte_superior: 11000
    corte_inferior: 4000
    termino_si_alto: Leucocitosis
    termino_si_bajo: Leucopenia
    codigos: { holonmed: "HM:0712" }
  - parametro: Hemoglobina
    corte_inferior: 12.0
    termino_si_bajo: Anemia
    codigos: { holonmed: "HM:0711" }
  - parametro: Plaquetas
    corte_inferior: 150000
    termino_si_bajo: Trombocitopenia
    codigos: { holonmed: "HM:0714" }
  - parametro: Glucosa
    corte_superior: 126
    corte_inferior: 70
    termino_si_alto: Hiperglucemia
    termino_si_bajo: Hipoglucemia
    codigos: { holonmed: "HM:0741" }
  - parametro: Creatinina
    corte_superior: 1.3
    termino_si_alto: Elevación de creatinina
    codigos: { holonmed: "HM:0751" }
  - parametro: Sodio
    corte_superior: 145
    corte_inferior: 135
    termino_si_alto: Hipernatremia
    termino_si_bajo: Hiponatremia
    codigos: { holonmed: "HM:0724" }
  - parametro: Potasio
    corte_superior: 5.5
    corte_inferior: 3.5
    termino_si_alto: Hiperpotasemia
    termino_si_bajo: Hipopotasemia
    codigos: { holonmed: "HM:0726" }
  - parametro: Proteína C reactiva
    corte_superior: 10
    termino_si_alto: Elevación de proteína C reactiva
    codigos: { holonmed: "HM:0761" }
  - parametro: Lactato
    corte_superior: 2.0
    termino_si_alto: Hiperlactatemia
    codigos: { holonmed: "HM:0747" }
---

# TRIAJE GENERAL

ROL: médico internista general.

Es el protocolo por defecto: se activa cuando ninguno específico encaja.
No estima la probabilidad de ninguna enfermedad concreta, y por eso **no
declara modelo bayesiano**. Emitir una cifra aquí sería inventarla.

## Instrucciones de extracción

1. Extrae los hallazgos de forma atómica: un concepto por infón.
2. **Interpreta los valores numéricos** con los cortes declarados arriba.
   «FC 115» se extrae como *Taquicardia*, no como «FC 115».
3. **No conviertas síntomas en diagnósticos.** «Dolor torácico» es un
   hallazgo; «infarto» es una hipótesis que aquí no te corresponde emitir.
4. Ignora los hallazgos negados: «sin fiebre» no genera ningún infón.
5. Los signos exploratorios cuentan aunque no tengan cifra: «edemas en
   ambas piernas» sustenta *Edema en miembros inferiores*.

## Banderas rojas

No son un diagnóstico: son motivos para que un humano mire ahora.

- Alteración del nivel de conciencia
- Saturación de oxígeno < 92 % en aire ambiente
- Presión arterial sistólica < 90 mmHg
- Frecuencia respiratoria > 30 rpm
- Dolor torácico de perfil isquémico
- Signos de irritación peritoneal
- Fiebre en paciente inmunodeprimido
- Lactato > 2 mmol/L con hipotensión
