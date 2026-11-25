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
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NamedTuple

from ..models import InferenciaBayesiana, Infon, Polaridad

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
        apariciones = [m.start() for m in re.finditer(re.escape(aguja), antecedentes)]
        if not apariciones:
            continue
        # Una nota puede mencionar el mismo factor varias veces y contradecirse
        # («niega alcoholismo. Luego reconoce alcoholismo crónico»), y los
        # antecedentes registrados se concatenan con la nota de hoy. Basta UNA
        # mención no negada para que el factor exista; sólo se suprime si TODAS
        # lo niegan. Sigue contando una sola vez: la que se elige es la primera
        # afirmada.
        afirmadas = [i for i in apariciones if not _esta_negado(antecedentes, i)]
        inicio = (afirmadas or apariciones)[0]
        negado = not afirmadas
        contradicho = bool(afirmadas) and len(afirmadas) < len(apariciones)
        candidatos.append(
            (inicio, inicio + len(aguja), str(factor), peso, negado, contradicho)
        )

    # El nombre más específico primero: con «alcoholismo» y «alcohol» en el
    # mismo sitio, manda el largo.
    candidatos.sort(key=lambda c: (c[0], -(c[1] - c[0])))

    salida: list[_FactorAplicado] = []
    ocupados: list[tuple[int, int]] = []
    for inicio, fin, factor, peso, negado, contradicho in candidatos:
        if any(inicio < f and i < fin for (i, f) in ocupados):
            salida.append(
                _FactorAplicado(
                    None,
                    f"Factor de riesgo '{factor}': se solapa con otro ya contado "
                    f"sobre el mismo texto — se cuenta UNA vez",
                )
            )
            continue

        if negado:
            ocupados.append((inicio, fin))
            salida.append(
                _FactorAplicado(
                    None,
                    f"Factor de riesgo '{factor}' NO aplicado: el texto lo niega",
                )
            )
            continue

        ocupados.append((inicio, fin))
        nota = " — otra mención lo niega y otra lo afirma" if contradicho else ""
        salida.append(
            _FactorAplicado(peso, f"Factor de riesgo '{factor}' (×{peso}){nota}")
        )
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
        mapa_signos = self._mapa_signos(skill_json)
        evidencia: list[str] = []

        # Se resuelve contra TODO lo que el protocolo declara y después se
        # mira si el signo trae cociente. Resolver sólo contra los que lo
        # traen haría que un hallazgo que nombra un signo sin LR cayera en
        # otro que sí lo tiene.
        vocabulario = self._vocabulario(skill_json)
        pares: list[tuple[str, Infon]] = []
        for infon in infones:
            # Sólo evidencia validada mueve la probabilidad. Un hallazgo en
            # ALERTA o RUIDO se muestra al clínico pero no entra al cálculo.
            if not infon.es_valido:
                continue
            clave = emparejar_infon(infon, vocabulario)
            if clave is not None and clave in mapa_signos:
                pares.append((clave, infon))

        # Un signo, una vez: dos menciones de la misma observación no son dos
        # pruebas independientes y su LR no se multiplica dos veces.
        elegidos = elegir_por_signo(pares)
        for clave, infon in pares:
            if infon is elegidos[clave]:
                continue
            nombre_signo = mapa_signos[clave].nombre
            if infon.polaridad is not elegidos[clave].polaridad:
                traza.append(
                    f"'{nombre_signo}': registro contradictorio — se descarta "
                    f"'{infon.termino}' ({infon.polaridad.value}) y manda la "
                    f"observación más reciente"
                )
            else:
                traza.append(
                    f"'{nombre_signo}': dos observaciones del mismo signo — se "
                    f"cuenta UNA vez y se descarta '{infon.termino}'"
                )

        for etiqueta, infon in elegidos.items():
            signo = mapa_signos[etiqueta]

            if signo.tramos:
                pob_ctx = infon.poblacion or (
                    str(holon_metadata["poblacion"])
                    if holon_metadata.get("poblacion")
                    else None
                )
                evaluacion = signo.evaluar_valor(
                    infon.valor, unidad=infon.unidad, poblacion=pob_ctx
                )
                if evaluacion.motivo:
                    traza.append(evaluacion.motivo)
                if (
                    evaluacion.tramo is None
                    and evaluacion.lr is None
                    and evaluacion.lr_negativo is None
                ):
                    continue
                positivo = evaluacion.lr
                negativo = evaluacion.lr_negativo
                tramo_activo = evaluacion.tramo
            else:
                positivo = signo.lr
                negativo = signo.lr_negativo
                tramo_activo = None

            # La polaridad decide qué LR se aplica. Una prueba sensible
            # negativa descarta con fuerza, y hasta ahora esa evidencia se
            # perdía: el sistema sólo sabía sumar.
            if infon.descarta:
                lr = negativo
                sufijo = " [ausente]"
            else:
                lr = positivo
                sufijo = ""

            if lr is None or lr == 1.0:
                if tramo_activo is not None:
                    traza.append(
                        f"'{signo.nombre}' (tramo '{tramo_activo.etiqueta()}'): "
                        f"sin LR aplicable para polaridad "
                        f"{'ausente' if infon.descarta else 'presente'}"
                    )
                continue

            odds *= lr
            direccion = "a favor" if lr > 1 else "en contra"
            if tramo_activo is not None:
                unidad_txt = infon.unidad or signo.graduacion.unidad
                valor_txt = (
                    f" ({infon.valor:g}{(' ' + unidad_txt) if unidad_txt else ''})"
                    if infon.valor is not None
                    else ""
                )
                evidencia.append(
                    f"{infon.termino}{valor_txt}{sufijo} → LR {lr} "
                    f"({direccion}, vía '{etiqueta}', tramo '{tramo_activo.etiqueta()}')"
                )
            else:
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
    def _mapa_signos(skill_json: dict[str, Any]) -> dict[str, Any]:
        """Término -> Signo (con LR escalar y/o tramos graduados)."""
        from .skills import Graduacion, Signo, Tramo

        mapa: dict[str, Signo] = {}
        for item in skill_json.get("signDetected", []) or []:
            if not isinstance(item, dict):
                continue
            nombre = item.get("name") or item.get("nombre") or item.get("analito")
            if not nombre:
                continue
            nombre_str = str(nombre)
            positivo = _recortar(
                item.get("bayes_lr") if "bayes_lr" in item else item.get("lr"),
                nombre_str,
                "LR+",
            )
            negativo = _recortar(
                item.get("bayes_lr_negativo")
                if "bayes_lr_negativo" in item
                else item.get("lr_negativo"),
                nombre_str,
                "LR-",
            )

            grad_raw = item.get("graduacion")
            if isinstance(grad_raw, dict):
                graduacion = Graduacion(
                    parametro=str(grad_raw.get("parametro") or "").strip(),
                    unidad=str(grad_raw.get("unidad") or "").strip(),
                    lectura=str(grad_raw.get("lectura") or "").strip(),
                )
            else:
                graduacion = Graduacion(
                    parametro=str(item.get("parametro") or "").strip(),
                    unidad=str(item.get("unidad") or "").strip(),
                    lectura=str(item.get("lectura") or "").strip(),
                )

            tramos_raw = item.get("tramos") if "tramos" in item else item.get("bandas")
            tramos: list[Tramo] = []
            for t in tramos_raw or []:
                if not isinstance(t, dict):
                    continue
                t_lr = _recortar(
                    t.get("lr") if "lr" in t else t.get("lr_positivo"),
                    nombre_str,
                    "LR+",
                )
                t_lr_neg = _recortar(t.get("lr_negativo"), nombre_str, "LR-")
                desde_v = t.get("desde")
                hasta_v = t.get("hasta")
                tramos.append(
                    Tramo(
                        umbral=str(t.get("umbral") or "").strip(),
                        umbral_condicion=str(t.get("umbral_condicion") or "").strip(),
                        desde=(
                            float(desde_v)
                            if isinstance(desde_v, (int, float))
                            and not isinstance(desde_v, bool)
                            else None
                        ),
                        hasta=(
                            float(hasta_v)
                            if isinstance(hasta_v, (int, float))
                            and not isinstance(hasta_v, bool)
                            else None
                        ),
                        lr=t_lr,
                        lr_negativo=t_lr_neg,
                        poblacion=str(t.get("poblacion") or "").strip(),
                        fuente=str(t.get("fuente") or "").strip(),
                    )
                )

            if positivo is None and negativo is None and not tramos:
                continue

            mapa[nombre_str.lower()] = Signo(
                nombre=nombre_str,
                lr=positivo,
                lr_negativo=negativo,
                graduacion=graduacion,
                tramos=tramos,
            )
        return mapa

    @staticmethod
    def _vocabulario(skill_json: dict[str, Any]) -> dict[str, dict[str, str]]:
        """Todo signo declarado, lleve LR o no, con sus códigos."""
        declarados: list[tuple[str, Mapping[str, Any]]] = []
        for lista in ("vocabulario", "signDetected"):
            for item in skill_json.get(lista, []) or []:
                if not isinstance(item, dict):
                    continue
                nombre = item.get("name") or item.get("nombre") or item.get("analito")
                if nombre:
                    declarados.append((str(nombre), item.get("codigos") or {}))
        return construir_vocabulario(declarados)


