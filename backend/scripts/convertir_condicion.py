"""Traslada una condición de medsemiotics-db al frontmatter de una skill.

El índice y este repositorio guardan el mismo conocimiento en dos formas que
no son intercambiables:

    medsemiotics-db                     holonmed
    ---------------                     --------
    concepto: 'HM:0732'                 codigos: { holonmed: "HM:0732" }
    estado_lr: medido | no_medido |     (implícito: hay `lr` o no lo hay)
               sin_efecto | no_medible
    lr_positivo: {valor, ic95, ref}     lr: 26.6
    lr_negativo: {valor, ic95, ref}     lr_negativo: 0.1
    ref: 'pmid:24938565'                fuente: cita en prosa
    umbral del concepto                 bloque `laboratorio` del protocolo

Traducir eso a mano es mecánico y por tanto se equivoca: se cae un decimal,
se pierde el intervalo, se cita de memoria. Este script hace la parte
mecánica y **se niega a hacer la parte que exige criterio**. Lo que no puede
decidir sin inventar, lo deja marcado y lo enumera al final:

  · un LR publicado como rango entre estudios no se promedia;
  · un LR− de 0.0 sale de una sensibilidad del 100% en una serie, no de una
    imposibilidad, y no se copia como si fuera certeza;
  · la probabilidad base del índice es la de la literatura, y el protocolo
    necesita la de la población que atiendes;
  · la prosa del cuerpo —el rol, la fisiopatología, las instrucciones— no
    está en el índice porque el índice no guarda prosa.

No hay red. Lee un clon local del índice y escribe un borrador que un humano
revisa, completa y sube como pull request. Esa asimetría es deliberada: es lo
que sostiene a la vez el procesamiento local y la auditabilidad del
razonamiento. Ver `medsemiotics-db/CLAUDE.md`, «La asimetría con holonmed».

Uso
===
    python scripts/convertir_condicion.py --listar
    python scripts/convertir_condicion.py HM:6007
    python scripts/convertir_condicion.py HM:6007 --salida skills/sca.md
    python scripts/convertir_condicion.py HM:6007 --indice /ruta/al/indice

Para traer de una vez toda condición nueva que medsemiotics-db haya
publicado desde la última corrida:

    python scripts/convertir_condicion.py --sync-all
    python scripts/convertir_condicion.py --sync-all --vocabulario vocabulario_nuevo.json

Decide qué es «nuevo» por el nombre de archivo de destino en
`backend/skills/`, igual que `--forzar` en el modo de una sola condición:
si el archivo ya existe, no lo toca —un protocolo en uso lleva prosa
escrita a mano que este script no reconstruye—. El vocabulario que falte
de TODAS las condiciones nuevas se consolida en un solo archivo, sin
repetir un concepto que ya pidió una condición anterior en la misma
corrida. Ningún borrador se autocompleta ni se sube solo: cada uno sigue
necesitando prosa, revisión y su propio pull request.

Casi ninguna condición del índice se apoya sólo en conceptos que holonmed ya
conozca. Los que falten salen traducidos al formato del vocabulario semilla,
para mezclarlos a mano en su lista `conceptos`:

    python scripts/convertir_condicion.py HM:6007 --vocabulario /tmp/faltan.json

Después, siempre:

    python scripts/importar_terminologia.py --semilla
    holonmed skills --validar     # comprueba que los códigos existen aquí
"""

import argparse
import io
import json
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

RAIZ_REPO = Path(__file__).resolve().parents[2]
DIRECTORIO_SKILLS = RAIZ_REPO / "backend" / "skills"
RUTA_SEMILLA = RAIZ_REPO / "backend" / "data" / "vocabulario_semilla.json"
INDICE_POR_DEFECTO = RAIZ_REPO.parent / "medsemiotics-db"

ANCHO = 74


def _consola_en_utf8() -> None:
    """La consola de Windows no habla UTF-8 y esto va lleno de acentos.

    Se hace desde `main` y no al importar: un módulo que le cambia el stdout
    a quien lo importa rompe a pytest, que lo tiene capturado.
    """
    for flujo in (sys.stdout, sys.stderr):
        if isinstance(flujo, io.TextIOWrapper):
            flujo.reconfigure(encoding="utf-8", errors="replace")

# Roles del índice que holonmed entiende. Coinciden hoy; si el índice acuña
# uno nuevo, el parseo de skills lo degradaría a «apoyo» en silencio, así que
# se avisa aquí en vez de dejar que pase desapercibido.
ROLES = ("manifestacion", "prueba_sensible", "prueba_especifica", "apoyo", "imagen")

# Las dos taxonomías del eje `efecto`. Se repiten aquí y en `skills.py` por la
# misma razón que `ROLES`: este script no importa el paquete. Que no diverjan lo
# comprueba `test_las_taxonomias_del_eje_no_divergen`.
EFECTOS = ("apoya", "bandera_roja", "excluye")
POLARIDADES = ("presente", "ausente")

# Claves de una arista que este conversor sabe traducir. Cada condición nueva
# del índice ha traído su propio bloque —tramos, sensibilidad_por_gravedad,
# modificadores—; lo que no esté aquí se anota como pendiente en vez de
# perderse.
CLAVES_ARISTA = {
    "concepto", "rol", "estado_lr", "lr_positivo", "lr_negativo",
    "motivo", "decision", "nota", "advertencia", "ref", "poblacion",
    "sensibilidad", "especificidad", "ic95_sensibilidad", "ic95_especificidad",
    # Eje `efecto`: qué papel juega el hallazgo en un criterio contado.
    "efecto", "dispara_si", "sostiene", "odds_ratio",
}

# Meter una clave en CLAVES_ARISTA sin emitirla la pasa de «denunciada» a
# SILENCIOSAMENTE PERDIDA, que es peor. Una clave entra en la lista blanca en el
# mismo commit que la emite, o entra aquí con el motivo escrito.
CONOCIDAS_NO_EMITIDAS = {
    "odds_ratio": (
        "un OR de regresión logística depende de qué covariables entraron en el "
        "modelo, así que no es una propiedad del hallazgo. `Signo` no tiene dónde "
        "ponerlo sin que el motor bayesiano pueda leerlo como cociente y "
        "multiplicarlo. Se comenta en la salida."
    ),
    "poblacion": (
        "se traslada como comentario junto a la cita, no como campo estructurado."
    ),
    "sensibilidad": "sin especificidad no hay cociente que emitir; se comenta.",
    "especificidad": "sin sensibilidad no hay cociente que emitir; se comenta.",
    "ic95_sensibilidad": "acompaña a la sensibilidad, que no se emite.",
    "ic95_especificidad": "acompaña a la especificidad, que no se emite.",
    "advertencia": "va a la prosa del cuerpo, no al frontmatter.",
    "decision": "va a la prosa del cuerpo, no al frontmatter.",
}

# Qué `sostiene` autoriza una bandera roja. La regla vive también en build.py
# del índice; se repite aquí porque el conversor puede apuntar a un clon sin
# construir. Cerrarlo del todo exige que la taxonomía viva en un archivo
# legible por máquina dentro del índice y que ambos la lean.
SOSTIENE_AUTORIZA_BANDERA = ("discriminacion_medida", "consenso_con_afirmacion")

# Un bloque del `balance` es un nivel de certeza si declara alguno de estos.
# Lista blanca POSITIVA, igual que `skills._CAMPOS_NIVEL`, y no «lo que no
# parezca nivel»: `poblacion: {...}` es un diccionario y colaba igual. Un nivel
# de más hace el criterio MÁS permisivo, que es la dirección mala.
#
# Que el mismo conjunto viva en dos archivos es el riesgo conocido; lo cierra
# `test_los_campos_de_nivel_no_divergen`, que compara los dos.
CAMPOS_NIVEL = {"apoyos_minimos", "banderas_maximas", "contrapeso"}


# ── Lectura del índice ────────────────────────────────────────────────────


@dataclass
class Indice:
    ruta: Path
    conceptos: dict[str, dict]
    condiciones: dict[str, dict]
    referencias: dict[str, dict]
    archivos: dict[str, str]
    commit: str
    limpio: bool

    def concepto(self, cid: str) -> dict:
        return self.conceptos.get(cid) or {}

    def termino(self, cid: str) -> str:
        return str(self.concepto(cid).get("termino") or cid)


