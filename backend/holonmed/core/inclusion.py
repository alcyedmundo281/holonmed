"""Un signo incluido en otro: una sola observación.

«Descenso del segmento ST» es un caso de «Signos de isquemia en el
electrocardiograma». Cada uno tiene su likelihood ratio, medido por separado:
aplicar los dos a un trazado multiplica una evidencia que se observó una vez.

La relación la DECLARA el protocolo, en el signo estrecho::

    incluido_en: ["HM:3016"]

con códigos de otros signos del mismo protocolo. Nunca se infiere de los
nombres ni del grafo del vocabulario, cuyo `padre` agrupa por sistema.

PARÁMETRO DE SEGURIDAD. Bayes, el veredicto declarado, la promoción y Φ
aplican la misma regla, la de este módulo. Con el signo estrecho `e` incluido
en el amplio `a`, cuando constan los dos:

    =========  =========  ==============================================
    `e`        `a`        cuenta
    =========  =========  ==============================================
    presente   presente   sólo `e`, aunque su cociente fuera el menor
    ausente    presente   sólo `a`; el LR− de `e` no se aplica
    ausente    ausente    sólo `a`: su ausencia ya implica la de `e`
    presente   ausente    ninguno: es una contradicción y se informa
    =========  =========  ==============================================

La contradicción no se resuelve por fecha: `Infon.timestamp` es la hora de la
extracción y no la del examen. Si sólo consta uno, cuenta ése. Cada par se
juzga sobre lo observado, así que el resultado no depende del orden.

Una declaración que no se puede cumplir invalida el protocolo entero para los
cuatro consumidores: calcular ignorándola sería volver a contar dos veces.
"""

from collections.abc import Collection, Mapping, Sequence
from typing import TYPE_CHECKING, Any, NamedTuple

from ..models import Infon, Polaridad
from .bayes import elegir_por_signo

if TYPE_CHECKING:  # pragma: no cover - sólo para tipado
    from .skills import Signo

CLAVE = "incluido_en"

# Una contradicción hace que no cuente ninguno de los dos. Sobre una exclusión
# o una bandera roja eso borraría un veto, así que ahí no se admite inclusión.
EFECTOS_UNIFICABLES = ("apoya", "evidencia")

# Signo estrecho -> TODOS los signos que lo incluyen, directa o indirectamente.
# Las claves son nombres en minúsculas, las del vocabulario de emparejamiento.
Inclusiones = Mapping[str, frozenset[str]]


class Unificacion(NamedTuple):
    cuentan: dict[str, Infon]
    descartados: dict[str, str]  # signo -> por qué no cuenta, para la traza


def declarar(
    signos: Sequence["Signo"], crudos: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, frozenset[str]], list[str]]:
    """Resuelve lo declarado a nombres de signo y dice todo lo que está mal.

    `crudos[i]` es el YAML del que salió `signos[i]`. Con un solo error no se
    devuelve ninguna relación: media declaración no es una declaración.
    """
    errores: list[str] = []
    por_codigo: dict[str, list[Signo]] = {}
    for signo in signos:
        codigo = signo.codigos.get("holonmed")
        if codigo:
            por_codigo.setdefault(codigo, []).append(signo)

    directas: dict[str, set[str]] = {}
    for signo, crudo in zip(signos, crudos, strict=True):
        donde = f"signo '{signo.nombre}'"
        # Una errata en la clave dejaría el par sin declarar sin que se note.
        for clave in crudo:
            if str(clave).lower().startswith("inclu") and clave != CLAVE:
                errores.append(f"{donde}: clave '{clave}' desconocida; es '{CLAVE}'")
        if CLAVE not in crudo:
            continue
        lista = crudo[CLAVE]
        if (
            not isinstance(lista, list)
            or not lista
            or not all(isinstance(c, str) and c.strip() for c in lista)
        ):
            errores.append(f"{donde}: '{CLAVE}' debe ser una lista de códigos HM:")
            continue
        for codigo in lista:
            destinos = por_codigo.get(codigo.strip(), [])
            if len(destinos) != 1:
                motivo = "no es de ningún" if not destinos else "es de más de un"
                errores.append(
                    f"{donde}: '{CLAVE}' cita '{codigo}', que {motivo} signo "
                    f"de este protocolo"
                )
                continue
            amplio = destinos[0]
            fallos = _incompatibilidades(signo, amplio)
            if fallos:
                errores.extend(
                    f"{donde}: incluido en '{amplio.nombre}', {f}" for f in fallos
                )
                continue
            directas.setdefault(signo.nombre.lower(), set()).add(amplio.nombre.lower())

    cerradas: dict[str, frozenset[str]] = {}
    for estrecho in directas:
        alcanzados: set[str] = set()
        pendientes = list(directas[estrecho])
        while pendientes:
            actual = pendientes.pop()
            if actual not in alcanzados:
                alcanzados.add(actual)
                pendientes.extend(directas.get(actual, ()))
        if estrecho in alcanzados:
            errores.append(f"signo '{estrecho}': '{CLAVE}' forma un ciclo")
        cerradas[estrecho] = frozenset(alcanzados)

    return ({} if errores else cerradas), errores


