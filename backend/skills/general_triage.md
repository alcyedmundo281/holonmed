# SKILL: TRIAJE GENERAL

ROL: Médico internista general.
OBJETIVO: Extraer hallazgos clínicos, signos vitales y banderas rojas de
una narrativa sin protocolo específico. Es el protocolo por defecto: se
activa cuando ningún otro encaja claramente.

BASE DE CONOCIMIENTO (JSON-LD):

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalGuideline",
  "name": "Triaje general",

  "criterios_laboratorio": {
    "instruccion": "Interpreta los valores numéricos con estos rangos de referencia en adultos. Extrae el hallazgo clínico, no el número.",
    "reglas": [
      {
        "parametro": "Temperatura",
        "corte_superior": 38.0,
        "termino_si_alto": "Fiebre",
        "snomed_id": "386661006"
      },
      {
        "parametro": "Frecuencia cardíaca",
        "corte_superior": 100,
        "corte_inferior": 60,
        "termino_si_alto": "Taquicardia",
        "termino_si_bajo": "Bradicardia",
        "snomed_id": "3424008"
      },
      {
        "parametro": "Frecuencia respiratoria",
        "corte_superior": 20,
        "termino_si_alto": "Taquipnea",
        "snomed_id": "271823003"
      },
      {
        "parametro": "Presión arterial sistólica",
        "corte_superior": 140,
        "corte_inferior": 90,
        "termino_si_alto": "Hipertensión arterial",
        "termino_si_bajo": "Hipotensión arterial",
        "snomed_id": "38341003"
      },
      {
        "parametro": "Saturación de oxígeno",
        "corte_inferior": 92,
        "termino_si_bajo": "Hipoxemia",
        "snomed_id": "389087006"
      },
      {
        "parametro": "Leucocitos",
        "corte_superior": 11000,
        "corte_inferior": 4000,
        "termino_si_alto": "Leucocitosis",
        "termino_si_bajo": "Leucopenia",
        "snomed_id": "767002"
      },
      {
        "parametro": "Hemoglobina",
        "corte_inferior": 12.0,
        "termino_si_bajo": "Anemia",
        "snomed_id": "271737000"
      },
      {
        "parametro": "Glucosa",
        "corte_superior": 126,
        "corte_inferior": 70,
        "termino_si_alto": "Hiperglucemia",
        "termino_si_bajo": "Hipoglucemia",
        "snomed_id": "80394007"
      },
      {
        "parametro": "Creatinina",
        "corte_superior": 1.3,
        "termino_si_alto": "Creatinina elevada",
        "snomed_id": "166717003"
      }
    ]
  },

  "signDetected": [
    { "name": "Fiebre", "snomed_id": "386661006" },
    { "name": "Taquicardia", "snomed_id": "3424008" },
    { "name": "Bradicardia", "snomed_id": "48867003" },
    { "name": "Taquipnea", "snomed_id": "271823003" },
    { "name": "Disnea", "snomed_id": "267036007" },
    { "name": "Hipotensión arterial", "snomed_id": "45007003" },
    { "name": "Hipertensión arterial", "snomed_id": "38341003" },
    { "name": "Hipoxemia", "snomed_id": "389087006" },
    { "name": "Alteración del nivel de conciencia", "snomed_id": "419284004" },
    { "name": "Dolor torácico", "snomed_id": "29857009" },
    { "name": "Dolor abdominal", "snomed_id": "21522001" },
    { "name": "Cefalea", "snomed_id": "25064002" },
    { "name": "Náuseas", "snomed_id": "422587007" },
    { "name": "Vómitos", "snomed_id": "422400008" },
    { "name": "Diarrea", "snomed_id": "62315008" },
    { "name": "Tos", "snomed_id": "49727002" },
    { "name": "Astenia", "snomed_id": "13791008" },
    { "name": "Anemia", "snomed_id": "271737000" },
    { "name": "Leucocitosis", "snomed_id": "767002" },
    { "name": "Hiperglucemia", "snomed_id": "80394007" }
  ]
}
```

## BANDERAS ROJAS

Marca de forma destacada si aparece cualquiera de estas situaciones. No
son un diagnóstico: son motivos para que un humano mire ahora.

- Alteración del nivel de conciencia
- Saturación de oxígeno < 92 % en aire ambiente
- Presión arterial sistólica < 90 mmHg
- Frecuencia respiratoria > 30 rpm
- Dolor torácico de perfil isquémico
- Signos de irritación peritoneal
- Fiebre con inmunosupresión conocida

## INSTRUCCIONES

1. Extrae los hallazgos clínicos de forma atómica: un concepto por infón.
2. Interpreta los valores numéricos con los `criterios_laboratorio`.
   "FC 115" se extrae como "Taquicardia", no como "FC 115".
3. No conviertas síntomas en diagnósticos. "Dolor torácico" es un
   hallazgo; "infarto" es una hipótesis que aquí no te corresponde emitir.
4. Ignora los hallazgos negados: "sin fiebre" no genera ningún infón.
5. Este protocolo no declara `modelo_bayesiano` a propósito: el triaje
   general no estima la probabilidad de ninguna enfermedad concreta.
