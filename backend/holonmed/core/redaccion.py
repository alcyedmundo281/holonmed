"""Qué puede cambiar una corrección de redacción, comprobado con código.

El modelo propone un texto corregido y aquí se decide si se puede enseñar.
No se le pregunta a ningún modelo si conservó los hechos: se comparan los dos
textos y, ante cualquier diferencia que no esté permitida, se rechaza.

POR QUÉ SE PROTEGEN TODAS LAS PALABRAS

Negaciones, lateralidad o meses se pueden enumerar. Los fármacos no: aquí no
hay un diccionario que los reconozca a todos, y nada determinista dice si un
sinónimo conserva el hecho («disfagia» y «disfasia» distan una letra). Así que
no se buscan los hechos para protegerlos: se protege **todo** salvo lo que está
en una lista cerrada de cambios que no pueden alterarlos.

QUÉ SE PUEDE CAMBIAR

- Puntuación, mayúsculas, espacios, saltos de línea y marcas de formato; en
  una frase con negación, la puntuación no puede cambiar lo que queda dentro.
- Añadir una tilde que faltaba. No quitarla ni moverla.
- Añadir, quitar o ajustar «el», «la», «los», «las», «además», «asimismo» y
  «adicionalmente».

Todo lo demás —palabras, cifras, símbolos y su orden— tiene que ser igual. No
se corrigen faltas de ortografía que cambien letras, ni se resume ni se
reescribe: es el precio de poder garantizar lo otro.

LO QUE NO GARANTIZA

Una coma o un punto movidos fuera de una frase con negación pueden cambiar a
qué se refiere una expresión, y una tilde añadida puede cambiar el sentido
(«practico», «práctico»). Quien lee compara la propuesta con el original, que
por eso se enseña al lado.
"""

import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

# Topes de tamaño, no parámetros clínicos. Un texto más largo no cabe en el
# contexto del modelo local y volvería cortado.
MAX_CARACTERES = 6000

_LIBRES = frozenset({"el", "la", "los", "las", "además", "asimismo", "adicionalmente"})
_ARTICULOS = frozenset({"el", "la", "los", "las"})

# El género de estos nombres sólo lo dice el artículo: cambiarlo, ponerlo o
# quitarlo cambia el sexo de la persona.
_GENERO_SOLO_EN_EL_ARTICULO = frozenset(
    {
        "paciente",
        "pacientes",
        "estudiante",
        "joven",
        "adolescente",
        "lactante",
        "infante",
        "familiar",
        "cónyuge",
        "acompañante",
        "donante",
        "gestante",
        "declarante",
    }
)

# Se comparan letra por letra, mayúsculas incluidas: «mg» no es «Mg» y «mUI»
# no es «MUI».
_UNIDADES = frozenset(
    "g mg mcg µg μg ug ng pg kg l dl ml µl μl ul fl mol mmol µmol μmol nmol pmol "
    "meq ui u mui µui μui mm cm m mmhg h s min seg lpm rpm bpm gy sv".split()
)

_NEGACIONES = frozenset(
    "no sin ni nunca jamás jamas tampoco ningún ningun ninguno ninguna ningunos "
    "ningunas nada nadie niega niegan negó nego negado negada ausencia ausente "
    "ausentes descarta descartan descartó descartado descartada negativo negativa "
    "negativos negativas excluye excluido excluida".split()
)

# Cierran el alcance de una negación, lleven o no una coma delante.
_ADVERSATIVAS = frozenset({"pero", "aunque", "sino"})

_LATERALIDAD = frozenset(
    "derecho derecha derechos derechas izquierdo izquierda izquierdos izquierdas "
    "bilateral bilaterales unilateral unilaterales ipsilateral contralateral "
    "homolateral diestro diestra zurdo zurda".split()
)

_FECHAS = frozenset(
    "enero febrero marzo abril mayo junio julio agosto septiembre setiembre octubre "
    "noviembre diciembre lunes martes miércoles jueves viernes sábado domingo hoy "
    "ayer anteayer anoche mañana".split()
)

