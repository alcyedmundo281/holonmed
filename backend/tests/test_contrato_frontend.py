"""El contrato con el frontend: que `types.ts` diga lo que el backend manda.

`frontend/src/lib/types.ts` abre diciendo «espejo de los modelos de
models.py; si cambias uno, cambia el otro». Era una promesa que sólo
vivía en un comentario, y se rompió: entre la descomposición de Φ en tres
factores y la persistencia de la competencia, el archivo se quedó sin
nueve campos de `Acoplamiento` y sin siete de `ResultadoTic` sin que nada
protestara. Un tipo que promete menos de lo que llega no rompe la
compilación —TypeScript sólo se queja de lo que falta cuando alguien lo
usa— así que la deriva es invisible hasta que un dato no se muestra.

LO QUE SE COMPARA ES EL JSON, NO LA CLASE
-----------------------------------------
Y ésa es la otra mitad. En los modelos hay valores derivados —`duda`,
`phi_legible`, `InferenciaBayesiana.veredicto`— declarados como
`@property`, de modo que Pydantic **no los serializa**. Declararlos en
`types.ts` sería una promesa que el servidor no cumple y que TypeScript
dejaría pasar hasta que algo leyera `undefined` en pantalla. Por eso la
comparación es en los dos sentidos: lo que falta y lo que sobra.

El test se salta si no hay frontend en el árbol: el backend se puede
sacar solo.
"""

import dataclasses
import re
from pathlib import Path

import pytest

from holonmed import models as m

TYPES_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "types.ts"

pytestmark = pytest.mark.skipif(
    not TYPES_TS.exists(), reason="no hay frontend en este árbol"
)

# Qué interfaz de TypeScript refleja qué modelo del backend. Se listan a
# mano y no por reflexión: que un modelo nuevo no aparezca aquí es una
# decisión que alguien tiene que tomar —no todo lo que existe viaja al
# navegador— y una lista explícita obliga a tomarla.
MODELOS = {
    "Infon": m.Infon,
    "InferenciaBayesiana": m.InferenciaBayesiana,
    "ComponenteAcoplamiento": m.ComponenteAcoplamiento,
    "Acoplamiento": m.Acoplamiento,
    "CandidataAbductiva": m.CandidataAbductiva,
    "Veto": m.Veto,
    "VeredictoDeclarado": m.VeredictoDeclarado,
    "ReaperturaDeIndagacion": m.ReaperturaDeIndagacion,
    "ResultadoTic": m.ResultadoTic,
}

# Los enums que el frontend reproduce como uniones de literales.
ENUMS = {
    "EstadoInfon": m.EstadoInfon,
    "Polaridad": m.Polaridad,
    "OrigenTic": m.OrigenTic,
    "EstadoDimension": m.EstadoDimension,
    "VeredictoSemiotico": m.VeredictoSemiotico,
    "CausaDeLaDuda": m.CausaDeLaDuda,
    "TrayectoriaDeLaCreencia": m.TrayectoriaDeLaCreencia,
}


def _sin_comentarios(texto: str) -> str:
    """Los comentarios llevan nombres de campo dentro y falsearían la lectura."""
    return re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", texto, flags=re.S))


@pytest.fixture(scope="module")
def fuente() -> str:
    return _sin_comentarios(TYPES_TS.read_text(encoding="utf-8"))


def campos_declarados(fuente: str, interfaz: str) -> set[str] | None:
    bloque = re.search(rf"export interface {interfaz} \{{(.*?)\n\}}", fuente, re.S)
    if bloque is None:
        return None
    return {c.group(1) for c in re.finditer(r"^\s*(\w+)\??:", bloque.group(1), re.M)}


def literales_declarados(fuente: str, alias: str) -> set[str] | None:
    bloque = re.search(rf"export type {alias} =\s*(.*?);", fuente, re.S)
    if bloque is None:
        return None
    return set(re.findall(r"'([^']+)'", bloque.group(1)))


@pytest.mark.parametrize("interfaz", sorted(MODELOS))
def test_la_interfaz_declara_exactamente_los_campos_que_viajan(fuente, interfaz):
    """Ni menos —un dato que no se muestra— ni más —un `undefined` en pantalla."""
    declarados = campos_declarados(fuente, interfaz)
    assert declarados is not None, f"`{interfaz}` no existe en types.ts"

    # `model_fields` y no `dir()`: las `@property` no se serializan, así
    # que declararlas en TypeScript prometería algo que no llega.
    del_backend = set(MODELOS[interfaz].model_fields)

    assert declarados == del_backend, (
        f"{interfaz}: faltan {sorted(del_backend - declarados)}, "
        f"sobran {sorted(declarados - del_backend)}"
    )


@pytest.mark.parametrize("alias", sorted(ENUMS))
def test_las_uniones_de_literales_cubren_el_enum(fuente, alias):
    """Un valor de enum sin literal deja al frontend con un caso sin ramas."""
    declarados = literales_declarados(fuente, alias)
    assert declarados is not None, f"`{alias}` no existe en types.ts"
    assert declarados == {e.value for e in ENUMS[alias]}


def test_la_clasificacion_viaja_con_sus_campos_y_sin_sus_propiedades(fuente):
    """`ResultadoClasificacion` es un dataclass, no un modelo Pydantic.

    Va en `ResultadoTic.clasificacion`, tipado como `Any`, y Pydantic lo
    serializa por sus campos declarados. `satisfechos`, `cumple`,
    `resumen` y `vacios` son propiedades y se quedan en el servidor.
    """
    from holonmed.core.clasificacion import CriterioEvaluado, ResultadoClasificacion

    for interfaz, cls in (
        ("ResultadoClasificacion", ResultadoClasificacion),
        ("CriterioEvaluado", CriterioEvaluado),
    ):
        declarados = campos_declarados(fuente, interfaz)
        assert declarados is not None, f"`{interfaz}` no existe en types.ts"
        assert declarados == {f.name for f in dataclasses.fields(cls)}


def test_lo_que_no_se_serializa_no_se_promete(fuente):
    """El caso concreto que motiva la comparación en los dos sentidos.

    `duda` y `phi_legible` son las dos propiedades que más tienta
    declarar, porque son justo lo que un panel querría pintar. No
    llegan: el servidor las consume y publica `reapertura`, que sí es un
    campo. Prometerlas daría `undefined` sin que nada avisara.
    """
    declarados = campos_declarados(fuente, "Acoplamiento")
    assert "duda" not in declarados
    assert "phi_legible" not in declarados
    assert campos_declarados(fuente, "ReaperturaDeIndagacion") is not None
