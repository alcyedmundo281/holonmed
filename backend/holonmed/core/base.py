"""La base de datos definida: la fase 1 de Weed, que el sistema no tenía.

EL ARGUMENTO, QUE NO ES DE ORDEN SINO DE VALIDEZ
------------------------------------------------
La lista de problemas es un artefacto de la base. Si sólo se sabe el nombre
del paciente no tiene problemas; si además se sabe su presión puede tener
uno; si además se le explora, dos. De modo que sin definir qué se averigua
siempre, la lista de problemas depende de dónde se formó quien preguntó, de
cuántos ingresos hubo anoche y de qué le interesa al que pasa visita.

Weed lo midió en una sala de urgencias: con un cuestionario de 32 preguntas
y personal paramédico, los médicos se estaban dejando **5.2 problemas por
paciente**. No por ignorancia — por no tener definido el mínimo.

Que el mínimo sea arbitrario no es objeción. Un campo de fútbol también lo
es, y sin la línea no hay forma de saber si alguien anotó.

QUIÉN LA OBTIENE, QUE NO ES EL MÉDICO
--------------------------------------
Cada ítem declara `quien` lo obtiene, y es deliberado que la mayoría no sea
el médico. La solución de Weed para esta fase es cuestionario con lógica de
ramificación, personal de enfermería entrenado y verificado, y el propio
paciente — que es quien más variables conoce de su propio cuadro. Un
formulario libre para que el médico teclee sería automatizar el caos.

POR QUÉ ESTO ES CÓDIGO Y NO UN PROMPT
--------------------------------------
El contrato lo exige: esquemas y condiciones de rechazo se implementan y se
prueban, no se confían a instrucciones en un prompt. Una base que un modelo
puede decidir dar por cumplida no es una base, es una sugerencia.

FALLO CERRADO
-------------
Una base incompleta **se detiene y dice qué falta**. No se completa con un
valor por defecto razonable, y no se da por buena porque «lo importante ya
está»: quién decide qué es lo importante es justo lo que la base existe
para no dejar al criterio del momento.

El caso más fino es la edad. Si la base condiciona ítems por edad y la edad
no se conoce, el sistema **no puede saber** si esos ítems aplican. Saltarlos
afirmaría que no aplican; exigirlos afirmaría que sí. Ninguna de las dos es
cierta, así que se detiene diciendo que falta la edad.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


class Quien(str, Enum):
    """Quién obtiene un ítem de la base.

    No es una etiqueta descriptiva: es la asignación de trabajo, y decide
    qué interfaz tiene que existir para cada ítem.
    """

    PACIENTE = "paciente"
    ENFERMERIA = "enfermeria"
    MEDICO = "medico"
    LABORATORIO = "laboratorio"


class Alcance(str, Enum):
    """Hasta dónde llega esta base.

    La base mínima se declara APARTE y con su nombre, no como una excepción
    informal a la comprehensiva. Weed la admite explícitamente —para un
    clavo en el pie no se hace la historia entera— pero la quiere declarada:
    en cuanto la excepción es informal, se convierte en la regla los días
    con mucha carga.
    """

    COMPREHENSIVA = "comprehensiva"
    EPISODICA = "episodica"


@dataclass(frozen=True)
class ItemBase:
    """Una cosa que la base exige averiguar, y de quién.

    `desde_edad` y `hasta_edad` son inclusivos por el extremo que declaran.
    Un ítem sin ninguno de los dos aplica a todo el mundo.
    """

    nombre: str
    quien: Quien
    codigo: str | None = None
    desde_edad: int | None = None
    hasta_edad: int | None = None

    @property
    def depende_de_la_edad(self) -> bool:
        return self.desde_edad is not None or self.hasta_edad is not None

    def aplica_a(self, edad: int) -> bool:
        if self.desde_edad is not None and edad < self.desde_edad:
            return False
        if self.hasta_edad is not None and edad > self.hasta_edad:
            return False
        return True


@dataclass(frozen=True)
class SeccionBase:
    """Un bloque de la base. Agrupa para leer, no cambia la exigencia."""

    nombre: str
    items: tuple[ItemBase, ...] = ()


@dataclass(frozen=True)
class EstadoBase:
    """El veredicto sobre una base, con lo que falta y de quién.

    `faltan_por_quien` no es un adorno de presentación: sin saber a quién
    pedirle cada hueco, «la base está incompleta» no es accionable, y una
    lista de huecos que nadie sabe quién llena se queda sin llenar.
    """

    completa: bool
    razon: str
    faltan: tuple[ItemBase, ...] = ()

    @property
    def faltan_por_quien(self) -> dict[str, list[str]]:
        salida: dict[str, list[str]] = {}
        for item in self.faltan:
            salida.setdefault(item.quien.value, []).append(item.nombre)
        return salida


@dataclass
class Base:
    """Una base definida, cargada de su declaración."""

    titulo: str
    version: str
    alcance: Alcance
    secciones: tuple[SeccionBase, ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def items(self) -> tuple[ItemBase, ...]:
        return tuple(item for seccion in self.secciones for item in seccion.items)

    @property
    def depende_de_la_edad(self) -> bool:
        return any(item.depende_de_la_edad for item in self.items)

    def exigidos(self, edad: int) -> tuple[ItemBase, ...]:
        return tuple(item for item in self.items if item.aplica_a(edad))


def evaluar(base: Base, cubiertos: Iterable[str], edad: int | None) -> EstadoBase:
    """Qué le falta a esta base, o por qué no se puede saber.

    `cubiertos` son los nombres de lo ya averiguado. La comparación es por
    nombre normalizado y no por código porque un ítem de la base puede no
    tener concepto —«¿con quién vive?» no está en ningún vocabulario
    clínico— y dejar fuera lo que no se codifica sería reducir la base a lo
    que el índice ya sabe nombrar.
    """
    if base.depende_de_la_edad and edad is None:
        # Ni saltarlos ni exigirlos sería cierto. Se dice y se para.
        return EstadoBase(
            completa=False,
            razon=(
                "Esta base condiciona ítems por edad y la edad no consta. No se "
                "puede saber cuáles aplican: averigüe la edad antes de evaluarla."
            ),
        )

    vistos = {_normalizar(nombre) for nombre in cubiertos}
    exigidos = base.exigidos(edad) if edad is not None else base.items
    faltan = tuple(item for item in exigidos if _normalizar(item.nombre) not in vistos)

    if not faltan:
        return EstadoBase(completa=True, razon="La base está completa.")

    return EstadoBase(
        completa=False,
        razon=(
            f"Faltan {len(faltan)} de {len(exigidos)} ítems de «{base.titulo}». "
            "La lista de problemas es un artefacto de la base: incompleta la "
            "base, la lista no se puede dar por cerrada."
        ),
        faltan=faltan,
    )


def _normalizar(texto: str) -> str:
    return " ".join(texto.lower().split())


def _item(crudo: Any) -> ItemBase | None:
    """Un ítem mal declarado no se adivina: se descarta y no cuenta."""
    if not isinstance(crudo, dict):
        return None
    nombre = str(crudo.get("nombre") or "").strip()
    if not nombre:
        return None
    try:
        quien = Quien(str(crudo.get("quien", "")).strip().lower())
    except ValueError:
        # Sin `quien` no hay a quién pedírselo, y un ítem que nadie obtiene
        # sólo sirve para que la base nunca se complete.
        return None
    return ItemBase(
        nombre=nombre,
        quien=quien,
        codigo=str(crudo["codigo"]) if crudo.get("codigo") else None,
        desde_edad=_entero(crudo.get("desde_edad")),
        hasta_edad=_entero(crudo.get("hasta_edad")),
    )


def _entero(valor: Any) -> int | None:
    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def cargar(ruta: Path) -> Base:
    """Lee una base declarada en Markdown con frontmatter, como las skills.

    Se usa el mismo formato a propósito: el proyecto ya tiene un lenguaje
    para declarar conocimiento verificable, y una base de datos definida es
    conocimiento verificable. Inventar un segundo formato costaría un
    parser, un validador y una forma más de equivocarse.
    """
    match = _FRONTMATTER.match(ruta.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{ruta.name}: sin frontmatter, no es una base declarada")

    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"{ruta.name}: el frontmatter no es un mapa")

    try:
        alcance = Alcance(str(meta.get("alcance", "")).strip().lower())
    except ValueError as exc:
        raise ValueError(
            f"{ruta.name}: `alcance` debe ser 'comprehensiva' o 'episodica'. "
            "No se supone: una base mínima que se lea como comprehensiva "
            "daría por cubierto lo que nadie preguntó."
        ) from exc

    secciones: list[SeccionBase] = []
    for cruda in meta.get("secciones") or []:
        if not isinstance(cruda, dict) or not cruda.get("nombre"):
            continue
        items = tuple(
            item
            for item in (_item(c) for c in cruda.get("items") or [])
            if item is not None
        )
        secciones.append(SeccionBase(nombre=str(cruda["nombre"]), items=items))

    return Base(
        titulo=str(meta.get("titulo") or ruta.stem),
        version=str(meta.get("version") or "0.0.0"),
        alcance=alcance,
        secciones=tuple(secciones),
        meta=meta,
    )


def cargar_todas(directorio: Path) -> dict[str, Base]:
    """Todas las bases de un directorio, indexadas por nombre de archivo."""
    if not directorio.is_dir():
        return {}
    return {ruta.stem: cargar(ruta) for ruta in sorted(directorio.glob("*.md"))}


def validar(bases: Sequence[Base]) -> list[str]:
    """Problemas de las bases declaradas, en el mismo espíritu que las skills.

    Se comprueba lo que puede estar mal sin salir del archivo. Que los
    códigos existan en el vocabulario lo comprueba CI aparte, igual que con
    los protocolos.
    """
    problemas: list[str] = []
    for base in bases:
        if not base.items:
            problemas.append(f"«{base.titulo}» no exige ni un ítem: no es una base.")
        vistos: set[str] = set()
        for item in base.items:
            clave = _normalizar(item.nombre)
            if clave in vistos:
                problemas.append(f"«{base.titulo}» declara «{item.nombre}» dos veces.")
            vistos.add(clave)
            if (
                item.desde_edad is not None
                and item.hasta_edad is not None
                and item.desde_edad > item.hasta_edad
            ):
                problemas.append(
                    f"«{base.titulo}» → «{item.nombre}»: el rango de edad está "
                    f"invertido ({item.desde_edad}–{item.hasta_edad}); no lo "
                    "cumple nadie."
                )
    return problemas
