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
from collections.abc import Sequence
from typing import Any

from ..models import InferenciaBayesiana, Infon

logger = logging.getLogger(__name__)

# Sin esto, un LR mal puesto en un skill puede llevar la probabilidad a 100%
# y presentar una certeza que la evidencia no sostiene.
LR_MAXIMO = 100.0
PROBABILIDAD_MAXIMA = 0.99


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
            for factor, peso_crudo in factores.items():
                peso = _a_float(peso_crudo, 1.0)
                if peso <= 0:
                    continue
                if factor.lower() in antecedentes:
                    odds *= peso
                    traza.append(f"Factor de riesgo '{factor}' (×{peso})")

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
