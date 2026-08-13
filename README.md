# HolonMed

[![DOI](https://zenodo.org/badge/1330400632.svg)](https://doi.org/10.5281/zenodo.21896525)
[![CI](https://github.com/alcyedmundo281/holonmed/actions/workflows/ci.yml/badge.svg)](https://github.com/alcyedmundo281/holonmed/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

Sistema de apoyo a la decisión clínica que convierte narrativa médica libre
en hallazgos estructurados, normalizados contra un vocabulario controlado y
**auditados antes de entrar en la historia del paciente**.

Todo el procesamiento ocurre en local: [Ollama](https://ollama.com) para el
razonamiento, SQLite embebido para los datos. Ninguna narrativa clínica sale
de la máquina.

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

Cada hallazgo pasa por cuatro capas antes de considerarse cierto, y en cada
una puede ser rechazado:

| Capa | Pregunta | Mecanismo |
|------|----------|-----------|
| **0 — Skill-hints** | ¿Lo codificó ya un humano? | Diccionario término→código del protocolo activo |
| **1 — Recuperación** | ¿Existe el concepto? | FTS5 con BM25 acota; puntuado difuso ordena |
| **2 — Re-ranking** | ¿Es *este* concepto? | El LLM audita candidatos y **puede responder "ninguno"** |
| **3 — Auditoría lógica** | ¿Lo sostiene la evidencia? | Comparación numérica explícita contra el protocolo |

El resultado no es un booleano sino un veredicto de tres estados:

- **VALIDADO** — concepto confirmado y evidencia que lo sostiene. Entra en
  la historia y cuenta como prueba.
- **ALERTA** — el concepto existe, pero la auditoría no pudo confirmarlo.
  Se muestra marcado para revisión humana. No cuenta como prueba.
- **RUIDO** — descartado. **Se muestra igualmente**, con el motivo.

Esa última decisión es deliberada: un sistema que oculta lo que rechaza no
se puede auditar. Si el validador empieza a descartar de más, quieres verlo.

### Guardas de colisión

Hay pares de conceptos que un motor de similitud confunde y un clínico
jamás. Están codificados como bloqueos duros que **ni siquiera el LLM puede
saltarse** ([`core/validator.py`](backend/holonmed/core/validator.py)):

```
amilasa   ⊗ lipasa        dos enzimas distintas
lipasemia ⊗ lipemia       enzima vs. lípidos
natremia  ⊗ potasemia     sodio vs. potasio
glucemia  ⊗ glucosuria    en sangre vs. en orina
hematuria ⊗ hematemesis   sangre en orina vs. en vómito
hipo…     ⊗ hiper…        dirección del desvío invertida
```

### Inferencia explicable

Sobre los hallazgos validados corre un motor bayesiano clásico:

```
odds_posterior = odds_previo × Π(LR de cada hallazgo validado)
```

Lo que lo hace útil no es el número final sino la traza: de dónde salió la
probabilidad previa, qué factor de riesgo la movió y qué hallazgo aportó
cada likelihood ratio. Un clínico puede recorrer el razonamiento y discrepar
de un paso concreto.

**Sólo la evidencia validada actualiza la probabilidad.** Un hallazgo en
alerta se ve en pantalla pero no mueve la aguja.

### El grafo clínico

El vocabulario no es una lista plana sino un grafo dirigido. Eso permite la
consulta que justifica toda la estructura:

```bash
curl 'localhost:8000/api/grafo/cohorte?codigo=HM:0730'
```

Devuelve los pacientes con **cualquier** alteración enzimática — aunque en
sus notas nadie escribiera esas palabras, sólo «lipasa elevada» o
«hiperamilasemia». El grafo deduce la relación.

Para que esa consulta sea barata, el cierre transitivo se materializa
únicamente para los conceptos que aparecen en datos clínicos reales.
Materializar un vocabulario completo serían decenas de millones de filas;
materializar lo que se usa son unos miles, y convierte la consulta en un
join indexado. Ver [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

---

## Arranque rápido

Sin descargas de terminología, sin servidor de base de datos y sin trámites
de licencia:

```bash
git clone https://github.com/alcyedmundo281/holonmed.git && cd holonmed
```

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

```bash
ollama pull gemma2:9b && ollama pull llama3
```

```bash
.venv/bin/holonmed check
```

`check` dice exactamente qué falta y con qué comando se arregla. Cuando
esté todo en verde:

```bash
.venv/bin/holonmed serve --reload
```

```bash
cd frontend && npm install && npm run dev
```

La interfaz queda en http://localhost:5173 y la documentación interactiva de
la API en http://localhost:8000/docs.

### Probar sin interfaz

```bash
holonmed tic "Varón 45a, dolor epigástrico en cinturón. Amilasa 1200, lipasa 890, calcio 6.8"
```

### Requisitos

- Python 3.10+ y Node 20+
- [Ollama](https://ollama.com) con los modelos configurados descargados

Eso es todo. La base de datos es un archivo SQLite que se crea sola, y el
vocabulario clínico base viene incluido.

---

## Vocabulario clínico

El repositorio incluye un **vocabulario semilla** de unos 110 conceptos
frecuentes en español, con sus sinónimos y su jerarquía. Es contenido propio
del proyecto, bajo la misma licencia que el código, y **no contiene códigos
de ninguna terminología con licencia**.

Sirve para que el validador funcione recién clonado: reconoce y normaliza lo
habitual, y rechaza lo que no reconoce. Sin vocabulario no habría validación
posible, y un validador que lo acepta todo es peor que no tener validador.

Reconoce sinónimos sin necesidad de LLM:

| Escribes | Normaliza a |
|----------|-------------|
| «lipasa elevada» | Hiperlipasemia |
| «calcio bajo» | Hipocalcemia |
| «falta de aire» | Disnea |
| «orina oscura» | Coluria |

### Importar una terminología completa

Para codificar de verdad — facturación, interoperabilidad, HCE — hace falta
una terminología estándar. El repositorio distribuye **el código que las
lee**, nunca los datos:

```bash
python scripts/importar_terminologia.py --rf2 /ruta/al/Snapshot/Terminology
```

**SNOMED CT** requiere licencia de afiliado, gratuita en los países
miembros. Comprueba el tuyo en
[snomed.org/member-countries](https://www.snomed.org/member-countries) y
solicítala a través del centro nacional. Obtenerla y cumplirla es
responsabilidad de quien la importa.

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
┌─────────────┐   hints → FTS5 → re-ranking → auditoría
│ VALIDACIÓN  │   VALIDADO / ALERTA / RUIDO
└─────────────┘
      │
      ▼
┌─────────────┐   sólo con la evidencia validada
│   BAYES     │   probabilidad + traza completa
└─────────────┘
      │
      ▼
   ResultadoTic  ──►  grafo del paciente
```

```
backend/holonmed/
├── core/
│   ├── terminology.py  índice FTS5 + carga de vocabularios
│   ├── validator.py    validación ontológica y guardas de colisión
│   ├── verifier.py     auditoría lógica contra criterios de laboratorio
│   ├── bayes.py        inferencia abductiva explicable
│   ├── skills.py       protocolos clínicos y extracción de hints
│   └── pipeline.py     orquestación del ciclo completo
├── db/
│   ├── schema.sql      esquema SQLite, incluido el grafo
│   └── store.py        repositorios y consultas de grafo
├── facturacion/
│   ├── propuesta.py    órdenes propuestas desde el plan (el médico firma)
│   ├── conciliacion.py orden ⊗ ejecución → cargo, y los descuadres
│   ├── registro.py     extracción según el protocolo de cada rol
│   └── exportacion.py  la cuenta en XML/JSON/CSV, con su trazabilidad
├── llm/client.py       cliente Ollama async con parseo defensivo
├── api/                FastAPI
└── services/           recetas PDF, agenda, laboratorio
```

### Vocabulario del dominio

El proyecto usa nombres deliberados, y merece la pena entenderlos:

- **Infón** — el átomo de verdad. Un hallazgo clínico único, normalizado y
  auditado, con su procedencia textual.
- **Holón** — la historia clínica como organismo que crece absorbiendo
  infones, no como formulario que se rellena.
- **Tic** — un ciclo completo de procesamiento. Cada consulta es un tic que
  hace crecer el holón.

---

## Protocolos clínicos (*skills*)

Un protocolo es un Markdown con frontmatter YAML. La prosa instruye al
modelo; el frontmatter lo consume el código directamente:

```yaml
---
condicion:
  nombre: Pancreatitis aguda
  codigos: { snomed: "197456007" }

modelo_bayesiano:
  probabilidad_base: 0.05
  factores_riesgo: { alcoholismo: 2.8, litiasis: 3.2 }

signos:
  - nombre: Hiperlipasemia (>3x)
    lr: 24.0
    lr_negativo: 0.15      # lo ausente también informa
    fuente: "Ann Intern Med 2010;152:342"

criterios_laboratorio:
  reglas:
    - parametro: Calcio sérico
      corte_inferior: 8.5
      termino_si_bajo: Hipocalcemia
---
```

De ahí salen los skill-hints, los cortes de laboratorio, los likelihood
ratios y los criterios de clasificación. Añadir un protocolo es añadir un
archivo: no se toca el código.

Hay un segundo tipo, `operativo`: los protocolos de rol —enfermería,
farmacia— declaran qué campos exige el registro de cada actor. No
interpretan una narrativa; estructuran lo que ese actor asienta y, sobre
todo, **señalan lo que falta** mientras todavía se puede corregir.

Guía completa en [docs/SKILLS.md](docs/SKILLS.md).

---

## Órdenes y facturación

La cadena no se puede saltar ningún eslabón:

```
plan de la nota ──► ORDEN ──► ejecución del actor ──► cargo
                      ↑                 ↑
                  autoriza       confirma que se hizo
```

Una orden no describe: **autoriza**. `cargo` referencia siempre una
`orden`, así que sin autorización no hay cargo — no porque se lo pidamos
a un modelo, sino porque no existe la fila.

El sistema lee el plan y **propone** órdenes; el médico firma con un
botón. Son dos endpoints a propósito, y entre ellos está la firma:

```
POST /api/facturacion/ordenes/proponer    devuelve borradores, no escribe
POST /api/facturacion/ordenes/autorizar   crea las órdenes reales
```

El borrador se edita antes de firmar. Lo que el plan no especifica sale
como hueco vacío, nunca relleno a ojo; y si el modelo devuelve una
categoría («Medicamento») donde debía ir el fármaco, la propuesta se marca
y no se corrige sola.

De la conciliación entre órdenes y ejecuciones sólo un resultado es de
facturación; los otros dos importan más:

| Situación | Qué significa |
|-----------|---------------|
| Orden sin ejecución | El paciente no recibió lo prescrito |
| Ejecución sin orden | Administración no autorizada |
| Orden + ejecución | Facturable |

Los tarifarios se cargan como un vocabulario más, con su `sistema` y su
fecha de vigencia, y la cuenta se exporta en XML, JSON o CSV con la orden
y la ejecución dentro de cada línea.

---

## Desarrollo

```bash
cd backend && pytest -q && ruff check .
```

Los tests no requieren Ollama ni ninguna terminología externa. Cubren sobre
todo las propiedades de seguridad: que la evidencia no validada no cuente,
que las colisiones se bloqueen, que un LR mal configurado no produzca
certeza del 100 %, que el grafo encuentre por ancestro y que un descarte no
muestre un término que el clínico nunca escribió.

## Privacidad y seguridad

- **Procesamiento local.** Ollama corre en tu máquina y la base es un
  archivo. No hay llamadas a terceros con datos de paciente.
- **Sin credenciales en el repositorio.** El `.gitignore` bloquea patrones
  de secretos y la CI falla si alguno se cuela.
- **Sin datos de paciente.** `*.db` está ignorado; los pacientes de
  `scripts/seed_demo.py` son inventados.
- Antes de usar esto con pacientes reales, revisa el RGPD/LOPD o la
  normativa que te aplique, y cifra el disco donde viva la base.

## Origen

Fusión de dos proyectos previos: **HolonMed Core** aportó el validador de
tres capas y el motor bayesiano; **Universal InfonMed** aportó la API, la
persistencia, la interfaz y la generación de documentos.

## Licencia

[AGPL-3.0](LICENSE). Si despliegas una versión modificada como servicio en
red, debes publicar el código fuente de esa versión.

Todas las dependencias son permisivas o de dominio público. Se evitó
deliberadamente ArangoDB, que desde su versión 3.12 usa BUSL-1.1 y cuya
Community Edition prohíbe el uso comercial; SQLite es de dominio público y
no impone ninguna condición aguas abajo.

## Autoría y contacto

Alcy Edmundo Torres Guerrero — [ORCID 0000-0002-9742-375X](https://orcid.org/0000-0002-9742-375X)

Para pull requests, propuestas de colaboración o dudas sobre el uso del
sistema: **alcy.torres@powersemiotics.com**

Las contribuciones son bienvenidas por la vía habitual: abre un issue para
discutir el cambio antes de invertir tiempo en él, sobre todo si toca los
umbrales del validador o las guardas de colisión, que son parámetros de
seguridad clínica.

## Citación

El software está archivado en Zenodo con DOI permanente:

> Torres Guerrero, A. E. (2026). *HolonMed: apoyo a la decisión clínica con
> validación ontológica y razonamiento bayesiano explicable* (v0.4.0).
> Zenodo. https://doi.org/10.5281/zenodo.21896525

```bibtex
@software{torres_guerrero_holonmed_2026,
  author    = {Torres Guerrero, Alcy Edmundo},
  title     = {HolonMed: apoyo a la decisión clínica con validación
               ontológica y razonamiento bayesiano explicable},
  year      = {2026},
  publisher = {Zenodo},
  version   = {v0.4.0},
  doi       = {10.5281/zenodo.21896525},
  url       = {https://doi.org/10.5281/zenodo.21896525}
}
```

Hay dos DOI y conviene distinguirlos:

| DOI | Qué identifica | Cuándo usarlo |
|-----|----------------|---------------|
| [`10.5281/zenodo.21896525`](https://doi.org/10.5281/zenodo.21896525) | Todas las versiones | Por defecto. Resuelve siempre a la última |
| [`10.5281/zenodo.21911667`](https://doi.org/10.5281/zenodo.21911667) | Sólo v0.4.0 | Cuando importe reproducir esta versión exacta |

GitHub también genera la cita automáticamente desde
[CITATION.cff](CITATION.cff) con el botón *Cite this repository*.
