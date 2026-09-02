# HolonMed — contrato de ingeniería y seguridad

## Alcance y límites

HolonMed convierte narrativa clínica libre en hallazgos codificados contra un vocabulario
controlado, los audita antes de dejarlos entrar en la historia del paciente, y calcula una
probabilidad a partir de un protocolo declarado mostrando el razonamiento entero. Todo el
procesamiento ocurre en local.

HolonMed **no emite diagnósticos ni indicaciones terapéuticas dirigidas al paciente**. Presenta
información y su procedencia para que un profesional la evalúe; la decisión clínica es siempre
humana. Cualquier cambio que acerque el sistema a emitir una conclusión directiva exige revisar
antes su clasificación regulatoria (ARCSA en Ecuador; los criterios de la FDA sobre apoyo a la
decisión clínica sirven de referencia sobre dónde está la línea). El alcance operativo está en
[DISCLAIMER.md](DISCLAIMER.md), y contradecirlo en el código es un fallo, no una mejora.

## Reglas no negociables

1. **Nada de datos identificables en el repositorio.** Ni en el código, ni en los archivos de
   configuración, ni en los registros, ni en las descripciones de pull request, ni en los mensajes
   de commit. Sin nombres, cédulas, historias clínicas, imágenes ni fragmentos de expediente. Los
   casos de prueba son sintéticos.
2. **Nada de credenciales en el repositorio.** Ni tokens, ni claves, ni archivos OAuth, ni rutas
   locales de una máquina concreta. Todo llega por variable de entorno o gestor de secretos, y los
   errores nunca imprimen el valor de un secreto. El trabajo de esta regla lo hacen
   [.gitignore](.gitignore) y el job `secretos` de CI; ninguno de los dos se relaja.
3. **Fallo cerrado.** Ante un dato ausente, una fuente que no resuelve o una configuración
   incompleta, el sistema se detiene y explica por qué. Nunca completa, aproxima ni infiere para
   poder continuar. Ya está dicho en `docs/ARQUITECTURA.md` como principio rector: *prefiere no
   decir nada antes que decir algo falso*. Aquí es además una condición de aceptación.
4. **Aprobación humana nombrada** antes de cualquier acción que salga del sistema: escribir en un
   expediente, enviar una notificación, publicar un resultado. La cadena que redacta no debe tener
   ruta hacia la ejecución.
5. **El determinismo vive en el código.** Esquemas, tablas de política y condiciones de rechazo se
   implementan y se prueban; no se confían a instrucciones en un prompt. Los umbrales del validador
   son configuración con valor por defecto explícito, no números escritos en una plantilla.

## Gates de calidad

Ninguna rama se fusiona sin que las cuatro pasen, en CI y en local. Desde `backend/`:

```bash
ruff check . && ruff format --check . && mypy && pytest -q
```

Corren sobre `backend/holonmed` y `backend/tests`. `guiones/` son exploratorios y quedan fuera a
propósito: si un guion se vuelve parte del sistema, se muda a `backend/` y entra bajo las cuatro.

`mypy` corre con su configuración por defecto más `warn_unreachable`, `warn_unused_ignores` y
`warn_redundant_casts` (ver `backend/pyproject.toml`). No exige anotar el mundo; caza la clase de
fallo que este dominio no puede permitirse —un `None` que se multiplica, un atributo que el tipo
no garantiza—. Endurecerlo (`--strict` sobre `core/`) es deuda declarada, no ruido.

CI añade tres comprobaciones que no son de estilo sino de promesa, y valen tanto como las cuatro:
que el sistema arranca sin nada instalado, que ningún protocolo apunta a un concepto inexistente, y
que no se ha colado una credencial.

## Arquitectura obligatoria

- **Núcleo determinista** — `backend/holonmed/core/`: funciones tipadas, sin red y sin estado
  global, con pruebas. Es donde vive la lógica y donde se verifica.
- **Servicio en el borde** — `backend/holonmed/api/`: envuelve el núcleo y aporta identidad,
  autorización, auditoría y persistencia. No reimplementa lógica.
- **El LLM habla con el servicio, nunca con los archivos.** Hay una sola puerta,
  `backend/holonmed/llm/client.py`: async, con timeouts explícitos, temperatura fijada por
  configuración y parseo defensivo que devuelve `{}` en vez de una suposición. Añadir un segundo
  camino al modelo es romper el contrato.
- **Auditoría append-only** de quién hizo y quién vio qué, con marca de tiempo. Incluye lecturas.
- **Canal de razonamiento separado del canal de acción.** El texto libre de un expediente es
  entrada no confiable: una frase dentro de una nota puede leerse como instrucción. Ese contenido
  nunca alcanza un contexto capaz de ejecutar acciones.
- **Sustrato compartido neutral**: el índice de fuentes (`medsemiotics-db`) y la capa de
  conocimiento no conocen a sus consumidores, para que sirvan igual a la clínica y a la docencia.

### Lo que todavía no es cierto

Este apartado existe para que el contrato no mienta. Son requisitos vigentes, sin implementar:

- **No hay tabla de auditoría append-only.** `tic` guarda el razonamiento entero y es trazable,
  pero nadie registra las *lecturas*, y ninguna tabla está protegida contra reescritura.
- **No hay tabla de política.** Las operaciones expuestas al modelo no se consultan contra una
  decisión declarada con su razón.
- **No hay aprobación humana nombrada.** `confirmar_cargo` es lo más cercano, y confirma un cargo,
  no una escritura en el expediente.

Cerrarlos es trabajo pendiente. Mientras tanto, ningún cambio puede alejarlos más.

## Cómo se trabaja

- Se desarrolla en una rama, nunca directo sobre `main`.
- Cada pull request explica por qué existe el cambio, no solo qué cambió, y espera CI en verde.
  Los mensajes de commit de este repositorio nombran la razón; sígalos.
- Un cambio que toca política, auditoría o manejo de datos de paciente se revisa aunque sea
  pequeño.
- Los umbrales del validador son parámetros de seguridad. Moverlos es un cambio revisable, con su
  justificación escrita, no un ajuste.

## Qué hacer ante la duda

Si falta información para completar una tarea correctamente, pregunte o deténgase. No invente un
valor por defecto razonable, no complete un dato clínico ausente, no asuma una identidad de
usuario. En este dominio, una respuesta segura y equivocada cuesta más que ninguna respuesta.