_CIFRAS_EN_LETRA = frozenset(
    "cero un uno una dos tres cuatro cinco seis siete ocho nueve diez once doce "
    "trece catorce quince veinte treinta cuarenta cincuenta cien ciento mil medio "
    "media doble triple".split()
)

_SIMBOLOS_PROTEGIDOS = frozenset("%‰/?'′″^")
# Marcas de formato que la categoría Unicode daría por símbolos.
_SIMBOLOS_IGNORADOS = frozenset("|`")
_GUIONES = frozenset("-‐‑‒–—−")

_PIEZA = re.compile(
    r"(?P<cifra>\d+(?:[.,:]\d+)*)|(?P<palabra>[^\W\d_]+)|(?P<salto>\n)|(?P<otro>\S)"
)
_CORTES = frozenset(".,;:!?()[]\n")
# Los que terminan una frase. Los demás sólo separan dentro de ella: el punto
# y coma también, porque separa los elementos de una enumeración.
_CORTES_DE_FRASE = frozenset(".!?\n")
# Su punto no termina la frase. También cuenta cualquier letra suelta.
_ABREVIATURAS = frozenset("ej etc aprox dr dra vs núm vit".split())


class CorreccionRechazada(ValueError):
    """La corrección no se puede ofrecer. El original queda como estaba."""


@dataclass(frozen=True)
class _Ficha:
    texto: str
    clave: str
    # Se compara tal cual: sin plegar mayúsculas ni tildes.
    literal: bool
    articulo: str = ""


def _sin_tildes(palabra: str) -> str:
    """Sin acento agudo ni diéresis. La tilde de la «ñ» se queda."""
    plano = unicodedata.normalize("NFD", palabra)
    return unicodedata.normalize("NFC", plano.replace("́", "").replace("̈", ""))


def _es_simbolo(texto: str, inicio: int, caracter: str) -> bool:
    if caracter in _GUIONES:
        return _guion_con_sentido(texto, inicio)
    if caracter == "*":
        return _entre_cifras(texto, inicio)
    if caracter in _SIMBOLOS_IGNORADOS:
        return False
    return caracter in _SIMBOLOS_PROTEGIDOS or unicodedata.category(caracter) in {
        "Sm",
        "So",
        "Sc",
    }


def _entre_cifras(texto: str, i: int) -> bool:
    antes, despues = texto[:i].rstrip(" "), texto[i + 1 :].lstrip(" ")
    return antes[-1:].isdigit() and despues[:1].isdigit()


def _guion_con_sentido(texto: str, i: int) -> bool:
    """Rango, signo o resultado negativo; no una viñeta ni una raya de inciso."""
    if _entre_cifras(texto, i):
        return True
    previo, siguiente = texto[i - 1 : i], texto[i + 1 : i + 2]
    if siguiente.isdigit() and (not previo or previo.isspace() or previo in "(=:"):
        return True
    resto = texto[i + 1 :].lstrip(" ")[:1]
    hay_algo_antes = bool(texto[:i].rsplit("\n", 1)[-1].strip())
    if hay_algo_antes and (not resto or resto in "\n.,;)"):
        return True
    return previo.isalnum() and not siguiente.isalnum()


@dataclass
class _Clausula:
    fichas: list[_Ficha] = field(default_factory=list)
    # "frase", "pausa", "adversativa", "abreviatura" o "lista" (dos puntos
    # al final de un renglón). El final del texto cierra la frase.
    cierre: str = ""


def _cerrar(clausulas: list[_Clausula], cierre: str) -> None:
    """Abre otra cláusula. De varios cortes seguidos manda el primero."""
    if clausulas[-1].fichas:
        clausulas[-1].cierre = cierre
        clausulas.append(_Clausula())


def _tipo_de_corte(texto: str, i: int) -> str:
    if texto[i] == ".":
        previa = re.search(r"(?<![^\W\d_])[^\W\d_]+$", texto[:i])
        if previa:
            palabra = previa.group(0).lower()
            if len(palabra) == 1 or palabra in _ABREVIATURAS:
                return "abreviatura"
    if texto[i] == ":" and texto[i + 1 :].lstrip(" \t\r*_").startswith("\n"):
        return "lista"
    return "frase" if texto[i] in _CORTES_DE_FRASE else "pausa"


