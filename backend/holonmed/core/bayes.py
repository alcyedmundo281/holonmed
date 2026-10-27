"""Motor de inferencia abductiva.

Razonamiento bayesiano clásico sobre *odds*: se parte de la prevalencia
poblacional, se ajusta por los factores de riesgo del paciente y se
actualiza con los likelihood ratios de cada hallazgo confirmado.

    odds_posterior = odds_previo × Π(LR de cada evidencia)

Lo que distingue a este motor de una caja negra es que devuelve la traza
completa: cada multiplicación queda registrada con su origen. Un clínico
puede recorrer el razonamiento y discrepar de un paso concreto, que es
justamente lo que un sistema de apoyo a la decisión debe permitir.

El nombre de la clase viene de la analogía inmunológica del proyecto: una
célula presentadora de antígeno recoge fragmentos dispersos y los presenta
juntos para que otro sistema decida. Aquí los fragmentos son infones.
"""

import logging
import re
from collections.abc import Sequence
from typing import Any, NamedTuple

from ..models import InferenciaBayesiana, Infon

logger = logging.getLogger(__name__)

# Sin esto, un LR mal puesto en un skill puede llevar la probabilidad a 100%
# y presentar una certeza que la evidencia no sostiene.
LR_MAXIMO = 100.0
PROBABILIDAD_MAXIMA = 0.99


# Marcas de negación como PALABRAS completas. Como subcadena, «no » casaba con
# el final de «masculino» y «femenino», y «masculino con alcoholismo» salía
# como un antecedente negado. `(?<!\w)` exige que la marca empiece en una
# frontera de palabra; se busca sobre el texto entero y no sobre la ventana
# recortada, para que una ventana que empiece a media palabra tampoco engañe.
_NEGACION = re.compile(r"(?<!\w)(?:sin|no|niega|ausencia\s+de|descarta)\s", re.IGNORECASE)
_VENTANA_NEGACION = 24

# Lo que CORTA el alcance de una negación antes de llegar al factor: el fin de
# la frase (. ; : ! ? o salto de línea) y las palabras que vuelven a afirmar o
# contrastan (con, pero, aunque, salvo, excepto, sino). Sin esto, «Sin fiebre.
# Alcoholismo crónico» y «Sin fiebre, con alcoholismo» suprimían un factor
# AFIRMADO porque había un «sin» a menos de 24 caracteres, y la previa bajaba.
# La coma NO corta: «niega tabaquismo, alcoholismo» es una lista negada, y
# tratar la coma como corte aplicaría un factor que el texto niega, que es
# el error que sube la probabilidad. «ni» tampoco corta: continúa la negación.
_CORTE_NEGACION = re.compile(
    r"[.;:!?\n]|(?<!\w)(?:con|pero|aunque|salvo|excepto|sino)(?!\w)", re.IGNORECASE
)


def _esta_negado(antecedentes: str, inicio: int) -> bool:
    """¿Llega una negación hasta el factor que empieza en `inicio`?

    Cuenta la negación MÁS CERCANA dentro de la ventana, y sólo si entre ella y
    el factor no hay un corte de frase ni una palabra que afirme de nuevo. Se
    busca sobre el texto entero y no sobre la ventana recortada, para que una
    ventana que empiece a media palabra tampoco invente una marca.
    """
    desde = max(0, inicio - _VENTANA_NEGACION)
    marcas = list(_NEGACION.finditer(antecedentes, desde, inicio))
    if not marcas:
        return False
    return _CORTE_NEGACION.search(antecedentes, marcas[-1].end(), inicio) is None


class _FactorAplicado(NamedTuple):
    """Un factor de riesgo con lo que se hizo con él. `peso=None`: no aplicado."""

    peso: float | None
    linea: str