def _incompatibilidades(estrecho: "Signo", amplio: "Signo") -> list[str]:
    if estrecho is amplio or estrecho.nombre.lower() == amplio.nombre.lower():
        return ["que es él mismo"]
    fallos = [
        f"con distinto '{campo}'"
        for campo in ("efecto", "dispara_si", "rol")
        if getattr(estrecho, campo) != getattr(amplio, campo)
    ]
    if estrecho.efecto not in EFECTOS_UNIFICABLES:
        fallos.append(
            f"con efecto '{estrecho.efecto}': sólo se unifican "
            f"{' y '.join(EFECTOS_UNIFICABLES)}"
        )
    if estrecho.tramos or amplio.tramos:
        fallos.append("y uno de los dos está graduado por tramos")
    return fallos


def unificar(elegidos: Mapping[str, Infon], inclusiones: Inclusiones) -> Unificacion:
    """Aplica la tabla del módulo a un infón por signo."""
    descartados: dict[str, str] = {}
    contradichos: dict[str, str] = {}
    for estrecho, amplios in inclusiones.items():
        if estrecho not in elegidos:
            continue
        for amplio in sorted(amplios):
            if amplio not in elegidos:
                continue
            uno, otro = elegidos[estrecho], elegidos[amplio]
            presente = uno.polaridad is Polaridad.PRESENTE
            if presente and otro.polaridad is not Polaridad.PRESENTE:
                motivo = (
                    f"'{uno.termino}' consta presente y '{otro.termino}', que lo "
                    f"incluye, no: contradicción, no cuenta ninguno de los dos"
                )
                contradichos[estrecho] = contradichos[amplio] = motivo
            elif presente:
                descartados[amplio] = (
                    f"'{otro.termino}' incluye a '{uno.termino}': una sola "
                    f"observación, cuenta la específica"
                )
            else:
                descartados[estrecho] = (
                    f"'{uno.termino}' está incluido en '{otro.termino}': una sola "
                    f"observación, cuenta la amplia"
                )
    descartados.update(contradichos)
    return Unificacion(
        {c: i for c, i in elegidos.items() if c not in descartados}, descartados
    )


def filtrar_incluidos(
    pares: Sequence[tuple[str, Infon]], inclusiones: Inclusiones
) -> tuple[list[tuple[str, Infon]], list[str]]:
    """Los pares (signo, infón) que quedan tras aplicar las inclusiones y por qué.

    Para los consumidores que recorren los infones de uno en uno. De un signo
    que participa en una inclusión queda el infón que elige
    `elegir_por_signo`, el mismo con el que se juzgó el par; los demás signos
    pasan como estaban.
    """
    relacionados = set(inclusiones).union(*inclusiones.values())
    elegidos = elegir_por_signo(pares)
    cuentan, descartados = unificar(elegidos, inclusiones)
    quedan = [
        (clave, infon)
        for clave, infon in pares
        if clave not in relacionados or cuentan.get(clave) is infon
    ]
    return quedan, list(dict.fromkeys(descartados.values()))


def dimensiones_vigentes(
    claves: Collection[str], cuentan: Collection[str], inclusiones: Inclusiones
) -> set[str]:
    """Qué signos forman el espacio donde se mide Φ.

    `claves` son los candidatos a dimensión y `cuentan` los signos que quedan
    tras unificar. Quien ya queda cubierto por uno que cuenta sale del caso de
    libro y del real: dejarlo en el primero castigaría la cobertura por no
    medir dos veces lo mismo. Un par del que no cuenta ninguno —nadie lo miró,
    o se contradice— es una sola dimensión sin medir, la amplia.
    """

    def relacionados(a: str, b: str) -> bool:
        return b in inclusiones.get(a, ()) or a in inclusiones.get(b, ())

    vigentes = {c for c in claves if c in cuentan}
    # De los más amplios a los más estrechos.
    for clave in sorted(claves, key=lambda c: (len(inclusiones.get(c, ())), c)):
        if clave in vigentes or any(relacionados(clave, o) for o in cuentan):
            continue
        if not inclusiones.get(clave, frozenset()) & vigentes:
            vigentes.add(clave)
    return vigentes