# --- Emparejamiento término ↔ signo ---------------------------------------
#
# PARÁMETRO DE SEGURIDAD. Vive aquí, y no duplicado en cada consumidor, porque
# Bayes, el veredicto declarado, la promoción y el medidor de acoplamiento
# tienen que emparejar **igual**: Φ lee la dirección del mismo vector cuya
# magnitud lee Bayes, y si poblaran ese vector con criterios distintos la
# relación entre las dos métricas dejaría de ser cierta.
#
# La regla anterior era contención de subcadena en las dos direcciones. Con
# ella «Dolor torácico» heredaba el LR de «Dolor torácico irradiado a ambos
# brazos», «Tos» emparejaba con «Vómitos» y la cadena vacía con cualquiera.

# Lo que puede seguir a la clave para que el resto sea un calificador suyo. El
# guion no está: «AUDIT-C» no es un «AUDIT» con apellido, es otro instrumento.
_TRAS_LA_CLAVE = " ,;:("


def _normalizar(texto: str) -> str:
    return " ".join(str(texto).lower().split())


def emparejar_termino(termino: str, mapa: Mapping[str, Any]) -> str | None:
    """La clave que nombra el término, o una que el término especifica.

    Sólo dos casos emparejan:

    * el mismo nombre, salvo mayúsculas y espacios;
    * el término **empieza** por la clave, en palabras completas, y añade
      calificadores: «Odinofagia intensa» es un caso de «Odinofagia».

    Nunca al revés: un término genérico no hereda lo que el protocolo declara
    de uno específico, porque eso afirma un dato que nadie observó. Tampoco
    basta con que la clave aparezca en medio: «Sensación de frío previa al
    síncope» no es un síncope y «Antecedente de disnea» no es disnea.

    No es un analizador de lenguaje: un calificador pospuesto que niegue
    («Disnea descartada») sigue emparejando. La polaridad se resuelve en la
    extracción y llega en `Infon.polaridad`.
    """
    objetivo = _normalizar(termino)
    claves = {_normalizar(clave): clave for clave in mapa}
    if not objetivo:
        return None
    if objetivo in claves:
        return claves[objetivo]
    candidatas = [
        normal
        for normal in claves
        if normal
        and objetivo.startswith(normal)
        and objetivo[len(normal)] in _TRAS_LA_CLAVE
    ]
    if candidatas:
        return claves[max(candidatas, key=len)]
    return None


