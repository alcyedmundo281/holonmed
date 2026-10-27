"""La historia del holon: lo que se le ha hecho al paciente, en orden.

POR QUÉ HACE FALTA
------------------
Φ contrasta una hipótesis con el contexto del paciente, y hasta ahora ese
contexto era **una nota de hoy**. Los dos extremos del coeficiente eran
documentales: `h` sale de la literatura —los `ln(LR)` publicados— y `e` salía
de un texto. Ninguno tocaba lo que se le hizo al paciente.

Si una creencia es una regla de acción, contrastar un diagnóstico con la prosa
de una nota lo contrasta con una **descripción**; contrastarlo con el registro
de acciones lo contrasta con **hábitos**. Este módulo no calcula ningún
coeficiente: construye el registro que haría falta para calcularlo, y que
mientras tanto ya sirve como contexto para el modelo.

NO SE INVENTA NADA: EL REGISTRO YA EXISTÍA
------------------------------------------
Está repartido en cinco tablas, todas indexadas por paciente y tiempo, y era
un subproducto de la facturación y de la emisión de documentos. Nadie lo leía
como **una** historia:

    tic         cada interacción, con su actor, su origen y su protocolo
    orden       lo que un clínico mandó hacer, con su prescriptor
    ejecucion   lo que alguien hizo de verdad, con su actor
    documento   recetas e informes emitidos
    infon       hallazgos validados, con su procedencia

El par `orden`/`ejecucion` merece decirse aparte. Una orden es una regla de
acción **declarada**; una ejecución es el acto. La diferencia entre ambas ya la
calcula `facturacion` para cobrar, y es literalmente el sitio donde una
creencia se enunció y no se sostuvo en la conducta. Aquí se conserva esa
distinción en vez de fundir las dos en «lo que pasó».

EL LÍMITE, DICHO ANTES DE QUE ALGUIEN LO SUPONGA
------------------------------------------------
Esto no es la historia clínica del paciente desde su nacimiento: es lo que
HolonMed ha registrado desde que se encendió, más los antecedentes que alguna
nota haya declarado y que hayan llegado a `infon`. Alimentarlo desde la
historia del centro es otra pieza, y no existe.

EL FILTRO POR TERRITORIO Y SU MODO DE FALLO
-------------------------------------------
Una vida no cabe en un coseno. Si todo lo que una hipótesis no explica baja el
acoplamiento, cuarenta años de acciones dejan **todas** las hipótesis en Φ≈0,
porque ningún diagnóstico explica una vida. Lo que hace falta no es recortar
por tiempo sino por **territorio**: qué acciones caen bajo el ámbito de la
hipótesis, que es lo que `ambito_grafo` declara y la tabla `ancestro` resuelve
con un join.

Y ahí está el modo de fallo que este módulo se niega a cometer en silencio:
**una acción sin `concepto_id` no se puede colocar en ningún territorio.** Un
filtro que simplemente no la devuelva convierte «no sé dónde va» en «no
aplica», que son cosas distintas y la segunda es una afirmación que nadie ha
comprobado. Por eso `Historia` lleva la cuenta de lo que no pudo colocar, y
`resumen()` la dice en voz alta.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

# Las clases de acción, de la más comprometida a la menos. El orden NO es
# decorativo: es el que se usa para desempatar cuando dos acciones comparten
# instante, y deja arriba lo que más compromete una creencia.
CLASES = ("ejecucion", "orden", "documento", "consulta", "hallazgo")


@dataclass(frozen=True)
class Accion:
    """Una cosa que se hizo, o que se mandó hacer, o que se registró.

    `clase` distingue el acto de la intención, que es la distinción que hace
    útil este registro: una orden sin ejecución no es un hueco, es un
    incidente —lo dice el propio esquema— y una ejecución sin orden es otro.
    """

    momento: str
    clase: str
    termino: str
    actor: str = ""
    detalle: str = ""
    concepto_id: int | None = None
    codigo: str | None = None
    sistema: str | None = None
    tic_id: str | None = None
    estado: str = ""
    texto_origen: str = ""

    @property
    def ubicable(self) -> bool:
        """¿Se puede decir a qué territorio pertenece?

        Sin concepto no se puede, y eso no es lo mismo que estar fuera.
        """
        return self.concepto_id is not None

    def linea(self) -> str:
        partes = [self.momento[:16], f"[{self.clase}]", self.termino]
        if self.actor:
            partes.append(f"— {self.actor}")
        if self.detalle:
            partes.append(f"({self.detalle})")
        if self.estado and self.estado not in ("VALIDADO", "pendiente"):
            partes.append(f"«{self.estado}»")
        return " ".join(partes)


@dataclass
class Historia:
    """El registro de acciones de un holon, con lo que no cupo en él.

    `sin_ubicar` no es un detalle de implementación: es la parte del paciente
    que este recorte **no puede afirmar** que sea irrelevante. Se devuelve
    junto al resultado para que ningún consumidor la confunda con un cero.
    """

    paciente_id: str
    acciones: list[Accion] = field(default_factory=list)
    sin_ubicar: list[Accion] = field(default_factory=list)
    fuera_de_territorio: int = 0
    ambito: tuple[str, ...] = ()
    truncada: bool = False
    traza: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.acciones)

    def ordenes_sin_ejecutar(self) -> list[Accion]:
        """Reglas de acción declaradas que nadie llevó a cabo.

        Se calcula sobre lo que hay en la historia, no sobre la base entera:
        una orden ejecutada fuera de la ventana consultada no está aquí, y
        decir lo contrario sería afirmar más de lo que se ha mirado.
        """
        ejecutados = {
            (a.codigo or a.termino).lower()
            for a in self.acciones
            if a.clase == "ejecucion"
        }
        return [
            a
            for a in self.acciones
            if a.clase == "orden" and (a.codigo or a.termino).lower() not in ejecutados
        ]

    def resumen(self) -> str:
        cuenta: dict[str, int] = {}
        for a in self.acciones:
            cuenta[a.clase] = cuenta.get(a.clase, 0) + 1
        piezas = [f"{cuenta[c]} {c}" for c in CLASES if c in cuenta]
        texto = (
            f"{self.total} acciones ({', '.join(piezas)})" if piezas else "sin acciones"
        )
        if self.ambito:
            texto += f" bajo {', '.join(self.ambito)}"
            texto += f"; {self.fuera_de_territorio} fuera del territorio"
            if self.sin_ubicar:
                texto += (
                    f"; {len(self.sin_ubicar)} SIN CONCEPTO, que no se pueden "
                    f"ubicar y por tanto no se declaran irrelevantes"
                )
        if self.truncada:
            texto += " (recortada por el límite)"
        return texto

    def para_llm(self, limite: int = 60) -> str:
        """El registro en texto plano, lo más reciente primero."""
        cabecera = [f"HISTORIA DE ACCIONES — {self.resumen()}", ""]
        cuerpo = [a.linea() for a in self.acciones[:limite]]
        pendientes = self.ordenes_sin_ejecutar()
        if pendientes:
            cuerpo += [
                "",
                "ÓRDENES SIN EJECUCIÓN REGISTRADA (una regla de acción "
                "declarada que no consta cumplida):",
            ]
            cuerpo += [f"  - {a.momento[:10]} {a.termino}" for a in pendientes[:20]]
        if self.sin_ubicar:
            cuerpo += [
                "",
                f"{len(self.sin_ubicar)} acciones sin concepto asignado: no se "
                f"pudieron situar en ningún territorio y NO se han descartado.",
            ]
        return "\n".join(cabecera + cuerpo)


class HistoriaRepo:
    """Lee las cinco tablas como una sola historia.

    No escribe nada. La historia es una **lectura derivada**: duplicarla en
    una tabla propia crearía una segunda fuente de verdad que se desincroniza
    en cuanto alguien inserte por otro camino.
    """

    def __init__(self, db, grafo=None):
        self._db = db
        self._grafo = grafo

    # --- API -----------------------------------------------------------

    def del_holon(
        self,
        paciente_id: str,
        ambito: Sequence[str] = (),
        desde: str | None = None,
        hasta: str | None = None,
        limite: int = 500,
    ) -> Historia:
        """Todas las acciones de un paciente, lo más reciente primero.

        `ambito` son códigos de concepto —los mismos que declara
        `skill.ambito_grafo`—. Con ámbito, la historia se recorta al
        territorio de la hipótesis; lo que queda fuera se cuenta, y lo que no
        se puede ubicar se devuelve aparte y NO se cuenta como fuera.
        """
        historia = Historia(paciente_id=paciente_id, ambito=tuple(ambito))

        crudas = list(self._leer(paciente_id, desde, hasta, limite))
        crudas.sort(key=_clave_de_orden, reverse=True)
        if len(crudas) > limite:
            crudas = crudas[:limite]
            historia.truncada = True

        if not ambito:
            historia.acciones = crudas
            historia.traza.append(f"{len(crudas)} acciones, sin recorte de territorio")
            return historia

        permitidos = self._ids_bajo(ambito)
        if not permitidos:
            # Un ámbito que no resuelve a ningún concepto no es un territorio
            # vacío: es un ámbito roto. Recortar con él dejaría la historia a
            # cero y parecería un paciente sin historia.
            historia.acciones = crudas
            historia.traza.append(
                f"el ámbito {list(ambito)} no resuelve a ningún concepto: no se "
                f"recorta, porque un ámbito roto no es un territorio vacío"
            )
            return historia

        for accion in crudas:
            if not accion.ubicable:
                historia.sin_ubicar.append(accion)
            elif accion.concepto_id in permitidos:
                historia.acciones.append(accion)
            else:
                historia.fuera_de_territorio += 1

        historia.traza.append(
            f"{len(historia.acciones)} en territorio, "
            f"{historia.fuera_de_territorio} fuera, "
            f"{len(historia.sin_ubicar)} sin concepto"
        )
        return historia

    # --- Lectura de cada tabla -----------------------------------------

    def _leer(
        self, paciente_id: str, desde: str | None, hasta: str | None, limite: int
    ) -> Iterable[Accion]:
        cx = self._db.conexion()
        for consulta in (
            self._tics,
            self._ordenes,
            self._ejecuciones,
            self._documentos,
            self._hallazgos,
        ):
            yield from consulta(cx, paciente_id, desde, hasta, limite)

    @staticmethod
    def _ventana(campo: str, desde: str | None, hasta: str | None) -> tuple[str, list]:
        sql, binds = "", []
        if desde:
            sql += f" AND {campo} >= ?"
            binds.append(desde)
        if hasta:
            sql += f" AND {campo} <= ?"
            binds.append(hasta)
        return sql, binds

    def _tics(self, cx, paciente_id, desde, hasta, limite) -> list[Accion]:
        filtro, binds = self._ventana("timestamp", desde, hasta)
        filas = cx.execute(
            "SELECT id, timestamp, origen, actor, skill, resumen FROM tic "
            "WHERE paciente_id = ?" + filtro + " ORDER BY timestamp DESC LIMIT ?",
            [paciente_id, *binds, limite],
        )
        return [
            Accion(
                momento=str(f["timestamp"]),
                clase="consulta",
                termino=str(f["skill"] or "consulta"),
                actor=str(f["actor"] or f["origen"] or ""),
                detalle=str(f["resumen"] or "")[:120],
                tic_id=str(f["id"]),
            )
            for f in filas
        ]

    def _ordenes(self, cx, paciente_id, desde, hasta, limite) -> list[Accion]:
        filtro, binds = self._ventana("timestamp", desde, hasta)
        filas = cx.execute(
            "SELECT id, timestamp, termino, codigo, sistema, concepto_id, "
            "       prescriptor, detalle, estado, tic_id, texto_origen "
            "FROM orden WHERE paciente_id = ?"
            + filtro
            + " ORDER BY timestamp DESC LIMIT ?",
            [paciente_id, *binds, limite],
        )
        return [
            Accion(
                momento=str(f["timestamp"]),
                clase="orden",
                termino=str(f["termino"]),
                actor=str(f["prescriptor"] or ""),
                detalle=_detalle(f["detalle"]),
                concepto_id=f["concepto_id"],
                codigo=f["codigo"],
                sistema=f["sistema"],
                tic_id=_texto(f["tic_id"]),
                estado=str(f["estado"] or ""),
                texto_origen=str(f["texto_origen"] or ""),
            )
            for f in filas
        ]

    def _ejecuciones(self, cx, paciente_id, desde, hasta, limite) -> list[Accion]:
        filtro, binds = self._ventana("timestamp", desde, hasta)
        filas = cx.execute(
            "SELECT id, timestamp, termino, codigo, sistema, actor, origen, "
            "       detalle, tic_id, texto_origen, campos_faltantes "
            "FROM ejecucion WHERE paciente_id = ?"
            + filtro
            + " ORDER BY timestamp DESC LIMIT ?",
            [paciente_id, *binds, limite],
        )
        salida = []
        for f in filas:
            faltan = _lista(f["campos_faltantes"])
            salida.append(
                Accion(
                    momento=str(f["timestamp"]),
                    clase="ejecucion",
                    termino=str(f["termino"]),
                    actor=str(f["actor"] or f["origen"] or ""),
                    detalle=_detalle(f["detalle"]),
                    concepto_id=self._concepto_por_codigo(f["codigo"], f["sistema"]),
                    codigo=f["codigo"],
                    sistema=f["sistema"],
                    tic_id=_texto(f["tic_id"]),
                    estado=f"registro incompleto: falta {', '.join(faltan)}"
                    if faltan
                    else "",
                    texto_origen=str(f["texto_origen"] or ""),
                )
            )
        return salida

    def _documentos(self, cx, paciente_id, desde, hasta, limite) -> list[Accion]:
        # La columna de tiempo aquí se llama `creado` y no `timestamp`, que es
        # como se llama en las otras cuatro. Una primera versión sondeaba el
        # esquema buscando `timestamp` o `fecha`, no encontraba ninguna y
        # devolvía cero documentos **sin decirlo**: las recetas desaparecían
        # de la historia igual que desaparecían antes de que existiera esta
        # tabla. Se lee el esquema y se escribe el nombre.
        filtro, binds = self._ventana("creado", desde, hasta)
        filas = cx.execute(
            "SELECT id, creado AS momento, tipo, tic_id FROM documento "
            "WHERE paciente_id = ?" + filtro + " ORDER BY creado DESC LIMIT ?",
            [paciente_id, *binds, limite],
        )
        return [
            Accion(
                momento=str(f["momento"]),
                clase="documento",
                termino=str(f["tipo"]),
                tic_id=_texto(f["tic_id"]),
            )
            for f in filas
        ]

    def _hallazgos(self, cx, paciente_id, desde, hasta, limite) -> list[Accion]:
        filtro, binds = self._ventana("timestamp", desde, hasta)
        filas = cx.execute(
            "SELECT timestamp, termino, codigo, sistema, concepto_id, polaridad, "
            "       estado, tic_id, texto_origen FROM infon "
            "WHERE paciente_id = ? AND estado = 'VALIDADO'"
            + filtro
            + " ORDER BY timestamp DESC LIMIT ?",
            [paciente_id, *binds, limite],
        )
        return [
            Accion(
                momento=str(f["timestamp"]),
                clase="hallazgo",
                termino=str(f["termino"]),
                detalle="" if str(f["polaridad"]) == "presente" else "ausente",
                concepto_id=f["concepto_id"],
                codigo=f["codigo"],
                sistema=f["sistema"],
                tic_id=_texto(f["tic_id"]),
                estado=str(f["estado"] or ""),
                texto_origen=str(f["texto_origen"] or ""),
            )
            for f in filas
        ]

    # --- Territorio -----------------------------------------------------

    def _ids_bajo(self, codigos: Sequence[str]) -> set[int]:
        """Conceptos que caen bajo cualquiera de esas ramas.

        Se resuelve por código sin exigir sistema, igual que hace la
        validación de `ambito_grafo` en `skills.py`: exigir el sistema
        preferente marcaría como roto un ámbito que resuelve por otra asa.

        SE RECORRE `es_un` Y NO LA TABLA `ancestro`, A PROPÓSITO.
        `ancestro` es un cierre **materializado bajo demanda**: se rellena
        dentro de `TicRepo.guardar`, y sólo para los `concepto_id` de los
        infones VALIDADOS de ese tic. Su propio comentario lo dice —«es una
        optimización de consulta, no parte del dato clínico»— y el fallo al
        materializar se traga a nivel debug.

        Consecuencia: un concepto que llegó por `orden` o por `ejecucion` y
        que nunca apareció como infón validado **no tiene fila en `ancestro`**.
        Un filtro apoyado ahí devolvería «ninguna acción en este territorio»
        cuando la verdad es «no he mirado». Con 196 conceptos, el recorrido
        recursivo cuesta nada y es correcto siempre.
        """
        cx = self._db.conexion()
        salida: set[int] = set()
        for codigo in codigos:
            filas = cx.execute(
                """WITH RECURSIVE bajo(id) AS (
                       SELECT id FROM concepto WHERE codigo = ?
                       UNION
                       SELECT e.hijo_id FROM es_un e JOIN bajo b ON e.padre_id = b.id
                   )
                   SELECT id FROM bajo""",
                (codigo,),
            )
            salida.update(int(f["id"]) for f in filas)
        return salida

    def _concepto_por_codigo(self, codigo: Any, sistema: Any) -> int | None:
        """Resuelve el concepto de una fila que guarda código pero no id.

        `orden` lleva `concepto_id`; `ejecucion` no —guarda `codigo` y
        `sistema`—. Sin esto, la clase de acción MÁS comprometida, la que
        registra lo que se hizo de verdad, sería la única que nunca se puede
        situar en un territorio. Es un hueco del esquema que aquí se rodea;
        arreglarlo de raíz es añadir la columna.
        """
        if not codigo:
            return None
        cx = self._db.conexion()
        if sistema:
            fila = cx.execute(
                "SELECT id FROM concepto WHERE codigo = ? AND sistema = ? LIMIT 1",
                (str(codigo), str(sistema)),
            ).fetchone()
            if fila:
                return int(fila["id"])
        fila = cx.execute(
            "SELECT id FROM concepto WHERE codigo = ? LIMIT 1", (str(codigo),)
        ).fetchone()
        return int(fila["id"]) if fila else None


# --- Utilidades -------------------------------------------------------


def _clave_de_orden(accion: Accion) -> tuple[str, int]:
    """Instante primero; a igualdad, lo que más compromete una creencia."""
    prioridad = len(CLASES) - CLASES.index(accion.clase)
    return (accion.momento, prioridad)


def _texto(valor: Any) -> str | None:
    return None if valor is None else str(valor)


def _detalle(crudo: Any) -> str:
    """El JSON de dosis/vía/frecuencia, en prosa corta y sin reventar."""
    if not crudo:
        return ""
    try:
        datos = json.loads(crudo) if isinstance(crudo, (str, bytes)) else crudo
    except (ValueError, TypeError):
        return str(crudo)[:120]
    if isinstance(datos, dict):
        return ", ".join(f"{k} {v}" for k, v in datos.items() if v)[:120]
    return str(datos)[:120]


def _lista(crudo: Any) -> list[str]:
    if not crudo:
        return []
    try:
        datos = json.loads(crudo) if isinstance(crudo, (str, bytes)) else crudo
    except (ValueError, TypeError):
        return []
    return [str(x) for x in datos] if isinstance(datos, list) else []