def _factores_que_aplican(factores: dict, antecedentes: str) -> list[_FactorAplicado]:
    """Qué factores modifican la probabilidad previa, y cuáles no y por qué.

    DOS DEFECTOS QUE ESTO CIERRA, LOS DOS EN LA DIRECCIÓN PELIGROSA
    ---------------------------------------------------------------
    El código anterior era `if factor.lower() in antecedentes: odds *= peso`
    en un bucle por clave. Con un antecedente de «alcoholismo crónico» y un
    protocolo que declara `alcohol` y `alcoholismo` —dos nombres del MISMO
    factor— la previa se multiplicaba dos veces:

        Prevalencia poblacional: 5.00%
        Factor de riesgo 'alcohol' (×2.8)
        Factor de riesgo 'alcoholismo' (×2.8)     29.2% en vez de 12.8%

    Y siendo subcadena, **«sin antecedente de alcoholismo» también
    multiplicaba** ×7.84. Eso ya no es un error de magnitud: es de dirección.
    El sistema subía la probabilidad porque la nota decía que el paciente NO
    tenía el factor.

    QUÉ HACE
    --------
    · Varias claves sobre el MISMO trozo de texto son un factor: se aplica
      una vez —la coincidencia más larga, el nombre más específico— y se dice
      que las otras se solaparon. Contar de más infla la previa, que es hacia
      donde no se debe errar.
    · Un factor precedido de una marca de negación no se aplica, y se informa.
      Un factor suprimido que se anuncia es auditable; uno aplicado en
      silencio sobre una negación, no.

    QUÉ NO ES
    ---------
    No es un analizador de negación y no pretende serlo. El arreglo de fondo
    es que los antecedentes pasen por la misma extracción y validación que los
    hallazgos —donde ya hay polaridad y tres capas de auditoría— en vez de
    emparejarse por subcadena contra texto libre. Hoy el a priori rodea todo
    el aparato que el resto del sistema usa para no equivocarse.
    """
    candidatos = []
    for factor, peso_crudo in factores.items():
        peso = _a_float(peso_crudo, 1.0)
        if peso <= 0:
            continue
        aguja = str(factor).lower()
        inicio = antecedentes.find(aguja)
        if inicio < 0:
            continue
        candidatos.append((inicio, inicio + len(aguja), str(factor), peso))

    # El nombre más específico primero: con «alcoholismo» y «alcohol» en el
    # mismo sitio, manda el largo.
    candidatos.sort(key=lambda c: (c[0], -(c[1] - c[0])))

    salida: list[_FactorAplicado] = []
    ocupados: list[tuple[int, int]] = []
    for inicio, fin, factor, peso in candidatos:
        if any(inicio < f and i < fin for (i, f) in ocupados):
            salida.append(
                _FactorAplicado(
                    None,
                    f"Factor de riesgo '{factor}': se solapa con otro ya contado "
                    f"sobre el mismo texto — se cuenta UNA vez",
                )
            )
            continue

        if _esta_negado(antecedentes, inicio):
            ocupados.append((inicio, fin))
            salida.append(
                _FactorAplicado(
                    None,
                    f"Factor de riesgo '{factor}' NO aplicado: el texto lo niega",
                )
            )
            continue

        ocupados.append((inicio, fin))
        salida.append(_FactorAplicado(peso, f"Factor de riesgo '{factor}' (×{peso})"))
    return salida


