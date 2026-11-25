"""La forma de nota clínica: evolución SOAP por problema.

Tres reglas, y las tres son de seguridad antes que de estilo.

1. **A y P no tienen campo.** El análisis y el plan los escribe el
   profesional. Un número en «Análisis» se lee como diagnóstico y un dato
   pendiente en «Plan» se lee como indicación, así que aquí no hay dónde
   ponerlos: la nota sólo puede declararlos vacíos.
2. **S y O sólo si la narrativa lo declara** con «S:» u «O:». No se deduce de
   palabras como «refiere» ni se rellena con un valor por defecto: lo que
   nadie declaró sale como sin clasificar.
3. **Cada hallazgo validado y presente es un problema.** Lo negado no lo es y
   va aparte; lo no validado queda fuera de la nota, a la vista. Agrupar
   varios hallazgos bajo un problema es un juicio, y no lo hace el sistema.

Nada de aquí llama al modelo ni usa su `resumen`, que es texto libre sin
validar.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from ..models import (
    EstadoInfon,
    HallazgoFueraDeNota,
    Infon,
    NegativoDocumentado,
    NotaEvolucion,
    Polaridad,
    ProblemaEvolucion,
    ResultadoTic,
)

SUBJETIVO = "subjetivo"
OBJETIVO = "objetivo"
DERIVADO = "derivado"
SIN_DECLARAR = "sin_declarar"

SIN_DATO = "sin dato declarado"
SIN_VALORACION = "sin valoración; la escribe el profesional"
SIN_PLAN = "sin plan; lo escribe el profesional"

# Una marca sólo vale al empezar el texto, una línea o una frase: «grupo
# sanguíneo O: positivo» no abre ninguna sección. Los demás encabezados no
# declaran nada, pero cierran la sección abierta: sin eso, lo escrito bajo
# «Plan:» quedaría como objetivo.
_MARCA = re.compile(
    r"(?:\A|\n|(?<=[.;!?]))[ \t]*"
    r"(?P<marca>S|O|A|P|(?i:subjetivo|objetivo|an[áa]lisis|apreciaci[óo]n|"
    r"valoraci[óo]n|impresi[óo]n|diagn[óo]stico|plan|antecedentes))[ \t]*:"
)
_LINEA_EN_BLANCO = re.compile(r"\n[ \t\r]*\n")


def _aplanar(texto: str) -> str:
    return " ".join(texto.split()).casefold()


def _secciones(narrativa: str) -> list[tuple[str, str]]:
    """Trocea la narrativa en (procedencia declarada, texto aplanado)."""
    tramos: list[tuple[str, str]] = []
    marca, inicio = "", 0
    cortes = [(m.start(), m.end(), m.group("marca")) for m in _MARCA.finditer(narrativa)]
    for desde, hasta, siguiente in [*cortes, (len(narrativa), len(narrativa), "")]:
        cuerpo = narrativa[inicio:desde]
        declarada = {"S": SUBJETIVO, "O": OBJETIVO}.get(marca, SIN_DECLARAR)
        # Una línea en blanco cierra la sección: ante la duda, sin declarar.
        primero, *resto = _LINEA_EN_BLANCO.split(cuerpo)
        tramos.append((declarada, _aplanar(primero)))
        tramos.extend((SIN_DECLARAR, _aplanar(parrafo)) for parrafo in resto)
        marca, inicio = siguiente, hasta
    return tramos


def declarar_procedencia(narrativa: str, cita: str) -> str:
    """Bajo qué marca está la cita. Si no se sabe con certeza, sin declarar.

    Si la cita aparece en dos secciones distintas, o no aparece literal en
    ninguna, no se elige.
    """
    buscada = _aplanar(cita).strip(" .;,:")
    if not buscada:
        return SIN_DECLARAR
    patron = re.compile(rf"(?<!\w){re.escape(buscada)}(?!\w)")
    halladas = {
        declarada for declarada, texto in _secciones(narrativa) if patron.search(texto)
    }
    return halladas.pop() if len(halladas) == 1 else SIN_DECLARAR


def procedencia_de(infon: Infon, narrativa: str) -> str:
    """Lo derivado no lo aseveró nadie; lo demás, lo que declare la narrativa."""
    if infon.derivado_de or infon.criterio:
        return DERIVADO
    return declarar_procedencia(narrativa, infon.texto_origen)


def asignar_procedencia(infones: Iterable[Infon], narrativa: str) -> None:
    for infon in infones:
        infon.procedencia = procedencia_de(infon, narrativa)


def etiqueta_derivado(infon: Infon) -> str:
    return (
        f"{infon.termino} (criterio: {infon.criterio})"
        if infon.criterio
        else infon.termino
    )


def lineas_soap(
    subjetivo: Sequence[str],
    objetivo: Sequence[str],
    sin_clasificar: Sequence[str],
    derivado: Sequence[str],
) -> list[str]:
    """Las líneas de un problema. S, O, A y P salen siempre, con dato o sin él."""
    lineas = [f"  S: {_citas(subjetivo)}", f"  O: {_citas(objetivo)}"]
    if sin_clasificar:
        lineas.append(f"  Sin clasificar S/O: {_citas(sin_clasificar)}")
    if derivado:
        lineas.append(f"  Derivado, no escrito en la nota: {'; '.join(derivado)}")
    lineas.append(f"  A: {SIN_VALORACION}")
    lineas.append(f"  P: {SIN_PLAN}")
    return lineas


def _citas(citas: Sequence[str]) -> str:
    return " · ".join(f"«{c}»" for c in citas) if citas else SIN_DATO


_NOMBRE_PROCEDENCIA = {SUBJETIVO: "S", OBJETIVO: "O", DERIVADO: "derivado"}


def linea_negativo(termino: str, cita: str, procedencia: str) -> str:
    # El término y «ausente» van delante: la cita del modelo puede venir
    # recortada y no incluir la negación.
    donde = _NOMBRE_PROCEDENCIA.get(procedencia, "sin clasificar S/O")
    return f"  {termino}: ausente · «{cita}» [{donde}]"


def _clave(codigo: Any, termino: str) -> str:
    # La misma que agrupa la lista de problemas: `COALESCE(codigo, termino)`.
    return str(codigo) if codigo is not None else termino


def construir_nota(
    resultado: ResultadoTic, lista: Sequence[Mapping[str, Any]] = ()
) -> NotaEvolucion:
    """La nota de evolución de un tic, como borrador sin firma.

    `lista` es la lista de problemas del paciente, y de ella salen los
    números. Un problema que no está en ella —el tic no se guardó— sale sin
    número en vez de recibir uno inventado.
    """
    asignar_procedencia(resultado.infones, resultado.texto_original)
    numeros = {_clave(p.get("codigo"), p["termino"]): p["numero"] for p in lista}

    problemas: dict[str, ProblemaEvolucion] = {}
    negativos: list[NegativoDocumentado] = []
    fuera: list[HallazgoFueraDeNota] = []
    for infon in resultado.infones:
        rechazado = infon.acto == "rechazado"
        if infon.estado is not EstadoInfon.VALIDADO or rechazado:
            fuera.append(
                HallazgoFueraDeNota(
                    termino=infon.termino,
                    cita=infon.texto_origen,
                    estado="RECHAZADO" if rechazado else infon.estado.value,
                )
            )
            continue
        if infon.polaridad is Polaridad.AUSENTE:
            negativos.append(
                NegativoDocumentado(
                    termino=infon.termino,
                    cita=infon.texto_origen,
                    procedencia=infon.procedencia,
                )
            )
            continue

        clave = _clave(infon.codigo, infon.termino)
        problema = problemas.setdefault(
            clave,
            ProblemaEvolucion(
                numero=numeros.get(clave), termino=infon.termino, codigo=infon.codigo
            ),
        )
        if infon.procedencia == DERIVADO:
            destino, dato = problema.derivado, etiqueta_derivado(infon)
        else:
            destino = {
                SUBJETIVO: problema.subjetivo,
                OBJETIVO: problema.objetivo,
            }.get(infon.procedencia, problema.sin_clasificar)
            dato = infon.texto_origen
        if dato not in destino:
            destino.append(dato)

    nota = NotaEvolucion(
        problemas=sorted(
            problemas.values(), key=lambda p: (p.numero is None, p.numero or 0)
        ),
        negativos=negativos,
        fuera_de_la_nota=fuera,
    )
    nota.texto = _texto(nota, resultado)
    return nota


def _fecha_local(marca: str) -> str:
    """La fecha donde se atiende. Se guarda en UTC, y recortarla fecharía al
    día siguiente lo escrito por la tarde al oeste de Greenwich."""
    return datetime.fromisoformat(marca).astimezone().date().isoformat()


def _texto(nota: NotaEvolucion, resultado: ResultadoTic) -> str:
    secciones = [
        f"EVOLUCIÓN: borrador sin firma · {_fecha_local(resultado.timestamp)} · "
        f"origen: {resultado.origen.value}"
    ]
    for p in nota.problemas:
        numero = f"#{p.numero}" if p.numero is not None else "(sin número)"
        secciones.append(
            "\n".join(
                [f"{numero} {p.termino}"]
                + lineas_soap(p.subjetivo, p.objetivo, p.sin_clasificar, p.derivado)
            )
        )
    if not nota.problemas:
        secciones.append("Sin problemas: ningún hallazgo validado y presente.")

    negativos = [linea_negativo(n.termino, n.cita, n.procedencia) for n in nota.negativos]
    secciones.append(
        "\n".join(
            ["Negativos documentados (no son problemas)"] + (negativos or ["  ninguno"])
        )
    )
    fuera = [f"  [{f.estado}] {f.termino} · «{f.cita}»" for f in nota.fuera_de_la_nota]
    secciones.append(
        "\n".join(
            ["Fuera de la nota (no validado, para revisar)"] + (fuera or ["  nada"])
        )
    )
    return "\n\n".join(secciones)
