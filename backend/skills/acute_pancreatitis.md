# SKILL: PROTOCOLO DE PANCREATITIS AGUDA (EVIDENCIA MBE)
ROL: Gastroenterólogo Experto (Basado en Evidencia).

BASE DE CONOCIMIENTO (JSON-LD Context):
{
    "@context": "https://schema.org",
    "@type": "MedicalCondition",
    "name": "Pancreatitis Aguda",
    "snomed_id": "197456007",
    "evidence_source": "GetTheDiagnosis.org / JAMA Rational Clinical Exam",
    
    "metadatos_inmunologicos": {
        "donde": ["Páncreas", "Epigastrio", "Retroperitoneo"],
        "como": ["Inflamación", "Necrosis", "Respuesta Sistémica"],
        "por_que": ["Alcoholismo", "Litiasis Biliar", "Hipertrigliceridemia"]
    },

    "modelo_bayesiano": {
        "probabilidad_base": 0.05, 
        "_nota_factores": "El emparejamiento es por subcadena literal, así que hay que declarar las variantes que un clínico escribe de verdad. 'bebedor de riesgo' no contiene 'alcohol'.",
        "factores_riesgo_a_priori": {
            "alcohol": 2.8,
            "alcoholismo": 2.8,
            "enolismo": 2.8,
            "bebedor": 2.8,
            "etilismo": 2.8,
            "litiasis": 3.2,
            "colelitiasis": 3.2,
            "coledocolitiasis": 3.2,
            "cálculos biliares": 3.2,
            "calculos biliares": 3.2,
            "hipertrigliceridemia": 2.2,
            "cpre": 2.5
        }
    },

    "criterios_laboratorio": {
        "instruccion": "Si encuentras valores numéricos, compáralos con estos rangos. Si están fuera, extrae el hallazgo clínico correspondiente.",
        "reglas": [
            {
                "parametro": "Amilasa",
                "corte_superior": 110,
                "multiplicador_pancreatitis": 3,
                "termino_si_alto": "Hiperamilasemia (>3x)",
                "snomed_id": "10427000"
            },
            {
                "parametro": "Lipasa",
                "corte_superior": 60,
                "multiplicador_pancreatitis": 3,
                "termino_si_alto": "Hiperlipasemia (>3x)",
                "snomed_id": "10443000"
            },
            {
                "parametro": "Leucocitos",
                "corte_superior": 11000,
                "termino_si_alto": "Leucocitosis",
                "snomed_id": "767002"
            },
            {
                "parametro": "Calcio sérico",
                "corte_inferior": 8.5,
                "termino_si_bajo": "Hipocalcemia",
                "snomed_id": "5291005"
            },
            {
                "parametro": "Hematocrito",
                "corte_superior": 44,
                "termino_si_alto": "Hemoconcentración",
                "snomed_id": "45643008"
            },
            {
                "parametro": "FC",
                "corte_superior": 100,
                "termino_si_alto": "Taquicardia",
                "snomed_id": "3424008"
            },
            {
                "parametro": "TA",
                "corte_inferior_sistolica": 100,
                "termino_si_bajo": "Hipotensión",
                "snomed_id": "45007003"
            }
        ]
    },

    "signDetected": [
        {
            "name": "Hiperlipasemia (>3x)",
            "snomed_id": "10443000",
            "bayes_lr": 26.6, 
            "description": "Evidencia Gold Standard. LR+ muy alto."
        },
        {
            "name": "Hiperamilasemia (>3x)",
            "snomed_id": "10427000",
            "bayes_lr": 12.5,
            "description": "Fuerte evidencia, pero menos específica que la lipasa."
        },
        {
            "name": "Dolor Epigástrico",
            "snomed_id": "79922009",
            "bayes_lr": 2.1,
            "description": "Sensible pero poco específico (LR bajo)."
        },
        {
            "name": "Vómitos",
            "snomed_id": "422400008",
            "bayes_lr": 1.6,
            "description": "Síntoma común, aporta poca certeza por sí solo."
        },
        {
            "name": "Rebote (Signo de Blumberg)",
            "snomed_id": "271956003",
            "bayes_lr": 2.2,
            "description": "Signo de irritación peritoneal."
        },
        {
            "name": "Signo de Cullen",
            "snomed_id": "45002005",
            "bayes_lr": 8.0,
            "description": "Raro pero específico para pancreatitis necrotizante/hemorrágica."
        }
    ]
}

INSTRUCCIONES CLÍNICAS:
1. Analiza los signos vitales y texto libre.
2. IMPORTANTE: Revisa los valores numéricos. Si hay valores de laboratorio o vitales, aplica las reglas de 'criterios_laboratorio'.
   - Ejemplo: Si ves "Calcio 7.5", deduce e informa "Hipocalcemia".
   - Ejemplo: Si ves "Leucocitos 18.000", deduce e informa "Leucocitosis".
   - Prioriza los términos con (>3x) para hallazgos enzimáticos masivos.
