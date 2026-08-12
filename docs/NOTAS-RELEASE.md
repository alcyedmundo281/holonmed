# HolonMed v0.2.1

Corrige un fallo que impedía instalar el paquete y unifica el versionado.

## Correcciones

- **`pip install -e .` fallaba.** `pyproject.toml` declaraba `readme` con una
  ruta fuera del directorio del paquete, y setuptools lo rechaza con
  `DistutilsOptionError`. Cualquiera que siguiera las instrucciones del
  README se estrellaba en el primer comando. Lo detectó la CI, que ejercita
  esa ruta de instalación; en local se venía instalando por
  `requirements.txt`, que no pasa por el backend de construcción.

- **La versión estaba en cuatro sitios con tres valores distintos.** Ahora
  hay una sola fuente por lado: `holonmed/__init__.py` en el backend, que
  `pyproject.toml` lee como versión dinámica y la API expone en su OpenAPI;
  y `package.json` en el frontend, que Vite inyecta en la interfaz.

## Sin cambios funcionales

El comportamiento del validador, el motor bayesiano y el grafo es idéntico
al de v0.2.0. Los 79 tests pasan sin modificaciones.

---

## Qué es HolonMed

Convierte narrativa clínica libre en hallazgos estructurados y auditados.
Un modelo de lenguaje local propone; un validador de cuatro capas decide
cuáles son ciertos:

1. **Skill-hints** — códigos ya verificados por un humano en el protocolo.
2. **Recuperación** — FTS5 con BM25 acota el vocabulario; puntuado difuso
   ordena.
3. **Re-ranking** — el modelo audita los candidatos y puede responder
   *ninguno*.
4. **Auditoría lógica** — comparación numérica explícita contra los puntos
   de corte del protocolo.

El veredicto tiene tres estados: **validado**, **en alerta** y
**descartado**. Los descartes se muestran con su motivo, para que el
comportamiento del validador sea auditable en lugar de silencioso.

### Lo que distingue el enfoque

- **Guardas de colisión** que ni el LLM puede saltarse, para pares que un
  motor de similitud confunde y un clínico no: hiperlipasemia frente a
  hiperlipemia, amilasa frente a lipasa, hipo- frente a hiper-.
- **Inferencia bayesiana con traza completa**: no una probabilidad opaca,
  sino de dónde salió la previa, qué factor de riesgo la movió y qué
  likelihood ratio aportó cada hallazgo. Sólo la evidencia validada cuenta.
- **Grafo clínico con cierre transitivo parcial**: buscar por «alteración
  enzimática» encuentra pacientes cuyas notas sólo dicen «lipasa elevada».
- **Conocimiento declarativo**: los protocolos son Markdown con JSON-LD
  embebido. Añadir un dominio clínico no requiere tocar el código.

### Funciona recién clonado

Sin servidor de base de datos, sin descargas de terminología y sin trámites
de licencia. Incluye un vocabulario semilla de 111 conceptos clínicos en
español con sus sinónimos, que es contenido propio del proyecto.

Sólo hacen falta Python 3.10+, Node 20+ y Ollama con un par de modelos.

### Privacidad

Todo el procesamiento es local: Ollama para el razonamiento y SQLite
embebido para los datos. Ninguna narrativa clínica sale de la máquina.

### Licencias de las dependencias

Todas permisivas o de dominio público. Se evitó deliberadamente ArangoDB,
que desde su versión 3.12 usa BUSL-1.1 y cuya Community Edition prohíbe el
uso comercial. SNOMED CT está soportado por código, pero la terminología no
se distribuye: la aporta quien tenga la licencia de afiliado.

## Advertencia

**No es un dispositivo médico.** No está certificado bajo el MDR ni por la
FDA, y ninguna de sus salidas sustituye el juicio de un profesional
sanitario. Las limitaciones conocidas están enumeradas sin adornos en
[DISCLAIMER.md](../DISCLAIMER.md); léelas antes de usarlo con datos reales.

## Estado

79 tests automatizados, centrados en las propiedades de seguridad clínica.

Lo que **no** hay todavía, y hace falta antes de cualquier uso asistencial:
validación del sistema contra un corpus de notas clínicas anotado por
profesionales.