def _trocear(texto: str) -> list[_Clausula]:
    """Las fichas protegidas, agrupadas en cláusulas."""
    clausulas = [_Clausula()]
    articulo = ""
    tras_cifra = False
    for pieza in _PIEZA.finditer(texto):
        token = pieza.group(0)
        if pieza.lastgroup == "cifra":
            clausulas[-1].fichas.append(_Ficha(token, token, True))
            articulo, tras_cifra = "", True
        elif pieza.lastgroup == "palabra":
            baja = token.lower()
            siglas = token[1:] != token[1:].lower()
            if baja in _LIBRES and not siglas and not tras_cifra:
                if baja in _ARTICULOS:
                    articulo = baja
                continue
            if baja in _ADVERSATIVAS:
                # Con coma delante, con punto o sin nada, el cierre es el mismo.
                _cerrar(clausulas, "adversativa")
                if len(clausulas) > 1:
                    clausulas[-2].cierre = "adversativa"
            literal = siglas or baja in _UNIDADES
            if literal:
                clave = token
            else:
                # Lo que sigue a una cifra suele ser su unidad: aunque no
                # esté en la lista, no se le cambian las mayúsculas.
                clave = _sin_tildes(token if tras_cifra else baja)
            clausulas[-1].fichas.append(_Ficha(token, clave, literal, articulo))
            articulo, tras_cifra = "", False
        else:
            if token in _CORTES:
                tipo = _tipo_de_corte(texto, pieza.start())
                if clausulas[-1].fichas:
                    _cerrar(clausulas, tipo)
                elif (
                    tipo == "frase"
                    and token != "\n"
                    and len(clausulas) > 1
                    and clausulas[-2].cierre == "pausa"
                ):
                    # En «(hoy).» el punto termina la frase aunque llegue
                    # después del paréntesis. Un salto de línea tras una coma
                    # no: es el mismo renglón partido.
                    clausulas[-2].cierre = "frase"
                articulo, tras_cifra = "", False
            if _es_simbolo(texto, pieza.start(), token):
                clave = "-" if token in _GUIONES else token
                clausulas[-1].fichas.append(_Ficha(token, clave, True))
                tras_cifra = False
    clausulas = [c for c in clausulas if c.fichas]
    if clausulas:
        clausulas[-1].cierre = "frase"
    return clausulas


def _categoria(ficha: _Ficha) -> str:
    baja = ficha.texto.lower()
    if baja in _NEGACIONES:
        return "negaciones"
    if baja[:1].isdigit() or baja in _CIFRAS_EN_LETRA:
        return "cifras, dosis o fechas"
    if baja in _UNIDADES:
        return "unidades"
    if baja in _LATERALIDAD:
        return "lateralidad"
    if baja in _FECHAS:
        return "fechas"
    if not any(c.isalnum() for c in baja):
        return "signos con significado"
    return "términos (entre ellos, fármacos)"


def _rechazo(motivo: str) -> CorreccionRechazada:
    return CorreccionRechazada(
        f"Se descarta la corrección: {motivo}. El texto original no cambia."
    )


def _comparar_fichas(antes: list[_Ficha], despues: list[_Ficha]) -> None:
    comparador = difflib.SequenceMatcher(
        a=[f.clave for f in antes], b=[f.clave for f in despues], autojunk=False
    )
    quitadas: list[_Ficha] = []
    puestas: list[_Ficha] = []
    for operacion, i1, i2, j1, j2 in comparador.get_opcodes():
        if operacion != "equal":
            quitadas += antes[i1:i2]
            puestas += despues[j1:j2]
    if not (quitadas or puestas):
        return

    categorias = ", ".join(sorted({_categoria(f) for f in quitadas + puestas}))
    # Sólo se cita el original: lo que el modelo añadió no se muestra.
    citas = ", ".join(f"«{f.texto}»" for f in quitadas[:5])
    detalle = f"; en el original, afecta a {citas}" if citas else "; añade contenido"
    raise _rechazo(f"cambia {categorias}{detalle}")