def construir_vocabulario(
    declarados: Iterable[tuple[str, Mapping[str, Any]]],
) -> dict[str, dict[str, str]]:
    """Nombre en minúsculas -> códigos, de cada signo que el protocolo declara."""
    vocabulario: dict[str, dict[str, str]] = {}
    for nombre, codigos in declarados:
        entrada = vocabulario.setdefault(nombre.lower(), {})
        entrada.update({str(s): str(c) for s, c in codigos.items()})
    return vocabulario


def emparejar_infon(
    infon: Infon, vocabulario: Mapping[str, Mapping[str, str]]
) -> str | None:
    """El signo declarado al que corresponde un infón, o None.

    `vocabulario` debe ser el protocolo ENTERO: quien sólo mire un subconjunto
    filtra el resultado, no la entrada. En este orden:

    1. el mismo nombre;
    2. el mismo código, que es identidad declarada por el protocolo y la
       ontología («Hiperlipasemia» y «Hiperlipasemia (>3x)» son HM:0732). Si
       el código nombra más de un signo no se elige ninguno;
    3. el término especifica a la clave, **sólo si consta presente**. Que
       falte «X irradiado» no dice que falte «X», y aplicarle su LR− bajaría
       la probabilidad con una ausencia que nadie documentó.
    """
    clave = emparejar_termino(infon.termino, vocabulario)
    if clave is not None and _normalizar(clave) == _normalizar(infon.termino):
        return clave
    if infon.codigo and infon.sistema:
        mismas = [
            k for k, c in vocabulario.items() if c.get(infon.sistema) == infon.codigo
        ]
        if mismas:
            return mismas[0] if len(mismas) == 1 else None
    if infon.polaridad is not Polaridad.PRESENTE:
        return None
    return clave


def elegir_por_signo(pares: Iterable[tuple[str, Infon]]) -> dict[str, Infon]:
    """Un infón por signo, con el mismo criterio para Bayes y para Φ.

    Si dos infones del mismo signo se contradicen, manda el más reciente: una
    lipasa normal hoy no queda anulada por una alta de la semana pasada,
    aunque aquella se midiera con más confianza. Si concuerdan, manda el de
    mejor confianza.
    """
    elegidos: dict[str, Infon] = {}
    for clave, infon in pares:
        previo = elegidos.get(clave)
        if previo is None:
            elegidos[clave] = infon
        elif previo.polaridad is not infon.polaridad:
            logger.info(
                "Registro contradictorio sobre '%s': %s vs %s; manda el reciente",
                clave,
                previo.polaridad.value,
                infon.polaridad.value,
            )
            if infon.timestamp > previo.timestamp:
                elegidos[clave] = infon
        elif infon.confianza > previo.confianza:
            elegidos[clave] = infon
    return elegidos


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
