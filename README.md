# HolonMed

Sistema de apoyo a la decisión clínica que convierte narrativa médica libre
en hallazgos estructurados, normalizados contra SNOMED CT y **auditados
antes de entrar en la historia del paciente**.

Todo el procesamiento ocurre en local mediante [Ollama](https://ollama.com).
Ninguna narrativa clínica sale de la máquina.

> **No es un dispositivo médico.** Ninguna salida de este sistema sustituye
> el juicio de un profesional sanitario. Lee [DISCLAIMER.md](DISCLAIMER.md)
> antes de usarlo con datos reales.

---

## El problema

Un modelo de lenguaje aplicado a texto clínico produce output plausible.
Plausible no es lo mismo que correcto, y en medicina la diferencia importa:

- Lee «Calcio 6.8», reconoce el concepto *Hipocalcemia* y lo afirma — sin
  haber comparado nunca 6.8 contra el punto de corte.
- Confunde **hiperlipasemia** (una enzima pancreática) con **hiperlipemia**
  (grasas en sangre). Dos caracteres de diferencia, dos cuadros distintos.
- Sustituye un síntoma por un diagnóstico: «dolor epigástrico» entra en la
  historia como «pancreatitis».

Un buscador difuso no detecta nada de esto, porque las cadenas se parecen.
Un LLM sin restricciones tampoco, porque su trabajo es sonar coherente.

## El enfoque

Cada hallazgo pasa por tres capas antes de considerarse cierto, y en cada
una puede ser rechazado:

| Capa | Pregunta | Mecanismo |
|------|----------|-----------|
| **0 — Skill-hints** | ¿Lo codificó ya un humano? | Diccionario término→SNOMED ID del protocolo activo |
| **1 — Recuperación** | ¿Existe el concepto? | Búsqueda difusa (rapidfuzz) o BM25 sobre SNOMED CT |
| **2 — Re-ranking** | ¿Es *este* concepto? | El LLM audita candidatos y **puede responder "ninguno"** |
| **3 — Auditoría lógica** | ¿Lo sostiene la evidencia? | Comparación numérica explícita contra el protocolo |

El resultado no es un booleano sino un veredicto de tres estados:

- **VALIDADO** — concepto confirmado y evidencia que lo sostiene. Entra en
  la historia y cuenta como prueba.
- **ALERTA** — el concepto existe, pero la auditoría no pudo confirmarlo.
  Se muestra marcado para revisión humana. No cuenta como prueba.
- **RUIDO** — descartado. **Se muestra igualmente**, con el motivo.

Esa última decisión es deliberada: un sistema que oculta lo que rechaza no
se puede auditar. Si el validador empieza a descartar de más, quieres
verlo.

### Guardas de colisión

Hay pares de conceptos que un motor de similitud confunde y un clínico
jamás. Están codificados como bloqueos duros que **ni siquiera el LLM puede
saltarse** ([`core/snomed.py`](backend/holonmed/core/snomed.py)):

```
amilasa   ⊗ lipasa        dos enzimas distintas
lipasemia ⊗ lipemia       enzima vs. lípidos
natremia  ⊗ potasemia     sodio vs. potasio
hipo…     ⊗ hiper…        dirección del desvío invertida
```

### Inferencia explicable

Sobre los hallazgos validados corre un motor bayesiano clásico:

```
odds_posterior = odds_previo × Π(LR de cada hallazgo validado)
```

Lo que lo hace útil no es el número final sino la traza: de dónde salió la
probabilidad previa, qué factor de riesgo la movió y qué hallazgo aportó
cada likelihood ratio. Un clínico puede recorrer el razonamiento y
discrepar de un paso concreto.

**Sólo la evidencia validada actualiza la probabilidad.** Un hallazgo en
alerta se ve en pantalla pero no mueve la aguja.

---

## Arranque rápido

### Requisitos

- Python 3.10+ y Node 20+
- [Ollama](https://ollama.com) con al menos un modelo descargado
- Licencia de afiliado de SNOMED CT (ver más abajo)
- ArangoDB — opcional; sin él, el sistema funciona pero no persiste nada

### Instalación

```bash
git clone https://github.com/alcyedmundo281/holonmed.git
cd holonmed
cp .env.example .env
```

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

```bash
ollama pull gemma2:9b && ollama pull llama3
```

```bash
docker compose up -d
```

### SNOMED CT

La terminología **no está en este repositorio** y no puede estarlo: es
propiedad de SNOMED International y requiere licencia de afiliado,
gratuita en los países miembros.

1. Comprueba si tu país es miembro en [snomed.org](https://www.snomed.org/member-countries)
2. Solicita la licencia a través de tu centro nacional
3. Descarga la *Spanish Edition* (basta el **Snapshot**)
4. Descomprime los `.txt` en `backend/data/snomed/`

```bash
cd backend && python scripts/setup_snomed.py --verificar
```

```bash
python scripts/setup_snomed.py --construir-cache
```

La primera ingesta tarda varios minutos; después el arranque es instantáneo
gracias al cache binario.

### Comprobar el entorno

```bash
cd backend && .venv/bin/holonmed check
```

Dice exactamente qué falta y con qué comando se arregla.

### Ejecutar

```bash
cd backend && .venv/bin/holonmed serve --reload
```

```bash
cd frontend && npm install && npm run dev
```

La interfaz queda en http://localhost:5173 y la documentación interactiva
de la API en http://localhost:8000/docs.

### Probar sin interfaz

```bash
holonmed tic "Varón 45a, dolor epigástrico en cinturón. Amilasa 1200, lipasa 890, calcio 6.8"
```

---

## Arquitectura

```
narrativa clínica
      │
      ▼
┌─────────────┐   ¿qué protocolo aplica?
│   TRIAJE    │   modelo rápido, conjunto cerrado de opciones
└─────────────┘
      │
      ▼
┌─────────────┐   hallazgos atómicos en bruto
│ EXTRACCIÓN  │   guiada por el vocabulario del protocolo
└─────────────┘
      │
      ▼
┌─────────────┐   hints → recuperación → re-ranking → auditoría
│ VALIDACIÓN  │   VALIDADO / ALERTA / RUIDO
└─────────────┘
      │
      ▼
┌─────────────┐   sólo con la evidencia validada
│   BAYES     │   probabilidad + traza completa
└─────────────┘
      │
      ▼
   ResultadoTic
```

```
backend/holonmed/
├── core/
│   ├── snomed.py      validación ontológica y guardas de colisión
│   ├── verifier.py    auditoría lógica contra criterios de laboratorio
│   ├── bayes.py       inferencia abductiva explicable
│   ├── skills.py      protocolos clínicos y extracción de hints
│   └── pipeline.py    orquestación del ciclo completo
├── llm/client.py      cliente Ollama async con parseo defensivo
├── db/arango.py       persistencia (opcional)
├── api/               FastAPI
└── services/          recetas PDF, agenda, laboratorio
```

Detalles en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

### Vocabulario

El dominio impone los nombres, y merece la pena entenderlos:

- **Infón** — el átomo de verdad. Un hallazgo clínico único, normalizado y
  auditado, con su procedencia textual.
- **Holón** — la historia clínica como organismo que crece absorbiendo
  infones, no como formulario que se rellena.
- **Tic** — un ciclo completo de procesamiento. Cada consulta es un tic que
  hace crecer el holón.

---

## Protocolos clínicos (*skills*)

Un protocolo es un Markdown con JSON-LD embebido. El texto instruye al
modelo; el JSON-LD lo consume el código directamente:

```json
{
  "name": "Pancreatitis aguda",
  "modelo_bayesiano": {
    "probabilidad_base": 0.05,
    "factores_riesgo_a_priori": { "alcoholismo": 2.8, "litiasis": 3.2 }
  },
  "criterios_laboratorio": {
    "reglas": [
      { "parametro": "Calcio sérico", "corte_inferior": 8.5,
        "termino_si_bajo": "Hipocalcemia", "snomed_id": "5291005" }
    ]
  },
  "signDetected": [
    { "name": "Hiperlipasemia (>3x)", "snomed_id": "10443000", "bayes_lr": 24.0 }
  ]
}
```

De ahí salen los skill-hints, los cortes de laboratorio y los likelihood
ratios. Añadir un protocolo es añadir un archivo: no se toca el código.

Guía completa en [docs/SKILLS.md](docs/SKILLS.md).

---

## Desarrollo

```bash
cd backend && pytest -q && ruff check .
```

Los tests no requieren Ollama, SNOMED ni ArangoDB: el pipeline se ejercita
con dobles de prueba. Cubren sobre todo las propiedades de seguridad —
que la evidencia no validada no cuente, que las colisiones se bloqueen, que
un LR mal configurado no produzca certeza del 100 %.

## Privacidad y seguridad

- **Procesamiento local.** Ollama corre en tu máquina. No hay llamadas a
  APIs de terceros con datos de paciente.
- **Sin credenciales en el repositorio.** El `.gitignore` bloquea patrones
  de secretos y la CI falla si alguno se cuela.
- **Sin datos de paciente en el repositorio.** Los ficticios de
  `scripts/seed_demo.py` son inventados.
- Antes de usar esto con pacientes reales, revisa el RGPD/LOPD o la
  normativa que te aplique. Que el procesamiento sea local ayuda, pero no
  te exime de nada.

## Origen

Fusión de dos proyectos previos: **HolonMed Core** aportó el validador de
tres capas y el motor bayesiano; **Universal InfonMed** aportó la API, la
persistencia, la interfaz y la generación de documentos.

## Licencia

[AGPL-3.0](LICENSE). Si despliegas una versión modificada como servicio en
red, debes publicar el código fuente de esa versión.

SNOMED CT tiene su propia licencia, independiente de esta. El código para
consumirla es libre; la terminología no se redistribuye aquí.