def _comparar_grafia(antes: _Ficha, despues: _Ficha) -> None:
    """Misma palabra salvo por tildes: sólo se admite haber añadido una."""
    if antes.literal or despues.literal:
        return
    original, corregida = antes.texto.lower(), despues.texto.lower()
    if original == corregida:
        return
    quita = any(
        letra != _sin_tildes(letra) and letra != nueva
        for letra, nueva in zip(original, corregida, strict=True)
    )
    # «si» y «sí» no dicen lo mismo, y una tilde en la «o» o la «e» final
    # suele cambiar el tiempo del verbo: «tomo», «tomó».
    cambia_sentido = original == "si" or (original[-1] in "oe" and corregida[-1] in "óé")
    if quita or cambia_sentido:
        raise _rechazo(f"cambia la tilde de «{antes.texto}» y puede cambiar su sentido")


def _frases(clausulas: list[_Clausula]) -> list[list[_Clausula]]:
    frases: list[list[_Clausula]] = [[]]
    for clausula in clausulas:
        frases[-1].append(clausula)
        if clausula.cierre in {"frase", "adversativa"}:
            frases.append([])
    return [f for f in frases if f]


def _niega(clausula: _Clausula) -> bool:
    return any(f.texto.lower() in _NEGACIONES for f in clausula.fichas)


def _negadas(clausulas: list[_Clausula]) -> list[tuple[tuple[str, ...], ...]]:
    """Cada frase con una negación, entera y con cómo se separan sus partes.

    La negación alcanza a toda la enumeración: en «niega fiebre, tos, dolor»
    un punto antes de «dolor» lo sacaría de lo negado. Si lo que se niega
    anuncia una lista en renglones aparte, no se sabe dónde acaba y se
    protege todo lo que sigue.
    """
    negadas = []
    hasta_el_final = False
    for frase in _frases(clausulas):
        if hasta_el_final or any(map(_niega, frase)):
            negadas.append(tuple((*(f.clave for f in c.fichas), c.cierre) for c in frase))
        hasta_el_final = hasta_el_final or any(
            c.cierre == "lista" and any(map(_niega, frase[: i + 1]))
            for i, c in enumerate(frase)
        )
    return negadas


def verificar_correccion(original: str, corregido: str) -> None:
    """No devuelve nada si `corregido` es admisible; si no, dice por qué no."""
    original = unicodedata.normalize("NFC", original)
    corregido = unicodedata.normalize("NFC", corregido)

    # Un carácter invisible o una marca suelta alteran lo que se lee sin
    # alterar las palabras que se comparan.
    nuevos = set(corregido) - set(original) - set("\n\r\t")
    if any(unicodedata.category(c) in {"Cc", "Cf", "Mn", "Me", "Co"} for c in nuevos):
        raise _rechazo("introduce caracteres invisibles o marcas superpuestas")

    antes, despues = _trocear(original), _trocear(corregido)
    planas_antes = [f for c in antes for f in c.fichas]
    planas_despues = [f for c in despues for f in c.fichas]
    _comparar_fichas(planas_antes, planas_despues)

    for a, d in zip(planas_antes, planas_despues, strict=True):
        _comparar_grafia(a, d)
        if a.texto.lower() in _GENERO_SOLO_EN_EL_ARTICULO and a.articulo != d.articulo:
            raise _rechazo(
                f"cambia el artículo de «{a.texto}», que es lo que indica el sexo"
            )

    if _negadas(antes) != _negadas(despues):
        raise _rechazo(
            "mueve la puntuación de una frase con negación y cambia su alcance"
        )


def validar_salida(datos: dict[str, Any], original: str) -> str:
    """El texto corregido que se puede enseñar, o el motivo del rechazo."""
    texto = datos.get("texto_corregido")
    if not isinstance(texto, str) or not texto.strip():
        raise _rechazo("el modelo no devolvió un texto corregido interpretable")
    texto = texto.strip()
    # Los artículos son libres; sin tope podrían repetirse sin límite.
    if len(texto) > len(original) * 1.2 + 80:
        raise _rechazo("el texto devuelto es mucho más largo que el original")
    if texto == original.strip():
        raise CorreccionRechazada(
            "El modelo no propone ningún cambio. El texto original no cambia."
        )
    verificar_correccion(original, texto)
    return texto