class AntigenPresentingCell:
    """Cruza los metadatos del holón con el modelo bayesiano de la skill."""

    def calcular(
        self,
        holon_metadata: dict[str, Any],
        skill_json: dict[str, Any],
        infones: Sequence[Infon],
    ) -> InferenciaBayesiana | None:
        modelo = skill_json.get("modelo_bayesiano")
        if not isinstance(modelo, dict):
            return None  # La skill no declara modelo: no se inventa uno.

        prob_base = _a_float(modelo.get("probabilidad_base"), 0.01)
        prob_base = min(max(prob_base, 1e-6), PROBABILIDAD_MAXIMA)

        odds = prob_base / (1 - prob_base)
        traza: list[str] = [f"Prevalencia poblacional: {prob_base * 100:.2f}%"]

        # --- A priori: quién es el paciente ---------------------------
        antecedentes = str(holon_metadata.get("antecedentes", "")).lower()
        factores = modelo.get("factores_riesgo_a_priori")
        if isinstance(factores, dict):
            for aplicado in _factores_que_aplican(factores, antecedentes):
                if aplicado.peso is not None:
                    odds *= aplicado.peso
                traza.append(aplicado.linea)

        edad = holon_metadata.get("edad")
        if edad is not None:
            traza.append(f"Edad {edad} años")

        prob_previa = odds / (1 + odds)

        # --- A posteriori: qué muestra la evidencia -------------------
        mapa_lr = self._mapa_likelihood_ratios(skill_json)
        evidencia: list[str] = []

        for infon in infones:
            # Sólo evidencia validada mueve la probabilidad. Un hallazgo en
            # ALERTA o RUIDO se muestra al clínico pero no entra al cálculo.
            if not infon.es_valido:
                continue

            par, etiqueta = self._buscar_lr(infon.termino, mapa_lr)
            if par is None:
                continue

            # La polaridad decide qué LR se aplica. Una prueba sensible
            # negativa descarta con fuerza, y hasta ahora esa evidencia se
            # perdía: el sistema sólo sabía sumar.
            positivo, negativo = par
            if infon.descarta:
                lr = negativo
                sufijo = " [ausente]"
            else:
                lr = positivo
                sufijo = ""

            if lr is None or lr == 1.0:
                continue

            odds *= lr
            direccion = "a favor" if lr > 1 else "en contra"
            evidencia.append(
                f"{infon.termino}{sufijo} → LR {lr} ({direccion}, vía '{etiqueta}')"
            )

        prob_final = odds / (1 + odds)
        prob_final = min(prob_final, PROBABILIDAD_MAXIMA)

        if not evidencia:
            traza.append("Sin evidencia validada: la probabilidad no se actualizó")

        return InferenciaBayesiana(
            diagnostico=skill_json.get("name", "Hipótesis sin nombre"),
            probabilidad_porcentaje=round(prob_final * 100, 2),
            probabilidad_previa=round(prob_previa * 100, 2),
            traza_logica=traza,
            evidencia_utilizada=evidencia,
        )

    @staticmethod
    def _mapa_likelihood_ratios(
        skill_json: dict[str, Any],
    ) -> dict[str, tuple[float | None, float | None]]:
        """Término -> (LR+, LR-). Ambos opcionales."""
        mapa: dict[str, tuple[float | None, float | None]] = {}
        for signo in skill_json.get("signDetected", []) or []:
            if not isinstance(signo, dict):
                continue
            nombre = signo.get("name")
            if not nombre:
                continue
            positivo = _recortar(signo.get("bayes_lr"), nombre, "LR+")
            negativo = _recortar(signo.get("bayes_lr_negativo"), nombre, "LR-")
            if positivo is None and negativo is None:
                continue
            mapa[str(nombre).lower()] = (positivo, negativo)
        return mapa

    @staticmethod
    def _buscar_lr(termino: str, mapa: dict[str, tuple[float | None, float | None]]):
        """Empareja el término normalizado con un LR del protocolo."""
        clave = emparejar_termino(termino, mapa)
        if clave is None:
            return None, ""
        return mapa[clave], clave


def emparejar_termino(termino: str, mapa: dict[str, Any]) -> str | None:
    """Localiza la clave del protocolo que corresponde a un término clínico.

    Vive aquí, y no duplicada en cada consumidor, porque el motor bayesiano
    y el medidor de acoplamiento tienen que emparejar **igual**: Φ lee la
    dirección del mismo vector cuya magnitud lee Bayes, y si los dos
    módulos poblaran ese vector con criterios distintos la relación entre
    las dos métricas dejaría de ser cierta.
    """
    objetivo = termino.lower()
    if objetivo in mapa:
        return objetivo
    # Coincidencia por contención: "hiperamilasemia (>3x)" contra
    # "hiperamilasemia". Se prefiere la clave más larga, que es la más
    # específica de las que encajan.
    candidatas = [clave for clave in mapa if clave in objetivo or objetivo in clave]
    if candidatas:
        return max(candidatas, key=len)
    return None


def _a_float(valor: Any, defecto: float) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def _recortar(valor: Any, nombre: str, etiqueta: str) -> float | None:
    """Valida y acota un likelihood ratio declarado en un protocolo."""
    if not isinstance(valor, (int, float)):
        return None
    lr = float(valor)
    if lr <= 0:
        logger.warning("%s inválido (%s) para '%s'; ignorado", etiqueta, lr, nombre)
        return None
    if lr > LR_MAXIMO:
        logger.warning("%s %s para '%s' recortado a %s", etiqueta, lr, nombre, LR_MAXIMO)
        return LR_MAXIMO
    return lr
