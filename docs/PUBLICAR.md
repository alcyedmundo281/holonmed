# Publicar y obtener un DOI

> **Estado: hecho.** El repositorio es público y v0.2.0 está archivado en
> Zenodo con DOI de concepto
> [10.5281/zenodo.21881233](https://doi.org/10.5281/zenodo.21881233).
> Lo que sigue documenta el proceso para las versiones futuras.

## Antes de publicar

Repasa esta lista. Un repositorio público no se puede despublicar de
verdad: quedan forks, cachés y el índice de los buscadores.

- [x] `CITATION.cff` y `.zenodo.json` tienen los datos reales del autor
- [ ] No hay credenciales versionadas (la CI lo comprueba, pero míralo)
- [ ] No hay datos de paciente reales en `backend/data/holonmed.db`
- [ ] Ninguna terminología con licencia está versionada
- [ ] Has leído [DISCLAIMER.md](../DISCLAIMER.md) y estás de acuerdo con lo que afirma

Sobre el tercer punto: el `.gitignore` excluye `*.db`, pero si en algún
momento procesaste una nota real, esa nota está en tu base local. No la
subas ni la adjuntes a un issue.

## Publicar el repositorio

```bash
cd holonmed && gh repo create holonmed --public --source=. --push
```

## Obtener el DOI de Zenodo

Zenodo es un repositorio de datos del CERN. Acuña DOIs gratis y de forma
permanente.

Hay dos caminos. **v0.2.0 se publicó por el manual**, porque la integración
automática no llegó a listar el repositorio recién creado.

### Camino manual (el que se usó)

1. Crea el release en GitHub.
2. Descarga el `.zip` que genera automáticamente en la página del release.
3. En [zenodo.org/uploads/new](https://zenodo.org/uploads/new), súbelo y
   rellena los metadatos desde [.zenodo.json](../.zenodo.json).
4. En el campo *Digital Object Identifier*, marca **«No, I need one»**.
   Marcarlo al revés es el error fácil: le dice a Zenodo que no acuñe DOI.
5. Publica.

Nota sobre el orden: el `.zip` archivado de v0.2.0 no contiene su propio
DOI en `CITATION.cff`, porque el DOI no existe hasta publicar. Se añadió al
repositorio justo después, así que las versiones siguientes ya lo llevarán
dentro.

### Camino automático (para las próximas)

**1. Conecta tu cuenta.** Entra en [zenodo.org](https://zenodo.org) e
inicia sesión con GitHub. Ve a
[zenodo.org/account/settings/github](https://zenodo.org/account/settings/github/)
y activa el interruptor del repositorio `holonmed`. Si no aparece en la
lista, pulsa **«Sync now»**: Zenodo cachea los repositorios y tarda en ver
los recién creados.

Hazlo **antes** de crear el release. Zenodo sólo archiva releases
publicados después de activar el interruptor: si lo haces al revés, tienes
que crear otro release.

**2. Crea el release.**

```bash
gh release create v0.2.0 --title "HolonMed v0.2.0" --notes-file docs/NOTAS-RELEASE.md
```

**3. Espera unos minutos.** Zenodo recibe el aviso, archiva el código y
acuña el DOI. Aparecerá en *Settings → GitHub* junto al repositorio.

**4. Añade la insignia al README.** Zenodo da dos DOIs:

- El **DOI de concepto**, que apunta siempre a la última versión. Es el que
  va en el README y el que quieres que cite la gente.
- Un **DOI de versión** por cada release. Es el que se cita cuando importa
  reproducir exactamente esa versión.

```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
```

**5. Vuelca el DOI en `CITATION.cff`** añadiendo el campo `doi:` con el de
concepto. A partir de ahí, GitHub muestra la cita completa en el botón
*Cite this repository*.

## Qué esperar

El DOI acredita que el software existe, es tuyo y está archivado de forma
citable. Es suficiente para:

- Citarlo en un artículo, una tesis o un currículum
- Que otros lo citen de forma inequívoca
- Que el código quede archivado aunque GitHub desaparezca

Lo que un DOI **no** hace: no es revisión por pares, no valida el software
clínicamente y no es una certificación de nada. Si quieres respaldo
académico revisado, el siguiente paso es un artículo de software en una
revista que los publique — [JOSS](https://joss.theoj.org) es la referencia
habitual para software de investigación, y su revisión es pública y
razonablemente rápida.

Para JOSS harían falta dos cosas que hoy no están: un `paper.md` con la
declaración de necesidad, y evidencia de validación del sistema sobre un
conjunto de notas clínicas anotado. Lo segundo es el trabajo de verdad, y
es también lo que haría el proyecto defendible ante un comité de ética.

## Versionado

Cada release nuevo genera un DOI de versión y actualiza el de concepto.
Conviene que la versión de `CITATION.cff`, la de `.zenodo.json`, la de
`backend/pyproject.toml` y la etiqueta de git digan lo mismo.
