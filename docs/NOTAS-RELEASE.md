# HolonMed v0.3.0

Primera versión ejecutada con modelos de lenguaje reales, y la primera que
distingue de dónde viene cada dato clínico.

Hasta v0.2.1 el pipeline sólo se había probado con dobles. Ponerlo a correr
con `gemma-4-E4B` y `dolphin-llama3-8b` reveló fallos que ningún test podía
anticipar, y arreglarlos llevó los hallazgos validados de 4/9 a 9/10 sobre
la misma nota de prueba.

## Actores del entorno clínico

Cada registro declara ahora qué proceso lo produjo: `consulta`,
`laboratorio`, `farmacia`, `enfermeria` o `imagen`, más el actor que lo
asertó. El historial se filtra por origen y la interfaz muestra el
responsable en cada entrada.

Esto recupera un concepto que existía en el sistema original y se había
perdido. Al reimplantarlo apareció una pérdida de datos silenciosa:

> **Las recetas no se guardaban en ninguna parte.** Se generaba el PDF y el
> fármaco prescrito desaparecía del registro, lo que rompe la conciliación
> de la medicación en la visita siguiente. Ahora una receta crea un tic de
> origen `farmacia` y queda en la historia con su contenido estructurado.

`actor` es informativo por ahora, porque no hay autenticación. Existe desde
esta versión a propósito: añadirla después obligaría a retro-asignar
autoría sobre registros clínicos ya escritos, que es justo lo que un
sistema con trazabilidad no puede permitirse.

## Protocolos declarativos y verificables

Los protocolos clínicos declaran su conocimiento en frontmatter YAML en vez
de bloques JSON embebidos en la prosa. Antes había que rascarlos con
expresiones regulares, y un error de sintaxis producía un protocolo
silenciosamente vacío: sin códigos, sin cortes y sin modelo bayesiano, pero
cargado y en uso.

```bash
holonmed skills --validar
```

Comprueba cada protocolo contra el vocabulario cargado. Nada más existir
encontró que dos hints no resolvían a ningún concepto, así que sus infones
salían sin linaje ni mapeo a CIE-10 — es decir, **no facturables** — sin
ningún error visible.

También llega `ambito_grafo`, que relaciona cada protocolo con ramas del
grafo y permite la consulta inversa: qué protocolos aplican a un paciente
según los hallazgos que ya tiene.

## Correcciones de la primera ejecución real

- **El auditor rechazaba todo hallazgo cualitativo.** Su prompt estaba
  escrito alrededor de valores numéricos, así que ante «vómitos repetidos»
  no encontraba cifra y concluía que no había evidencia. Ningún síntoma
  llegaba a validado ni alimentaba la inferencia.
- **Los factores de riesgo de la nota actual se ignoraban.** El motor
  bayesiano sólo miraba la ficha y el historial, de modo que en una primera
  consulta la probabilidad previa era siempre la prevalencia poblacional.
- **El emparejamiento de factores es literal**, y el lenguaje clínico real
  no usa las palabras del protocolo: «bebedor de riesgo» no contiene
  «alcohol». Se añadieron variantes y un test que lo documenta.
- **La CLI reventaba** al imprimir la inferencia en la consola de Windows.
- El contexto de las consultas generales llegaba vacío al modelo por un
  campo renombrado que quedó sin actualizar.

## Compatibilidad

- Las bases de datos existentes se migran solas al arrancar.
- Los protocolos con el formato JSON antiguo siguen funcionando; se
  traducen al vuelo y se registra un aviso.
- La versión vive en un único sitio por lado —`holonmed/__init__.py` y
  `package.json`— en vez de repetida en cuatro archivos con tres valores
  distintos, como estaba.

## Estado

98 tests automatizados, centrados en las propiedades de seguridad clínica.
Vocabulario semilla de 114 conceptos.

**Sigue sin validar.** Los veredictos han mejorado mucho, pero los
razonamientos que los acompañan no son fiables: el auditor llegó a inventar
un punto de corte que el protocolo declara explícitamente. En un sistema
cuyo argumento es la trazabilidad, eso pesa tanto como el acierto. Ver
[docs/VALIDACION.md](../docs/VALIDACION.md), que registra sin adornos lo
que funciona y lo que no.

Lo que hace falta antes de cualquier uso asistencial sigue siendo lo mismo:
validación contra un corpus de notas clínicas anotado por profesionales.

## Advertencia

**No es un dispositivo médico.** No está certificado bajo el MDR ni por la
FDA, y ninguna de sus salidas sustituye el juicio de un profesional
sanitario. Las limitaciones conocidas están en
[DISCLAIMER.md](../DISCLAIMER.md); léelas antes de usarlo con datos reales.