def cargar_indice(ruta: Path) -> Indice:
    if not (ruta / "condiciones").is_dir():
        raise SystemExit(
            f"No parece un clon de medsemiotics-db: {ruta}\n"
            f"Clónalo junto a este repositorio o indica --indice."
        )

    def carga(directorio: str) -> tuple[dict[str, dict], dict[str, str]]:
        registros: dict[str, dict] = {}
        archivos: dict[str, str] = {}
        for archivo in sorted((ruta / directorio).glob("*.yaml")):
            try:
                datos = yaml.safe_load(archivo.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                raise SystemExit(f"YAML ilegible en {archivo.name}: {exc}") from exc
            identificador = datos.get("id")
            if not identificador:
                continue
            registros[str(identificador)] = datos
            archivos[str(identificador)] = archivo.stem
        return registros, archivos

    conceptos, _ = carga("conceptos")
    condiciones, archivos = carga("condiciones")
    referencias, _ = carga("referencias")

    return Indice(
        ruta=ruta,
        conceptos=conceptos,
        condiciones=condiciones,
        referencias=referencias,
        archivos=archivos,
        commit=_git(ruta, "rev-parse", "--short", "HEAD") or "desconocido",
        limpio=not _git(ruta, "status", "--porcelain"),
    )


def _git(ruta: Path, *args: str) -> str:
    try:
        salida = subprocess.run(
            ["git", "-C", str(ruta), *args],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return salida.stdout.strip() if salida.returncode == 0 else ""


# ── Informe de lo que queda por decidir ───────────────────────────────────


class Informe:
    """Lo que el conversor no puede resolver sin inventar.

    Separa lo que exige una decisión de lo que es backlog previsible. Un
    aviso sobre un cociente sospechoso sepultado bajo veinte rutinarios es
    un aviso que nadie lee.
    """

    def __init__(self) -> None:
        self.pendientes: list[tuple[str, str]] = []
        self.rutinarios: dict[str, list[str]] = {}

    def pendiente(self, donde: str, texto: str) -> None:
        self.pendientes.append((donde, texto))

    def rutina(self, etiqueta: str, donde: str) -> None:
        self.rutinarios.setdefault(etiqueta, []).append(donde)

    def imprimir(self) -> None:
        if self.pendientes:
            print(
                f"\n--- DECIDE ANTES DE ABRIR EL PR ({len(self.pendientes)}) ---",
                file=sys.stderr,
            )
            for donde, texto in self.pendientes:
                print(f"  · {donde}", file=sys.stderr)
                print(
                    textwrap.fill(
                        texto, width=ANCHO,
                        initial_indent="      ", subsequent_indent="      ",
                    ),
                    file=sys.stderr,
                )
        elif not self.rutinarios:
            print("\nNada pendiente de criterio humano.", file=sys.stderr)

        for etiqueta, casos in self.rutinarios.items():
            print(f"\n--- {etiqueta} ({len(casos)}) ---", file=sys.stderr)
            print(
                textwrap.fill(
                    ", ".join(casos), width=ANCHO,
                    initial_indent="  ", subsequent_indent="  ",
                ),
                file=sys.stderr,
            )


# ── Emisión de YAML con comentarios ───────────────────────────────────────
#
# `yaml.dump` no escribe comentarios, y aquí los comentarios son media
# función del archivo: son donde va la advertencia que acompaña a un
# cociente. Así que el frontmatter se compone a mano.


_INICIAL_ESPECIAL = set("-?:,[]{}#&*!|>'\"%@`")


def _escalar(valor: Any) -> str:
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, float):
        return f"{valor:.1f}" if valor.is_integer() else f"{valor:.10g}"
    if isinstance(valor, int):
        return str(valor)
    texto = str(valor)
    if not texto:
        return '""'
    if texto[0] in _INICIAL_ESPECIAL or ": " in texto or " #" in texto or texto != texto.strip():
        return '"' + texto.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return texto


def _plano(texto: str) -> str:
    return " ".join(str(texto).split())


class Bloque:
    """Acumulador de líneas YAML con sangría explícita."""

    def __init__(self) -> None:
        self.lineas: list[str] = []

    def crudo(self, texto: str = "") -> None:
        self.lineas.append(texto)

    def comentario(self, texto: str, sangria: int = 0) -> None:
        prefijo = " " * sangria + "# "
        for linea in textwrap.wrap(_plano(texto), width=ANCHO - sangria) or [""]:
            self.lineas.append(prefijo + linea)

    def campo(self, clave: str, valor: Any, sangria: int = 0, guion: bool = False) -> None:
        marca = "- " if guion else ""
        self.lineas.append(f"{' ' * sangria}{marca}{clave}: {_escalar(valor)}")

    def prosa(self, clave: str, texto: str, sangria: int = 0, guion: bool = False) -> None:
        """Escalar plegado `>-`, que es como el índice guarda el texto largo."""
        marca = "- " if guion else ""
        self.lineas.append(f"{' ' * sangria}{marca}{clave}: >-")
        cuerpo = textwrap.fill(_plano(texto), width=ANCHO - sangria - 2)
        for linea in cuerpo.splitlines():
            self.lineas.append(" " * (sangria + 2) + linea)

    def texto(self) -> str:
        return "\n".join(self.lineas)


# ── Traducción ────────────────────────────────────────────────────────────


def cita(ref_id: str, indice: Indice, informe: Informe, donde: str) -> str:
    """Convierte 'pmid:24938565' en una cita que se puede leer.

    El frontmatter de una skill exige `fuente` en prosa para todo LR que no
    sea 1.0: un cociente sin procedencia es un número inventado con formato
    científico. Aquí la procedencia se compone del registro verificado, no
    de memoria.
    """
    registro = indice.referencias.get(ref_id)
    if not registro:
        informe.pendiente(donde, f"cita «{ref_id}», que no está en referencias/")
        return ref_id

    autores = registro.get("autores") or []
    firma = str(autores[0]) if autores else ""
    if len(autores) > 1:
        firma += " et al."

    revista = " ".join(
        str(x) for x in (registro.get("publicacion"), registro.get("anio")) if x
    )
    if registro.get("volumen"):
        revista += f";{registro['volumen']}"
    if registro.get("paginas"):
        revista += f":{registro['paginas']}"

    identificadores = registro.get("identificadores") or {}
    partes = [p for p in (firma, revista) if p]
    if identificadores.get("pmid"):
        partes.append(f"PMID {identificadores['pmid']}")
    if identificadores.get("doi"):
        partes.append(f"doi:{identificadores['doi']}")

    verificacion = registro.get("verificacion") or {}
    if not verificacion.get("pubmed"):
        informe.pendiente(donde, f"«{ref_id}» no está verificada contra PubMed")
    if verificacion.get("errata"):
        informe.pendiente(
            donde,
            f"«{ref_id}» tiene errata publicada ({verificacion['errata']}): "
            f"comprueba la cifra contra la corrección antes de trasladarla",
        )

    return ". ".join(p.rstrip(".") for p in partes if p) + "."


def _lr(bloque: Any) -> dict[str, Any]:
    """Normaliza un LR del índice, que puede venir suelto o con contexto."""
    if isinstance(bloque, dict):
        return bloque
    if isinstance(bloque, (int, float)):
        return {"valor": bloque}
    return {}


def _valor_utilizable(
    lr: dict, campo: str, concepto: str, informe: Informe
) -> float | None:
    """El número que se puede copiar, o nada y un pendiente explicando por qué."""
    valor = lr.get("valor")

    if valor is None and lr.get("rango"):
        rango = lr["rango"]
        informe.pendiente(
            concepto,
            f"{campo} publicado como rango {rango} entre estudios. El índice no "
            f"promedia y este conversor tampoco: elige el valor que vas a usar y "
            f"déjalo escrito en `fuente`"
            + (f". La fuente anota: {_plano(lr['nota'])}" if lr.get("nota") else ""),
        )
        return None

    if valor is None:
        informe.pendiente(concepto, f"{campo} sin «valor» ni «rango»")
        return None

    if not isinstance(valor, (int, float)):
        informe.pendiente(concepto, f"{campo} no es un número: {valor!r}")
        return None

    if valor <= 0:
        informe.pendiente(
            concepto,
            f"{campo} = {valor}. Un cociente de 0 sale de una sensibilidad del "
            f"100% en la serie estudiada, no de una imposibilidad; copiarlo "
            f"haría el posterior exactamente 0. Decide qué valor entra"
            + (f". La fuente anota: {_plano(lr['nota'])}" if lr.get("nota") else ""),
        )
        return None

    if valor > 100:
        informe.pendiente(
            concepto,
            f"{campo} = {valor}: por encima de 100 casi siempre es una serie "
            f"diminuta o una errata. Se traslada, pero compruébalo",
        )

    return float(valor)


def _fuente(
    bloques: list[tuple[str, dict]],
    arista: dict,
    indice: Indice,
    informe: Informe,
    donde: str,
) -> str:
    """La prosa que acompaña al cociente en la skill.

    Un signo puede traer LR+ y LR− medidos por separado, cada uno con su
    intervalo, su umbral y a veces su fuente. La skill sólo tiene un campo
    `fuente`, así que se etiqueta cada mitad en vez de quedarse con la
    primera y perder el intervalo de la otra.
    """
    partes: list[str] = []

    referencias: list[str] = []
    for _, lr in [*bloques, ("", arista)]:
        referencia = lr.get("ref")
        if referencia and str(referencia) not in referencias:
            referencias.append(str(referencia))
    partes += [cita(r, indice, informe, donde) for r in referencias]

    etiquetar = len(bloques) > 1
    for etiqueta, lr in bloques:
        detalle: list[str] = []
        if lr.get("ic95"):
            detalle.append(f"IC95% {lr['ic95']}")
        if lr.get("umbral"):
            detalle.append(f"umbral: {_plano(lr['umbral'])}")
        if detalle:
            prefijo = f"{etiqueta} " if etiquetar else ""
            partes.append(prefijo + "; ".join(detalle) + ".")

    poblacion = next(
        (lr["poblacion"] for _, lr in bloques if lr.get("poblacion")),
        arista.get("poblacion"),
    )
    if poblacion:
        partes.append(f"Población: {_plano(poblacion)}.")

    for _, lr in bloques:
        if lr.get("nota"):
            partes.append(_frase(lr["nota"]))
    for origen in (*(lr for _, lr in bloques), arista):
        if origen.get("decision"):
            partes.append(_frase(origen["decision"]))

    return " ".join(dict.fromkeys(partes))


def _comentar_contexto(
    salida: "Bloque", arista: dict, indice: Indice, informe: Informe, termino: str
) -> None:
    """Lo que rodea a una arista sin cociente y no cabe en ningún campo.

    Una arista que no aporta LR sigue trayendo información que decide: en qué
    población se midió, qué sensibilidad se publicó, y la advertencia de que
    su ausencia no tranquiliza. Va en comentarios porque el motor no la lee,
    pero quien revise el protocolo sí.
    """
    if arista.get("poblacion"):
        salida.comentario(f"población: {_plano(arista['poblacion'])}", sangria=4)
    for clave in ("sensibilidad", "especificidad"):
        if arista.get(clave) is not None:
            salida.comentario(f"{clave} publicada: {arista[clave]}", sangria=4)
    if arista.get("advertencia"):
        salida.comentario(f"ADVERTENCIA: {_plano(arista['advertencia'])}", sangria=4)
    if arista.get("nota"):
        salida.comentario(_plano(arista["nota"]), sangria=4)
    if arista.get("ref"):
        salida.comentario(cita(str(arista["ref"]), indice, informe, termino), sangria=4)


def _frase(texto: Any) -> str:
    """El índice escribe las notas en minúscula y sin punto; aquí son prosa."""
    limpio = _plano(texto)
    if not limpio:
        return ""
    return limpio[0].upper() + limpio[1:].rstrip(".") + "."


def _decidir_efecto(
    arista: dict, por_defecto: str, termino: str, informe: Informe
) -> tuple[str, str] | None:
    """Qué `efecto` y `dispara_si` se emiten, o None para no emitir la arista.

    LA DIRECCIÓN DE LA NEGATIVA, QUE ES TODO EL ASUNTO
    --------------------------------------------------
    Una versión anterior degradaba a `apoya` la arista cuyo efecto no podía
    honrarse. Eso no es conservador: **invierte el signo**. `veredicto.py`
    cuenta los signos con `efecto == "apoya"`, así que una anemia declarada
    como advertencia pasaba a **sumar a favor** de la enfermedad contra la que
    avisaba, y una exclusión absoluta sin `motivo` se convertía en un criterio
    de apoyo.

    La negativa correcta es **no meter la arista en el bloque estructurado**.
    Eso deja exactamente el comportamiento anterior al ciclo —el hallazgo sigue
    en la prosa del cuerpo, que el modelo lee— y por construcción no puede
    empujar el veredicto en ninguna dirección. Es el mismo criterio del PR #10:
    lo que no se puede honrar cae al valor más estricto, no al más permisivo.

    Un matiz que importa: sólo se aplica cuando la arista **declaró** algo que
    no puede honrarse. Una arista de `signos` sin clave `efecto` es `apoya` por
    declaración del esquema, no por respaldo, y se emite como siempre.
    """
    efecto = str(arista.get("efecto") or por_defecto)
    sostiene = str(arista.get("sostiene") or "")
    dispara = str(arista.get("dispara_si") or "presente")

    if efecto not in EFECTOS:
        informe.pendiente(
            termino,
            f"efecto «{efecto}» que holonmed no conoce: la arista no entra en el "
            f"bloque estructurado. Emitirla como apoyo invertiría su signo",
        )
        return None

    if efecto == "bandera_roja" and sostiene not in SOSTIENE_AUTORIZA_BANDERA:
        # Misma regla que build.py: la pertenencia a una lista no autoriza una
        # bandera. Enumerar la negativa es la mitad del arreglo; una negativa
        # silenciosa sería el fallo.
        informe.pendiente(
            termino,
            f"declarada como bandera roja pero la sostiene «{sostiene or 'nada'}», "
            f"que no lo autoriza (hace falta "
            f"{' o '.join(SOSTIENE_AUTORIZA_BANDERA)}): no entra en el bloque "
            f"estructurado. Se queda en la prosa, donde ya estaba",
        )
        return None

    if efecto == "excluye" and sostiene == "mecanismo" and not arista.get("motivo"):
        informe.pendiente(
            termino,
            "sostiene «mecanismo» sin «motivo»: la arista no entra en el bloque "
            "estructurado. `mecanismo` es el valor que hay que justificar por "
            "escrito, no la puerta trasera",
        )
        return None

    if dispara not in POLARIDADES:
        # Una bandera que debía dispararse por ausencia y se emite por
        # presencia dispara justo al revés. Tampoco se emite.
        informe.pendiente(
            termino,
            f"dispara_si «{dispara}» desconocido: la arista no entra en el bloque "
            f"estructurado, porque emitirla como «presente» podría invertir cuándo "
            f"dispara",
        )
        return None

    return efecto, dispara


def signos(condicion: dict, indice: Indice, informe: Informe) -> tuple[Bloque, list[str]]:
    """Traduce las aristas concepto→condición al bloque `signos`."""
    salida = Bloque()
    salida.crudo("# Cada LR conserva la procedencia con la que entró en el índice.")
    salida.crudo("# Un cociente sin fuente es un número inventado con formato científico.")
    salida.crudo("signos:")

    usados: list[str] = []
    primero = True

    # Las DOS listas. `signos_de_alarma` se emitía sólo a la prosa del cuerpo:
    # el modelo las leía y `veredicto.py` no, de modo que una bandera curada en
    # el índice no llegaba a contarse. La prosa se conserva —son dos
    # consumidores, no uno migrando al otro—; lo que se añade es el bloque
    # estructurado.
    entradas = [(a, "apoya") for a in (condicion.get("signos") or [])]
    entradas += [(a, "bandera_roja") for a in (condicion.get("signos_de_alarma") or [])]

    for arista, efecto_por_defecto in entradas:
        codigo = str(arista.get("concepto") or "")
        concepto = indice.concepto(codigo)
        if not concepto:
            informe.pendiente(codigo or "?", "la arista apunta a un concepto que no existe")
            continue

        termino = str(concepto.get("termino") or codigo)

        # SE DECIDE ANTES DE ESCRIBIR NADA. Si el efecto declarado no puede
        # honrarse, la arista no entra en el bloque estructurado —ni siquiera
        # su `nombre`—, porque una arista a medio emitir se lee como `apoya`
        # por defecto y eso invierte su signo.
        decision = _decidir_efecto(arista, efecto_por_defecto, termino, informe)
        if decision is None:
            continue
        efecto, dispara = decision

        usados.append(codigo)

        if not primero:
            salida.crudo()
        primero = False

        rol = str(arista.get("rol") or "apoyo")
        if rol not in ROLES:
            informe.pendiente(termino, f"rol «{rol}» que holonmed no conoce; se leerá como «apoyo»")

        salida.campo("nombre", termino, sangria=2, guion=True)

        codigos = {"holonmed": codigo}
        for sistema, valor in (concepto.get("codigos") or {}).items():
            if valor:
                # El índice usa `icd10`; el frontmatter también.
                codigos[str(sistema)] = str(valor)
        pares = ", ".join(f'{k}: "{v}"' for k, v in codigos.items())
        salida.crudo(f"    codigos: {{ {pares} }}")
        salida.campo("rol", rol, sangria=4)

        # `efecto` y `dispara_si`: el eje que dice qué papel juega el hallazgo
        # dentro de un criterio contado, ortogonal al rol. Ya vienen decididos
        # por `_decidir_efecto`; aquí sólo se escriben los que no son el valor
        # por defecto del frontmatter.
        if efecto != "apoya":
            salida.campo("efecto", efecto, sangria=4)
        if dispara != "presente":
            salida.campo("dispara_si", dispara, sangria=4)

        estado = str(arista.get("estado_lr") or "")
        positivo = _lr(arista.get("lr_positivo"))
        negativo = _lr(arista.get("lr_negativo"))

        if estado == "sin_efecto":
            # `sin_efecto` y `no_medido` no son lo mismo, y ésta es la única
            # traducción que preserva la diferencia: 1.0 deja el hallazgo en
            # el protocolo sin mover la probabilidad. Sin cociente, en cambio,
            # el motor lo ignora.
            salida.campo("lr", 1.0, sangria=4)
            motivo = _plano(arista.get("motivo") or "")
            salida.comentario(
                "sin_efecto en el índice: se reconoce el término pero no desplaza "
                "la probabilidad" + (f". {motivo[:1].upper()}{motivo[1:]}" if motivo else ""),
                sangria=4,
            )
            _comentar_contexto(salida, arista, indice, informe, termino)
        elif positivo or negativo:
            valor_positivo = (
                _valor_utilizable(positivo, "LR+", termino, informe) if positivo else None
            )
            valor_negativo = (
                _valor_utilizable(negativo, "LR−", termino, informe) if negativo else None
            )
            if valor_positivo is not None:
                salida.campo("lr", valor_positivo, sangria=4)
            if valor_negativo is not None:
                salida.campo("lr_negativo", valor_negativo, sangria=4)

            emitidos = [
                (etiqueta, lr)
                for etiqueta, lr, valor in (
                    ("LR+", positivo, valor_positivo),
                    ("LR−", negativo, valor_negativo),
                )
                if valor is not None
            ]
            # Si no se traslada ninguno, la procedencia se comenta igual: es
            # lo que necesita quien vaya a decidir qué número entra.
            texto = _fuente(
                emitidos or [(e, lr) for e, lr in (("LR+", positivo), ("LR−", negativo)) if lr],
                arista, indice, informe, termino,
            )
            if valor_positivo is None and valor_negativo is None:
                salida.comentario(
                    "el índice trae cociente pero no se traslada ninguno todavía; "
                    "ver el informe.", sangria=4,
                )
                salida.comentario(texto, sangria=4)
            elif texto:
                salida.prosa("fuente", texto, sangria=4)
            else:
                informe.pendiente(termino, "el LR se traslada sin fuente citable")
        else:
            # La relación existe aunque nadie la haya cuantificado. El término
            # sigue reconociéndose; simplemente no entra en el cálculo.
            motivo = _plano(arista.get("motivo") or "") or "el índice no publica cociente"
            salida.comentario(f"{estado or 'sin cociente'}: {motivo}", sangria=4)
            _comentar_contexto(salida, arista, indice, informe, termino)
            if estado == "no_medido":
                informe.rutina(
                    "aristas sin cociente publicado: el término se reconoce pero no "
                    "entra en el cálculo",
                    termino,
                )

        sobrantes = sorted(set(arista) - CLAVES_ARISTA)
        for clave in sorted(set(arista) & set(CONOCIDAS_NO_EMITIDAS)):
            informe.rutina(
                f"claves que el índice trae y el frontmatter no guarda: {clave}",
                termino,
            )
        if sobrantes:
            informe.pendiente(
                termino,
                "la fuente trae "
                + ", ".join(f"«{c}»" for c in sobrantes)
                + " y holonmed no tiene dónde guardarlo: decide si va a la prosa "
                  "del cuerpo o se pierde",
            )

    return salida, usados



def nucleo_y_balance(
    condicion: dict, indice: Indice, informe: Informe
) -> Bloque | None:
    """Emite `nucleo` y `balance`, o se niega y enumera por qué.

    Dos traducciones que no son evidentes:

    · La cita cambia de nombre. El índice guarda el identificador (`ref`), la
      skill guarda la cita en prosa (`fuente`). Emitir `ref:` dentro del balance
      de una skill no falla —el parseador lo descarta por no ser un dict— pero
      pierde la cita entera sin decir nada.

    · Los códigos del núcleo se traducen a TÉRMINOS PREFERIDOS, porque
      `Nucleo.satisfecho()` empareja por subcadena contra términos, no contra
      códigos.

    Y una negativa que hay que razonar: si un concepto del núcleo no resuelve,
    NO se emite tampoco el balance. Emitir el balance solo no es conservador,
    es más permisivo: el núcleo es justamente lo que impide que un diagnóstico
    alcance «probable» sobre un paciente del que no consta nada.
    """
    nucleo = condicion.get("nucleo")
    balance = condicion.get("balance")
    if not isinstance(nucleo, dict) and not isinstance(balance, dict):
        return None

    salida = Bloque()
    emitir_balance = True

    if isinstance(nucleo, dict):
        terminos: dict[str, list[str]] = {}
        roto = False
        for campo in ("requiere", "y_al_menos_uno_de"):
            terminos[campo] = []
            for codigo in (nucleo.get(campo) or []):
                concepto = indice.concepto(str(codigo))
                if not concepto:
                    informe.pendiente(
                        str(codigo),
                        "concepto del núcleo que no resuelve: no se emite el núcleo "
                        "NI el balance. Emitir el balance sin su núcleo sería más "
                        "permisivo, no más conservador",
                    )
                    roto = True
                    continue
                terminos[campo].append(str(concepto.get("termino") or codigo))
        if roto:
            emitir_balance = False
        else:
            cita_nucleo = cita(str(nucleo.get("ref") or ""), indice, informe, "el núcleo")
            salida.crudo("# Sin el núcleo el criterio ni siquiera se aplica: no es una")
            salida.crudo("# exclusión, es que la pregunta todavía no se puede hacer.")
            salida.crudo("nucleo:")
            for campo, etiqueta in (("requiere", "requiere"),
                                    ("y_al_menos_uno_de", "y_al_menos_uno_de")):
                if terminos[campo]:
                    lista = ", ".join(f'"{t}"' for t in terminos[campo])
                    salida.crudo(f"  {etiqueta}: [{lista}]")
            if cita_nucleo:
                salida.prosa("fuente", cita_nucleo, sangria=2)
            else:
                informe.pendiente("el núcleo", "se emite sin fuente citable")

    if isinstance(balance, dict) and emitir_balance:
        cita_balance = cita(str(balance.get("ref") or ""), indice, informe, "el balance")
        if not cita_balance:
            informe.pendiente(
                "el balance",
                "sin fuente citable: los enteros los fija el panel que redacta el "
                "criterio y el sistema no los deriva, así que no se emite",
            )
        else:
            if salida.lineas:
                salida.crudo()
            salida.crudo("# Los niveles se evalúan EN ORDEN y gana el primero que se")
            salida.crudo("# satisface: invertirlos rebajaría el grado en silencio.")
            salida.crudo("balance:")
            salida.prosa("fuente", cita_balance, sangria=2)
            for nombre, regla in balance.items():
                # Lista blanca POSITIVA, la misma que usa el parseador. Filtrar
                # por «lo que no parezca nivel» dejaba pasar cualquier clave con
                # diccionario —`poblacion: {...}`— y la escribía en el borrador
                # como un grado de certeza. El parseador la rechaza después,
                # pero quien revisa el borrador la lee como legítima.
                if not isinstance(regla, dict) or not (set(regla) & CAMPOS_NIVEL):
                    if nombre not in ("ref", "nota", "fuente"):
                        informe.pendiente(
                            "el balance",
                            f"«{nombre}» no declara ninguno de "
                            f"{', '.join(sorted(CAMPOS_NIVEL))}: no se emite como "
                            f"nivel de certeza",
                        )
                    continue
                pares = ", ".join(f"{k}: {v}" for k, v in regla.items())
                salida.crudo(f"  {nombre}: {{ {pares} }}")

    return salida if salida.lineas else None


def laboratorio(codigos: list[str], indice: Indice, informe: Informe) -> Bloque | None:
    """Cortes de laboratorio, tomados del `umbral` de cada concepto.

    Es la mitad del protocolo que convierte una cifra en un concepto
    clínico. Sin ella el modelo se inventa el punto de corte: al auditar
    «lipasa 890» escribió «>3x el límite normal (aprox. 250-300)» cuando el
    protocolo declara 60.
    """
    criterios = [c for c in codigos if (indice.concepto(c).get("umbral") or {}).get("parametro")]
    if not criterios:
        return None

    salida = Bloque()
    salida.crudo("laboratorio:")
    for i, codigo in enumerate(criterios):
        concepto = indice.concepto(codigo)
        umbral = concepto["umbral"]
        termino = _termino_con_multiplicador(concepto)

        if i:
            salida.crudo()
        salida.campo("parametro", str(umbral["parametro"]), sangria=2, guion=True)

        alto = umbral.get("corte_superior")
        bajo = umbral.get("corte_inferior")
        if alto is not None:
            salida.campo("corte_superior", alto, sangria=4)
        if bajo is not None:
            salida.campo("corte_inferior", bajo, sangria=4)
        if umbral.get("multiplicador"):
            salida.campo("multiplicador", umbral["multiplicador"], sangria=4)

        direccion = str(umbral.get("direccion") or ("alto" if alto is not None else "bajo"))
        salida.campo(
            "termino_si_alto" if direccion == "alto" else "termino_si_bajo",
            termino, sangria=4,
        )

        pares = [f'holonmed: "{codigo}"']
        for sistema, valor in (concepto.get("codigos") or {}).items():
            if valor:
                pares.append(f'{sistema}: "{valor}"')
        salida.crudo("    codigos: { " + ", ".join(pares) + " }")

        if not umbral.get("ref"):
            informe.rutina(
                "cortes que viajan sin procedencia en el índice (`umbral.ref: null`)",
                f"{umbral['parametro']} ({termino})",
            )

    return salida


def _termino_con_multiplicador(concepto: dict) -> str:
    """«Hiperlipasemia» o «Hiperlipasemia (>3x)», según el umbral.

    Cuando el corte lleva multiplicador, el término que el protocolo extrae
    no es el genérico: la lipasa elevada y la elevada más de tres veces son
    hallazgos distintos. El índice guarda esa variante como sinónimo.
    """
    termino = str(concepto.get("termino") or "")
    multiplicador = (concepto.get("umbral") or {}).get("multiplicador")
    if not multiplicador:
        return termino

    patron = re.compile(rf">\s*{multiplicador:g}\s*x", re.IGNORECASE)
    for sinonimo in concepto.get("sinonimos") or []:
        texto = str(sinonimo)
        if patron.search(texto) and termino.lower() in texto.lower():
            return texto[0].upper() + texto[1:]
    return f"{termino} (>{multiplicador:g}x)"


def clasificacion(condicion: dict, indice: Indice, informe: Informe) -> Bloque | None:
    """Las `reglas` del índice, propuestas como bloque `clasificacion`.

    Va comentado a propósito. Una regla del índice dice qué componentes
    tiene y de dónde sale; el bloque de holonmed exige además cuántos hacen
    falta y qué término acuña cuando se cumplen, y eso es una decisión
    clínica que no está escrita en ninguna parte del origen.
    """
    reglas = condicion.get("reglas") or []
    if not reglas:
        return None

    salida = Bloque()
    salida.crudo("# ── Propuesta de clasificación, sin activar ──────────────────────────")
    salida.crudo("# El índice declara estas reglas con sus componentes y su fuente. Para")
    salida.crudo("# activarlas hay que decidir dos cosas que el origen no dice: cuántos")
    salida.crudo("# criterios se exigen y qué término se acuña al cumplirse. Descoméntalo")
    salida.crudo("# cuando lo hayas resuelto.")
    salida.crudo("#")
    salida.crudo("# clasificacion:")

    primera = reglas[0]
    salida.crudo(f"#   nombre: {_plano(primera.get('nombre') or '')}")
    if primera.get("ref"):
        salida.crudo(
            f"#   fuente: {cita(str(primera['ref']), indice, informe, 'clasificacion')}"
        )
    salida.crudo("#   requiere: <cuántos criterios hacen falta>")
    salida.crudo("#   criterios:")
    for regla in reglas:
        componentes = ", ".join(f'"{c}"' for c in (regla.get("componentes") or []))
        salida.crudo(f"#     - nombre: {_plano(regla.get('nombre') or '')}")
        salida.crudo("#       rol: <manifestacion | prueba_sensible | prueba_especifica>")
        salida.crudo(f"#       satisface_si: [{componentes}]")
        for codigo in regla.get("componentes") or []:
            salida.crudo(f"#         # {codigo}  {indice.termino(str(codigo))}")
    salida.crudo("#   produce:")
    salida.crudo(f"#     termino: {condicion.get('termino')}")
    salida.crudo(f"#     codigos: {{ holonmed: \"{condicion.get('id')}\" }}")
    salida.crudo("#     semantica: trastorno")

    informe.pendiente(
        "clasificacion",
        f"el índice declara {len(reglas)} regla(s) combinada(s). El bloque va "
        f"comentado: decide `requiere` y `produce` antes de activarlo",
    )
    return salida


def ramas(codigos: list[str], indice: Indice) -> list[str]:
    """Los padres de los conceptos enlazados, que son el ámbito del grafo."""
    salida: list[str] = []
    for codigo in codigos:
        # La raíz del árbol no es un ámbito: cubre el índice entero y haría
        # que el protocolo se ofreciera para cualquier paciente. Cuando el
        # padre es la raíz, la rama útil es el concepto mismo.
        padre = str(indice.concepto(codigo).get("padre") or "")
        if not padre or indice.concepto(padre).get("semantica") == "raiz":
            padre = codigo
        if padre not in salida:
            salida.append(padre)
    return salida


def ambito_grafo(codigos: list[str], indice: Indice) -> Bloque | None:
    """Las ramas del grafo sobre las que actúa el protocolo.

    Es lo que permite preguntar qué protocolos aplican a un paciente por los
    hallazgos que ya tiene, en vez de que lo decida el triaje con el texto de
    hoy.
    """
    ramas_ = ramas(codigos, indice)
    if not ramas_:
        return None

    salida = Bloque()
    salida.crudo("# Ramas del grafo sobre las que actúa este protocolo: los padres de")
    salida.crudo("# los conceptos enlazados. Poda las que sean demasiado generales.")
    salida.crudo("ambito_grafo:")
    ancho = max(len(r) for r in ramas_)
    for rama in sorted(ramas_):
        salida.crudo(f"  - {rama:<{ancho}}   # {indice.termino(rama)}")
    return salida


def bayes(condicion: dict, indice: Indice, informe: Informe) -> Bloque:
    salida = Bloque()
    salida.crudo("modelo_bayesiano:")

    base = condicion.get("probabilidad_base")
    valor = base.get("valor") if isinstance(base, dict) else base

    if valor is None:
        salida.comentario(
            "El índice no publica prevalencia para esta condición. Sin "
            "probabilidad base el motor no arranca: pon la de tu población.",
            sangria=2,
        )
        salida.campo("probabilidad_base", 0.0, sangria=2)
        informe.pendiente(
            "modelo_bayesiano",
            "el índice no publica prevalencia: queda en 0.0 y el modelo bayesiano "
            "no se activará hasta que pongas la de tu población",
        )
    else:
        salida.comentario(
            "Prevalencia en la población que atiendes, no en la literatura "
            "mundial. El valor del índice queda abajo como referencia.",
            sangria=2,
        )
        salida.campo("probabilidad_base", valor, sangria=2)
        if isinstance(base, dict):
            if base.get("poblacion"):
                salida.comentario(f"medida en: {_plano(base['poblacion'])}", sangria=2)
            if base.get("ref"):
                salida.comentario(
                    cita(str(base["ref"]), indice, informe, "probabilidad_base"),
                    sangria=2,
                )
        informe.pendiente(
            "modelo_bayesiano",
            f"probabilidad_base {valor} es la de la literatura. Ajústala a la "
            f"prevalencia de tu servicio o el posterior saldrá sesgado",
        )

    salida.crudo()
    salida.comentario(
        "OJO: el emparejamiento es por SUBCADENA LITERAL. Hay que declarar las "
        "variantes que un clínico escribe de verdad — «bebedor de riesgo» no "
        "contiene «alcohol», y sin la variante el factor nunca se aplica.",
        sangria=2,
    )
    con_peso: list[tuple[str, float, dict]] = []
    sin_peso: list[tuple[str, dict]] = []
    for factor in condicion.get("factores_riesgo") or []:
        if isinstance(factor, dict):
            nombre = _plano(
                factor.get("nombre") or factor.get("factor") or factor.get("termino") or ""
            )
            peso = factor.get("valor") or factor.get("lr") or factor.get("peso")
        else:
            nombre, peso = _plano(factor), None
        if not nombre:
            continue
        detalle = factor if isinstance(factor, dict) else {}
        if isinstance(peso, (int, float)):
            con_peso.append((nombre, float(peso), detalle))
        else:
            sin_peso.append((nombre, detalle))

    # Un factor que el índice describe pero no cuantifica no puede entrar: el
    # bloque es término→multiplicador y ponerle un número sería inventarlo.
    for nombre, detalle in sin_peso:
        salida.comentario(f"El índice declara «{nombre}» sin peso.", sangria=2)
        if detalle.get("nota"):
            salida.comentario(f"nota: {_plano(detalle['nota'])}", sangria=2)
        if detalle.get("ref"):
            salida.comentario(cita(str(detalle["ref"]), indice, informe, nombre), sangria=2)
        informe.pendiente(
            "factores_riesgo",
            f"«{nombre}» viene del índice sin multiplicador, así que no entra en "
            f"el bloque. Si le asignas uno, que salga de una fuente",
        )

    if con_peso:
        salida.crudo("  factores_riesgo:")
        for nombre, peso, detalle in con_peso:
            salida.campo(nombre.lower(), peso, sangria=4)
            if detalle.get("ref"):
                salida.comentario(
                    cita(str(detalle["ref"]), indice, informe, nombre), sangria=4
                )
        informe.pendiente(
            "factores_riesgo",
            "añade las variantes de escritura de cada factor: el emparejamiento "
            "es literal y sin ellas el factor no se aplica nunca",
        )
    else:
        salida.crudo("  factores_riesgo: {}")

    if not con_peso and not sin_peso:
        informe.pendiente(
            "factores_riesgo",
            "el índice no declara ninguno. Si tu población tiene factores con "
            "peso conocido, añádelos con todas sus variantes de escritura",
        )

    return salida


# ── Cuerpo en Markdown ────────────────────────────────────────────────────


def cuerpo(condicion: dict, codigos: list[str], indice: Indice, informe: Informe) -> str:
    """La prosa que entra en el prompt.

    El índice no la tiene y no la tendrá: guarda hechos. Lo que sí se puede
    trasladar son los hechos que el modelo necesita ver en prosa —los signos
    de alarma, las escalas por tramos, la conclusión de la fuente— y el
    esqueleto de todo lo demás.
    """
    termino = str(condicion.get("termino") or "")
    partes: list[str] = [f"# PROTOCOLO DE {termino.upper()}", ""]

    partes += [
        "ROL: <!-- especialidad y postura: «cardiólogo experto, basado en "
        "evidencia» -->",
        "",
        "## Contexto fisiopatológico",
        "",
        "<!-- El índice no guarda prosa. Estas tres líneas son las que hacen que",
        "     el modelo reconozca el cuadro y no sólo sus términos. -->",
        "",
        "- **Dónde**: <!-- órgano, territorio, compartimento -->",
        "- **Cómo**: <!-- mecanismo -->",
        "- **Por qué**: <!-- causas frecuentes -->",
        "",
        "## Instrucciones de extracción",
        "",
        "1. Analiza los signos vitales, la exploración y el texto libre.",
    ]

    ejemplos = _ejemplos_de_corte(codigos, indice)
    if ejemplos:
        partes += [
            "2. **Interpreta los valores numéricos** con los cortes declarados",
            "   arriba. Extrae el hallazgo clínico, nunca la cifra suelta:",
        ]
        partes += [f"   - «{cifra}» → *{nombre}*" for cifra, nombre in ejemplos]
    else:
        partes.append("2. Extrae el hallazgo clínico, nunca la cifra suelta.")
    partes += [
        "3. No infieras lo que no está escrito. Un dato que falta se pide, no",
        "   se supone.",
        "",
    ]

    alarma = condicion.get("signos_de_alarma") or []
    if alarma:
        partes += [
            "## Signos de alarma",
            "",
            "Apuntan fuera de este cuadro y obligan a estudiar antes de etiquetar.",
            "Si aparece alguno, dilo explícitamente en la valoración:",
            "",
        ]
        for signo in alarma:
            codigo = str(signo.get("concepto") or "")
            partes.append(f"- **{indice.termino(codigo)}** ({codigo})")
        partes.append("")

    escalas = condicion.get("escalas") or []
    if escalas:
        partes += [
            "## Escalas",
            "",
            "No son signos: combinan varios elementos y se leen por tramos.",
            "holonmed no las calcula — si el texto trae la puntuación, úsala tal",
            "como viene y aplica el tramo que corresponda.",
            "",
        ]
        for escala in escalas:
            partes.append(f"### {_plano(escala.get('nombre') or '')}")
            if escala.get("componentes_declarados"):
                partes += ["", f"Componentes: {_plano(escala['componentes_declarados'])}."]
            partes.append("")
            for tramo in escala.get("tramos") or []:
                cocientes = []
                if tramo.get("lr_positivo"):
                    cocientes.append(f"LR+ {tramo['lr_positivo']}")
                if tramo.get("lr_negativo"):
                    cocientes.append(f"LR− {tramo['lr_negativo']}")
                if tramo.get("ic95"):
                    cocientes.append(f"IC95% {tramo['ic95']}")
                partes.append(
                    f"- **{_plano(tramo.get('rango') or '')}**: " + ", ".join(cocientes)
                )
            if escala.get("decision"):
                partes += ["", _plano(escala["decision"]).capitalize() + "."]
            partes.append("")
        informe.pendiente(
            "escalas",
            f"el índice trae {len(escalas)} escala(s) con cocientes por tramo. "
            f"holonmed no tiene un slot estructurado para ellas: van al cuerpo, "
            f"donde las lee el modelo pero no el motor bayesiano",
        )

    if condicion.get("conclusion_de_la_fuente"):
        partes += [
            "## Lo que la fuente concluye",
            "",
            textwrap.fill(_plano(condicion["conclusion_de_la_fuente"]), width=ANCHO),
            "",
        ]

    partes += [
        "## Formato de salida",
        "",
        "<!-- Cópialo del protocolo que más se le parezca de los ya escritos.",
        "     Un formato distinto por protocolo rompe el pipeline de registro. -->",
        "",
    ]
    return "\n".join(partes)


def _ejemplos_de_corte(codigos: list[str], indice: Indice) -> list[tuple[str, str]]:
    """Ejemplos «cifra → hallazgo» derivados de los cortes declarados.

    Son aritmética sobre el propio umbral, no valores clínicos inventados.
    """
    ejemplos: list[tuple[str, str]] = []
    for codigo in codigos:
        umbral = indice.concepto(codigo).get("umbral") or {}
        parametro = umbral.get("parametro")
        if not parametro or len(ejemplos) >= 3:
            continue
        termino = _termino_con_multiplicador(indice.concepto(codigo))
        multiplicador = umbral.get("multiplicador") or 1
        if umbral.get("corte_superior") is not None:
            cifra = umbral["corte_superior"] * multiplicador * 1.3
            ejemplos.append((f"{parametro} {cifra:,.0f}", termino))
        elif umbral.get("corte_inferior") is not None:
            cifra = umbral["corte_inferior"] * 0.85
            ejemplos.append((f"{parametro} {cifra:,.1f}", termino))
    return ejemplos


# ── Contraste con el vocabulario de holonmed ──────────────────────────────


def vocabulario_local() -> tuple[set[str], Path]:
    """Códigos que holonmed reconoce hoy, sin levantar la base de datos."""
    if not RUTA_SEMILLA.exists():
        return set(), RUTA_SEMILLA
    datos = json.loads(RUTA_SEMILLA.read_text(encoding="utf-8"))
    return {str(c["codigo"]) for c in datos.get("conceptos", []) if c.get("codigo")}, RUTA_SEMILLA


def fragmento_vocabulario(
    codigos: list[str], condicion: dict, indice: Indice, conocidos: set[str]
) -> list[dict]:
    """Los conceptos que el protocolo usa y holonmed todavía no conoce.

    Un código que no está en el vocabulario no falla: produce un infón sin
    linaje ni mapeo, en silencio. Traducirlos es mecánico —el índice guarda
    justo los campos que la semilla necesita— así que se traducen aquí y el
    humano decide si los mezcla.
    """
    faltan: list[str] = []
    pendientes = list(codigos)
    while pendientes:
        codigo = pendientes.pop(0)
        if codigo in conocidos or codigo in faltan:
            continue
        concepto = indice.concepto(codigo)
        if not concepto:
            continue
        faltan.append(codigo)
        # Sin su padre, el concepto entra desconectado del grafo y deja de
        # responder a la pregunta de qué protocolos aplican a un paciente.
        if concepto.get("padre"):
            pendientes.append(str(concepto["padre"]))

    entradas: list[dict] = []
    for codigo in faltan:
        concepto = indice.concepto(codigo)
        entrada: dict[str, Any] = {
            "codigo": codigo,
            "termino": str(concepto.get("termino") or ""),
            "semantica": str(concepto.get("semantica") or "hallazgo"),
        }
        if concepto.get("padre"):
            entrada["padre"] = str(concepto["padre"])
        if concepto.get("sinonimos"):
            entrada["sinonimos"] = [str(s) for s in concepto["sinonimos"]]
        entradas.append(entrada)

    identificador = str(condicion.get("id") or "")
    if identificador and identificador not in conocidos:
        # La condición vive en `condiciones/`, no en `conceptos/`, así que no
        # la alcanza el barrido de arriba. Hace falta en cuanto se active el
        # bloque `clasificacion`, que la acuña como término.
        entrada = {
            "codigo": identificador,
            "termino": str(condicion.get("termino") or ""),
            "semantica": "trastorno",
            "padre": "HM:1000",
        }
        if condicion.get("sinonimos"):
            entrada["sinonimos"] = [str(s) for s in condicion["sinonimos"]]
        entradas.append(entrada)

    return entradas


# ── Composición ───────────────────────────────────────────────────────────


@dataclass
class Borrador:
    texto: str
    codigos: list[str] = field(default_factory=list)


def convertir(condicion: dict, indice: Indice, informe: Informe) -> Borrador:
    termino = str(condicion.get("termino") or "")
    identificador = str(condicion.get("id") or "")

    cabecera = Bloque()
    cabecera.crudo("---")
    # Sólo la inicial: «infección precoz por VIH» pierde el acrónimo si se
    # baja el término entero.
    cabecera.campo("titulo", f"Protocolo de {termino[:1].lower()}{termino[1:]}")
    cabecera.comentario(
        "Frase con la que el triaje elige este protocolo. Descríbelo por lo que "
        "el paciente trae, no por el diagnóstico: el triaje sólo ha leído el "
        "texto de hoy."
    )
    sinonimos = ", ".join(str(s) for s in (condicion.get("sinonimos") or []))
    cabecera.prosa(
        "descripcion",
        f"TODO. {termino}" + (f" ({sinonimos})." if sinonimos else "."),
    )
    cabecera.campo("version", "0.1.0-borrador")
    cabecera.crudo()

    cabecera.crudo("condicion:")
    cabecera.campo("nombre", termino, sangria=2)
    codigos_condicion = {
        k: v for k, v in (condicion.get("codigos") or {}).items() if v
    }
    codigos_condicion.setdefault("holonmed", identificador)
    cabecera.crudo("  codigos:")
    for sistema, valor in codigos_condicion.items():
        cabecera.campo(str(sistema), str(valor), sangria=4)
    if not any(k != "holonmed" for k in codigos_condicion):
        informe.pendiente(
            "condicion",
            "sin código SNOMED ni CIE-10 en el índice. El protocolo funciona, "
            "pero lo que produzca no se podrá mapear fuera de holonmed",
        )

    bloque_signos, codigos_usados = signos(condicion, indice, informe)
    bloque_ambito = ambito_grafo(codigos_usados, indice)
    bloque_bayes = bayes(condicion, indice, informe)
    bloque_lab = laboratorio(codigos_usados, indice, informe)
    bloque_clas = clasificacion(condicion, indice, informe)
    bloque_nucleo = nucleo_y_balance(condicion, indice, informe)

    procedencia = Bloque()
    procedencia.crudo("# De dónde salió este archivo. No lo edites a mano: si vuelves a")
    procedencia.crudo("# pasar el conversor, se regenera y el PR queda auditable.")
    procedencia.crudo("procedencia:")
    procedencia.campo("indice", "medsemiotics-db", sangria=2)
    procedencia.campo("condicion", identificador, sangria=2)
    procedencia.campo("commit", indice.commit, sangria=2)
    procedencia.campo("generado", date.today().isoformat(), sangria=2)
    procedencia.campo("herramienta", "scripts/convertir_condicion.py", sangria=2)

    if not indice.limpio:
        informe.pendiente(
            "procedencia",
            f"el clon del índice tiene cambios sin confirmar: el commit "
            f"{indice.commit} no reproduce lo que acabas de leer. Confírmalos "
            f"antes de abrir el PR",
        )

    # El núcleo va ANTES del balance y ambos antes de los signos: se lee en el
    # mismo orden en que se aplica —primero si el criterio procede, luego cómo
    # se cuenta, después qué se cuenta—.
    piezas = [cabecera, bloque_ambito, bloque_nucleo, bloque_bayes, bloque_signos,
              bloque_lab, bloque_clas, procedencia]
    frontmatter = "\n\n".join(p.texto() for p in piezas if p is not None)

    referidos = list(
        dict.fromkeys(
            codigos_usados
            + ramas(codigos_usados, indice)
            + [str(s.get("concepto")) for s in (condicion.get("signos_de_alarma") or [])]
        )
    )
    return Borrador(
        texto=frontmatter + "\n---\n\n" + cuerpo(condicion, codigos_usados, indice, informe),
        codigos=[c for c in referidos if c and c != "None"],
    )


# ── Interfaz ──────────────────────────────────────────────────────────────


def listar(indice: Indice) -> int:
    print(f"\nÍndice: {indice.ruta}  ({indice.commit}"
          f"{'' if indice.limpio else ', con cambios sin confirmar'})")
    print(f"{len(indice.condiciones)} condiciones\n")
    for identificador, condicion in sorted(indice.condiciones.items()):
        aristas = condicion.get("signos") or []
        con_lr = sum(1 for a in aristas if a.get("lr_positivo") or a.get("lr_negativo"))
        print(
            f"  {identificador:<10} {str(condicion.get('termino')):<42}"
            f"{len(aristas):>3} aristas, {con_lr:>2} con cociente"
        )
    print()
    return 0


def resolver(clave: str, indice: Indice) -> tuple[str, dict]:
    """Acepta 'HM:6007', 'HM6007' o el nombre del archivo."""
    normalizada = clave.strip()
    if normalizada in indice.condiciones:
        return normalizada, indice.condiciones[normalizada]

    con_dos_puntos = re.sub(r"^(HM)[:\-]?(\d{4})$", r"\1:\2", normalizada, flags=re.I).upper()
    if con_dos_puntos in indice.condiciones:
        return con_dos_puntos, indice.condiciones[con_dos_puntos]

    for identificador, stem in indice.archivos.items():
        if stem == normalizada or stem.startswith(normalizada):
            return identificador, indice.condiciones[identificador]

    raise SystemExit(
        f"No hay ninguna condición «{clave}» en el índice.\n"
        f"Usa --listar para ver las {len(indice.condiciones)} disponibles."
    )


def nombre_por_defecto(identificador: str, indice: Indice) -> str:
    stem = indice.archivos.get(identificador, identificador)
    return re.sub(r"^HM\d+-", "", stem).replace("-", "_")


def sync_all(indice: Indice, forzar: bool, ruta_vocab: Path | None) -> int:
    """Convierte de una sola pasada toda condición del índice que todavía no
    tenga protocolo en `backend/skills/`.

    Reutiliza `convertir()` y `nombre_por_defecto()` sin duplicar su lógica,
    así que se comporta exactamente igual que pasar cada condición a mano:
    el mismo nombre de archivo, el mismo informe, la misma protección
    `--forzar` para no pisar un protocolo con prosa ya escrita. Lo único que
    hace por su cuenta es decidir CUÁLES condiciones son nuevas —comparando
    el archivo de destino, no una lista aparte que pueda desincronizarse—.
    """
    conocidos, ruta_semilla = vocabulario_local()

    nuevas: list[str] = []
    cubiertas: list[str] = []
    for identificador in sorted(indice.condiciones):
        nombre = nombre_por_defecto(identificador, indice)
        destino = DIRECTORIO_SKILLS / f"{nombre}.md"
        (nuevas if (forzar or not destino.exists()) else cubiertas).append(identificador)

    print(
        f"\nÍndice: {indice.ruta}  ({indice.commit}"
        f"{'' if indice.limpio else ', con cambios sin confirmar'})",
        file=sys.stderr,
    )
    print(f"{len(cubiertas)} condición(es) ya con protocolo, {len(nuevas)} nueva(s)\n", file=sys.stderr)
    if not nuevas:
        print("Nada que convertir.", file=sys.stderr)
        return 0

    vocab_acumulado: list[dict] = []
    vistos_acumulado = set()
    for identificador in nuevas:
        condicion = indice.condiciones[identificador]
        informe = Informe()
        borrador = convertir(condicion, indice, informe)

        faltan = fragmento_vocabulario(borrador.codigos, condicion, indice, conocidos)
        for entrada in faltan:
            if entrada["codigo"] not in vistos_acumulado:
                vistos_acumulado.add(entrada["codigo"])
                vocab_acumulado.append(entrada)
        if faltan:
            informe.pendiente(
                "vocabulario",
                f"{len(faltan)} concepto(s) del protocolo no existen en "
                f"{ruta_semilla.name}: {', '.join(e['codigo'] for e in faltan)}. "
                f"Van en el vocabulario consolidado de esta corrida",
            )
        # Los recién vistos cuentan como conocidos para el resto de la
        # corrida: dos condiciones nuevas que comparten un concepto no lo
        # duplican en el vocabulario consolidado.
        conocidos = conocidos | {e["codigo"] for e in faltan}

        nombre = nombre_por_defecto(identificador, indice)
        destino = DIRECTORIO_SKILLS / f"{nombre}.md"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(borrador.texto, encoding="utf-8", newline="\n")

        print(f"=== {identificador} · {condicion.get('termino')} -> {destino.name} ===", file=sys.stderr)
        informe.imprimir()
        print(file=sys.stderr)

    if vocab_acumulado:
        destino_vocab = ruta_vocab or Path("vocabulario_nuevo.json")
        destino_vocab.parent.mkdir(parents=True, exist_ok=True)
        destino_vocab.write_text(
            json.dumps({"conceptos": vocab_acumulado}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(
            f"Vocabulario nuevo consolidado en {destino_vocab} "
            f"({len(vocab_acumulado)} concepto(s), sin repetir entre condiciones).\n"
            f"Mézclalo en `conceptos` de {ruta_semilla.name} y recarga:\n"
            f"  python scripts/importar_terminologia.py --semilla",
            file=sys.stderr,
        )

    print(
        f"\n{len(nuevas)} protocolo(s) escrito(s) en {DIRECTORIO_SKILLS}. Ninguno se "
        f"auto-completa: cada uno necesita prosa (rol, contexto fisiopatológico, "
        f"banderas rojas), fijar `probabilidad_base` y `factores_riesgo` si aplica, "
        f"pasar `holonmed skills --validar` y subirse como pull request — uno por "
        f"uno o juntos, pero siempre revisados por un humano antes de fusionar.",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    _consola_en_utf8()
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("condicion", nargs="?", help="HM:6007, HM6007 o el nombre del archivo")
    parser.add_argument("--indice", type=Path, default=INDICE_POR_DEFECTO,
                        help=f"Clon local de medsemiotics-db (por defecto {INDICE_POR_DEFECTO})")
    parser.add_argument("--salida", type=Path, metavar="ARCHIVO",
                        help="Dónde escribir. Sin esto, sale por pantalla")
    parser.add_argument("--skills", action="store_true",
                        help=f"Escribe en {DIRECTORIO_SKILLS} con el nombre derivado")
    parser.add_argument("--forzar", action="store_true",
                        help="Sobrescribe un protocolo existente")
    parser.add_argument("--vocabulario", type=Path, metavar="ARCHIVO",
                        help="Escribe los conceptos que faltan en el vocabulario semilla")
    parser.add_argument("--listar", action="store_true", help="Qué hay en el índice")
    parser.add_argument(
        "--sync-all", action="store_true",
        help="Convierte toda condición del índice que no tenga ya protocolo en backend/skills/",
    )
    args = parser.parse_args()

    indice = cargar_indice(args.indice.resolve())

    if args.sync_all:
        return sync_all(indice, args.forzar, args.vocabulario)

    if args.listar or not args.condicion:
        return listar(indice)

    identificador, condicion = resolver(args.condicion, indice)
    informe = Informe()
    borrador = convertir(condicion, indice, informe)

    # Un código que holonmed no reconoce no rompe nada de forma visible: el
    # hallazgo se extrae y produce un infón sin linaje ni mapeo. Por eso se
    # comprueba aquí, antes de que el protocolo llegue a usarse.
    conocidos, ruta_semilla = vocabulario_local()
    faltan = fragmento_vocabulario(borrador.codigos, condicion, indice, conocidos)
    if faltan:
        informe.pendiente(
            "vocabulario",
            f"{len(faltan)} concepto(s) del protocolo no existen en "
            f"{ruta_semilla.name}: {', '.join(e['codigo'] for e in faltan)}. Sin "
            f"ellos el protocolo carga, pero sus hallazgos no se codifican. "
            f"Sácalos con --vocabulario y mézclalos en `conceptos`",
        )

    destino = args.salida
    if destino is None and args.skills:
        destino = DIRECTORIO_SKILLS / f"{nombre_por_defecto(identificador, indice)}.md"

    if args.vocabulario:
        args.vocabulario.parent.mkdir(parents=True, exist_ok=True)
        args.vocabulario.write_text(
            json.dumps({"conceptos": faltan}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(
            f"Conceptos que faltan: {args.vocabulario} ({len(faltan)})\n"
            f"Mézclalos en la lista `conceptos` de {ruta_semilla.name} y recarga:\n"
            f"  python scripts/importar_terminologia.py --semilla",
            file=sys.stderr,
        )

    if destino is None:
        print(borrador.texto)
    else:
        if destino.exists() and not args.forzar:
            # Un protocolo en uso lleva prosa escrita a mano que este script no
            # sabe reconstruir. Sobrescribirlo por descuido la borra entera.
            raise SystemExit(
                f"Ya existe {destino}.\n"
                f"Genera al lado y compara antes de pisarlo:\n"
                f"  python scripts/convertir_condicion.py {identificador} "
                f"--salida {destino.with_suffix('.nuevo.md')}"
            )
        destino.parent.mkdir(parents=True, exist_ok=True)
        # `newline` explícito: en Windows el traslado saldría con CRLF y el
        # repositorio es LF entero. Un protocolo nuevo aparecería como
        # archivo reescrito de arriba abajo en cuanto alguien lo tocara.
        destino.write_text(borrador.texto, encoding="utf-8", newline="\n")
        print(f"Escrito: {destino}", file=sys.stderr)

    print(
        f"\n{condicion.get('termino')} ({identificador}) desde "
        f"medsemiotics-db@{indice.commit}",
        file=sys.stderr,
    )
    informe.imprimir()
    print(
        "\nEl índice no publica en holonmed: revisa el borrador, escribe la prosa,\n"
        "pasa `holonmed skills --validar` y súbelo como pull request.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
