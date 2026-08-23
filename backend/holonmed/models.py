"""Modelos de dominio de HolonMed.

El vocabulario es deliberado y viene de la teoría que sostiene el sistema:

* **Infón**: el átomo de verdad. Un hallazgo clínico único, normalizado
  contra SNOMED CT y auditado. Si no pasó el validador, sigue siendo un
  infón, pero marcado como ruido: el sistema nunca borra evidencia, la
  clasifica.
* **Holón**: la historia clínica como organismo. No es un formulario que
  se rellena, es un ente que crece absorbiendo infones a lo largo del
  tiempo. Cada consulta es un *tic* que lo hace crecer.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrigenTic(str, Enum):
    """Qué proceso produjo un tic.

    En un entorno clínico real la información no llega de un solo sitio: la
    consulta dicta una narrativa, el laboratorio devuelve un informe, la
    farmacia dispensa. Los tres alimentan la misma historia, pero no valen
    lo mismo ni se auditan igual, así que el origen tiene que quedar
    registrado en el dato y no deducirse del contexto.

    Es además la pieza sobre la que se apoyará el multiusuario: cuando haya
    autenticación, el origen saldrá del rol de quien escribe.
    """

    CONSULTA = "consulta"
    LABORATORIO = "laboratorio"
    FARMACIA = "farmacia"
    ENFERMERIA = "enfermeria"
    IMAGEN = "imagen"
    OTRO = "otro"


class Polaridad(str, Enum):
    """Si el hallazgo está presente o consta explícitamente como ausente.

    La distinción no es cosmética: en un razonamiento bayesiano una prueba
    sensible negativa descarta con fuerza, y hasta ahora el sistema tiraba
    esa evidencia. El prompt de extracción decía literalmente «ignora los
    hallazgos negados», así que «lipasa normal» —que es la evidencia más
    potente en contra de una pancreatitis— no llegaba a ninguna parte.

    Hay un tercer caso que NO se representa aquí a propósito: que no conste
    nada. «No consta» no es «ausente». Tratarlos igual produciría falsos
    negativos con toda la confianza del mundo, así que la ausencia de
    mención simplemente no genera infón.
    """

    PRESENTE = "presente"
    AUSENTE = "ausente"


class EstadoInfon(str, Enum):
    """Veredicto del validador de tres capas."""

    VALIDADO = "VALIDADO"  # Ontología y lógica coinciden. Utilizable.
    ALERTA = "ALERTA"  # Acierto ontológico, duda lógica. Requiere ojo humano.
    RUIDO = "RUIDO"  # Descartado. Probable alucinación del modelo.


class Infon(BaseModel):
    """El átomo de verdad: una afirmación clínica validada y trazable."""

    timestamp: str = Field(default_factory=_now)

    # Procedencia
    texto_origen: str = Field(description="Cita textual de la narrativa original")
    termino_propuesto: str = Field(description="Lo que el LLM extrajo, sin normalizar")

    # Normalización ontológica. El sistema de codificación es explícito
    # porque el vocabulario es intercambiable: puede ser el semilla del
    # proyecto, SNOMED CT si tienes licencia, o cualquier otro importado.
    termino: str = Field(description="Término preferente tras la normalización")
    polaridad: Polaridad = Polaridad.PRESENTE
    codigo: str | None = None
    sistema: str | None = Field(
        default=None, description="'holonmed' | 'snomed' | 'hpo' | …"
    )
    concepto_id: int | None = Field(
        default=None, description="Clave interna del concepto en el grafo"
    )
    cie10_code: str | None = None
    linaje_clinico: str | None = Field(
        default=None, description="Concepto padre en la jerarquía del grafo"
    )

    # Derivación: un infón de nivel 2 no se cita de la narrativa sino que
    # se deduce de otros infones mediante criterios de clasificación.
    derivado_de: list[str] = Field(
        default_factory=list,
        description="Términos que satisfacen los criterios, si es derivado",
    )
    criterio: str | None = Field(
        default=None, description="Criterio de clasificación que lo produjo"
    )

    # Veredicto y trazabilidad
    estado: EstadoInfon = EstadoInfon.RUIDO
    confianza: float = 0.0
    score_ontologico: float = 0.0
    score_logico: float = 0.0
    razon_auditoria: str = "No evaluado"
    origen_skill: str = "general_triage"

    @property
    def es_valido(self) -> bool:
        return self.estado == EstadoInfon.VALIDADO

    @property
    def confirma(self) -> bool:
        """Un hallazgo validado y presente. El que suma en la inferencia."""
        return self.es_valido and self.polaridad is Polaridad.PRESENTE

    @property
    def descarta(self) -> bool:
        """Una ausencia documentada y validada. La que resta."""
        return self.es_valido and self.polaridad is Polaridad.AUSENTE

    @property
    def es_facturable(self) -> bool:
        """Un infón sólo sirve para facturar si está validado y mapea a CIE-10."""
        return self.es_valido and bool(self.cie10_code)


class InferenciaBayesiana(BaseModel):
    """Salida del motor abductivo: una hipótesis con su razonamiento visible."""

    diagnostico: str
    probabilidad_porcentaje: float
    probabilidad_previa: float
    traza_logica: list[str] = Field(
        default_factory=list, description="Cómo se construyó la probabilidad a priori"
    )
    evidencia_utilizada: list[str] = Field(
        default_factory=list, description="Qué infones movieron la aguja y cuánto"
    )

    @property
    def veredicto(self) -> str:
        if self.probabilidad_porcentaje > 90:
            return "HIPOTESIS_CONFIRMADA"
        if self.probabilidad_porcentaje > 50:
            return "PROBABLE"
        return "BAJA_SOSPECHA"


class Veto(BaseModel):
    """Un corte duro: la hipótesis no se evalúa, se retira.

    No es una probabilidad baja, es una imposibilidad. Un paciente
    apendicectomizado no tiene poca probabilidad de apendicitis: tiene
    cero, y ninguna evidencia futura la actualiza. Por eso no puede
    expresarse como un likelihood ratio —un cociente de 0.001 deja una
    probabilidad pequeña pero distinta de cero— y necesita mecanismo
    propio.

    Se retira **con su motivo visible**, nunca en silencio: el sistema
    clasifica evidencia, no la borra, y el próximo clínico que lea el caso
    no debería tener que rehacer el razonamiento.
    """

    tipo: str = Field(description="'exclusion_absoluta' | 'tope_banderas'")
    motivo: str
    termino: str | None = None
    hipotesis: str = ""


class VeredictoDeclarado(BaseModel):
    """El conteo del criterio publicado: apoyos contra banderas rojas.

    Es el estándar reproducible —para eso lo escribe un panel— y se lee
    junto a la probabilidad y a Φ **sin fundirse con ellas**. Cuando el
    criterio contado y la aritmética discrepan, esa discrepancia es
    información clínica; reconciliarlas en un número la destruiría.
    """

    nivel: str | None = Field(default=None, description="El grado alcanzado, si alguno")
    apoyos: list[str] = Field(default_factory=list)
    banderas_rojas: list[str] = Field(default_factory=list)
    veto: Veto | None = None
    fuente: str = ""
    traza: list[str] = Field(default_factory=list)

    @property
    def sostiene(self) -> bool:
        return self.veto is None and self.nivel is not None


class EstadoDimension(str, Enum):
    """Qué hace el registro en una dimensión del espacio de hallazgos."""

    CONCUERDA = "concuerda"            # el registro dice lo que la hipótesis exige
    CONTRADICE = "contradice"          # el registro dice lo contrario
    SIN_MEDIR = "sin_medir"            # nadie lo ha mirado: no es ausencia, es vacío
    NO_SIMBOLIZADO = "no_simbolizado"  # hallazgo real que la hipótesis no explica


class VeredictoSemiotico(str, Enum):
    """Lectura del coeficiente de acoplamiento en bandas.

    Las bandas son presentación; la métrica es Φ, que es continuo. Se
    nombran para que el clínico no tenga que interpretar un decimal a
    solas, nunca para sustituirlo.
    """

    ARMONIA = "ARMONIA"                            # la creencia es operable
    ACOPLAMIENTO_PARCIAL = "ACOPLAMIENTO_PARCIAL"  # encaja, pero queda por mirar
    INERCIA = "INERCIA"                            # ortogonal: no toca este caso
    FRICCION = "FRICCION"                          # el contexto empieza a disentir
    DESARMONIA = "DESARMONIA"                      # el contexto la contradice


class ComponenteAcoplamiento(BaseModel):
    """Una dimensión del espacio, con lo que la hipótesis exige y lo que hay.

    Es la unidad de auditoría de Φ: un clínico puede recorrer la lista y
    discrepar de una línea concreta, igual que puede hacerlo con la traza
    bayesiana. Una métrica de armonía que no se pudiera impugnar punto por
    punto sería justamente el tipo de argumento que la métrica existe para
    detectar.
    """

    dimension: str
    rol: str = "apoyo"
    esperado: float = Field(description="hᵢ: ln(LR+) que exige el caso de libro")
    observado: float = Field(description="eᵢ: peso de evidencia que aporta el registro")
    estado: EstadoDimension
    detalle: str = ""
    infon: str | None = None
    confianza: float = 0.0

    @property
    def contribucion(self) -> float:
        """Lo que esta dimensión aporta al producto escalar h·e."""
        return round(self.esperado * self.observado, 4)


class Acoplamiento(BaseModel):
    """Coeficiente de Acoplamiento (Φ): armonía entre la hipótesis y el contexto.

    Φ ∈ [−1, +1] es el coseno del ángulo entre el caso de libro y el caso
    real en el espacio del peso de evidencia, atenuado por el anclaje α.
    Nunca modifica la `InferenciaBayesiana`: se lee junto a ella.
    """

    phi: float = Field(description="Φ ∈ [−1, +1]. Armonía con el contexto.")
    coseno: float = Field(description="cos(h,e) antes de aplicar el anclaje")
    phi_categorico: float | None = Field(
        default=None,
        description=(
            "Φ sobre TODOS los signos declarados, con peso ±1 en vez de ln(LR). "
            "Es la única lectura posible cuando el protocolo declara categorías y "
            "no cocientes, que es el caso de casi todos los criterios publicados."
        ),
    )
    coseno_categorico: float | None = Field(
        default=None,
        description=(
            "Φ categórico ANTES de α: el término homólogo de `coseno`, y el "
            "único que sirve para ordenar candidatas. `phi_categorico` ya lleva "
            "α dentro, así que ordenar por él ordena por calidad documental."
        ),
    )
    dimensiones_categoricas: int = 0

    # Los tres factores del coseno. No son cálculo nuevo: son `coseno`
    # partido, y su producto lo reconstruye. Se informan y NUNCA se
    # aplican — multiplicarlos otra vez contaría dos veces algo que ya
    # está dentro. Valen None cuando su definición no existe para este
    # caso, que no es lo mismo que valer cero.
    direccion: float | None = Field(
        default=None,
        description=(
            "cos(h_S, e_S): si lo que se ha mirado concuerda con la hipótesis. "
            "None cuando no se ha mirado ninguna dimensión declarada."
        ),
    )
    cobertura: float | None = Field(
        default=None,
        description=(
            "‖h_S‖²/‖h‖²: qué fracción de lo que la hipótesis AFIRMA se ha "
            "puesto a prueba. Es del lado h. None si el protocolo no declara LR."
        ),
    )
    explicacion: float | None = Field(
        default=None,
        description=(
            "‖e_S‖²/‖e‖²: qué fracción de lo que el paciente TIENE cae dentro "
            "de las dimensiones que la hipótesis declara. Es del lado e, y es "
            "el factor que cobra el resto no simbolizado. None si no hay "
            "vector observado."
        ),
    )

    # Los mismos tres, sobre la lectura de pesos unitarios. Su producto
    # reconstruye `coseno_categorico`, no `phi_categorico`.
    direccion_categorica: float | None = Field(
        default=None, description="Σeᵢ/m: de lo mirado, cuánto concuerda"
    )
    cobertura_categorica: float | None = Field(
        default=None, description="m/D: de lo declarado, cuánto se ha mirado"
    )
    explicacion_categorica: float | None = Field(
        default=None, description="m/(m+r): del registro, cuánto cae dentro"
    )

    anclaje: float = Field(description="α ∈ [0,1]: sujeción del argumento a lo medido")
    hipotesis: str

    veredicto: VeredictoSemiotico
    cuadrante: str = Field(description="Lectura conjunta de la probabilidad y Φ")

    componentes: list[ComponenteAcoplamiento] = Field(default_factory=list)
    resto_no_simbolizado: list[str] = Field(
        default_factory=list,
        description="Hallazgos validados que la hipótesis no explica",
    )
    indagacion: list[str] = Field(
        default_factory=list, description="Hacia dónde apunta la duda"
    )
    anclaje_detalle: dict[str, float] = Field(default_factory=dict)
    traza: list[str] = Field(default_factory=list)

    @property
    def peso_evidencia_declarado(self) -> float:
        """Σ eᵢ sobre las dimensiones que el protocolo declara.

        Ésta —y no la suma sobre el vector completo— es la cantidad que
        iguala `ln(odds posterior / odds previo)` del motor bayesiano. El
        resto no simbolizado queda fuera a propósito: su peso es una
        convención de este módulo, un número que Bayes nunca vio y con el
        que nunca operó.

        Existe como propiedad, y no como una suma escrita en el test, para
        que la invariante tenga un nombre en el código. Quien mañana
        cambie la escala del residuo verá que esta propiedad la excluye
        explícitamente, en vez de descubrir por sorpresa que rompió una
        identidad que sólo vivía en la documentación.
        """
        return sum(
            c.observado
            for c in self.componentes
            if c.estado is not EstadoDimension.NO_SIMBOLIZADO
        )

    @property
    def duda(self) -> bool:
        """Hay duda cuando la creencia ha perdido su armonía con el contexto.

        No es un umbral cosmético: por debajo del acoplamiento mínimo la
        hipótesis ha dejado de funcionar como regla de acción fiable, y eso
        es exactamente lo que debe reabrir la indagación.
        """
        return self.phi < 0.20


class CandidataAbductiva(BaseModel):
    """Un protocolo que compitió por explicar a este paciente, y con qué.

    La competencia **no decide nada todavía**: corre en paralelo al triaje
    para medir cuánto se equivoca el prompt antes de sustituirlo por nada.
    Las perdedoras se guardan a propósito — «se consideró diverticulitis y
    sacó 0.25» *es* la traza de auditoría, y sin ella el sistema mostraría
    una conclusión sin decir contra qué compitió.
    """

    skill: str
    clave: float | None = Field(
        default=None,
        description=(
            "El coseno por el que se ordena: el ponderado si el protocolo "
            "declara cocientes, el categórico si no. Los dos leen en la misma "
            "unidad, así que se comparan sin traducir."
        ),
    )
    lectura: str = Field(
        default="ponderada", description="De cuál de las dos salió `clave`"
    )
    anclaje: float = 0.0
    cobertura: float | None = None
    explicacion: float | None = None

    vetada: bool = False
    motivo_veto: str | None = None
    admitida: bool = Field(
        default=False, description="Ni vetada ni con α = 0: compite de verdad"
    )


class Promocion(BaseModel):
    """¿Sigue siendo un problema, o ya es un diagnóstico?

    La cuarta pregunta, y ninguna de las otras tres la responde. Se lee junto
    a ellas y por separado: una probabilidad alta con la tupla incompleta es
    información clínica —dice que falta una prueba, no que falte evidencia— y
    fundirlas la destruiría.
    """

    hipotesis: str
    promueve: bool

    exigido: dict[str, int] = Field(
        default_factory=dict, description="Cuántos de cada rol pide la tupla"
    )
    cumplido: dict[str, int] = Field(default_factory=dict)
    terminos: dict[str, list[str]] = Field(
        default_factory=dict, description="Qué hallazgo satisface cada rol"
    )
    faltan: dict[str, int] = Field(
        default_factory=dict, description="Lo que impide promover, por rol"
    )

    umbral_postest: float | None = None
    probabilidad: float | None = None
    # None cuando el protocolo no declara umbral: no es «no lo cumple», es
    # que no hay umbral que cumplir.
    umbral_cumplido: bool | None = None

    fuente: str = ""
    traza: list[str] = Field(default_factory=list)

    @property
    def se_queda_como_problema(self) -> bool:
        """Lo que ocurre cuando la tupla no se completa, dicho con su nombre."""
        return not self.promueve


class ResultadoTic(BaseModel):
    """Todo lo que produce un único ciclo de procesamiento (un *tic*)."""

    tic_id: str | None = None
    timestamp: str = Field(default_factory=_now)
    paciente_id: str
    texto_original: str

    origen: OrigenTic = OrigenTic.CONSULTA
    actor: str | None = Field(
        default=None,
        description="Quién asertó estos datos. Sin autenticación es informativo.",
    )

    skill_activa: str
    skill_version: str | None = Field(
        default=None,
        description=(
            "La versión del protocolo que corrió, junto a su nombre. Es lo que "
            "convierte recomputar en auditar: sin ella, volver a pasar los "
            "infones de aquel día por el protocolo de hoy responde a otra "
            "pregunta que la que se quería hacer."
        ),
    )
    resumen: str = ""
    infones: list[Infon] = Field(default_factory=list)
    # `Any` para no importar de core y crear un ciclo; en la práctica es
    # un ResultadoClasificacion.
    clasificacion: Any | None = None
    inferencia: InferenciaBayesiana | None = None
    # Segundo eje, independiente de la probabilidad: cuánto armoniza la
    # hipótesis con el resto del paciente. Se lee junto a `inferencia`,
    # nunca en lugar de ella.
    acoplamiento: Acoplamiento | None = None
    # El criterio publicado, contado. Se lee junto a `inferencia` y
    # `acoplamiento`, nunca fundido con ellos.
    veredicto_declarado: VeredictoDeclarado | None = None

    # La competencia abductiva, que hoy sólo MIDE. El protocolo que se usa
    # sigue siendo `skill_activa`, elegido por el prompt de triaje; esto
    # registra cuál habría elegido el grafo y si coinciden.
    competencia: list[CandidataAbductiva] = Field(default_factory=list)
    ganadora_abductiva: str | None = None
    triaje_coincide: bool | None = Field(
        default=None,
        description="None si no hubo competencia con la que comparar",
    )
    aviso_competencia: str | None = Field(
        default=None,
        description=(
            "Se dice en voz alta cuando la de mayor coseno quedó fuera por α: "
            "«encaja mejor y no puedo usarla porque su protocolo no cita». Si "
            "la compuerta actúa callada, el sistema trata otra cosa."
        ),
    )

    @property
    def infones_validados(self) -> list[Infon]:
        return [i for i in self.infones if i.es_valido]

    @property
    def infones_descartados(self) -> list[Infon]:
        return [i for i in self.infones if i.estado == EstadoInfon.RUIDO]


class HolonPaciente(BaseModel):
    """La historia clínica como organismo digital que crece por absorción."""

    paciente_id: str
    nombre: str = "Paciente"
    edad: int | None = None
    sexo: str | None = None
    telefono: str | None = None
    antecedentes: str = ""

    linea_tiempo: list[Infon] = Field(default_factory=list)
    resumen_vivo: str = "Paciente nuevo sin antecedentes registrados."

    def absorber(self, nuevos: list[Infon]) -> None:
        """El crecimiento del holón: sólo se integra lo que fue validado."""
        self.linea_tiempo.extend(i for i in nuevos if i.es_valido)

    def presentes(self) -> list[Infon]:
        return [i for i in self.linea_tiempo if i.polaridad is Polaridad.PRESENTE]

    def metadatos_para_bayes(self, texto_actual: str = "") -> dict[str, Any]:
        """Contexto que alimenta la probabilidad a priori.

        Se consideran tres fuentes: los antecedentes registrados en la
        ficha, los hallazgos validados de visitas anteriores, y **la
        narrativa de hoy**.

        Incluir la narrativa actual no es opcional: en una primera
        consulta la ficha está vacía y los factores de riesgo sólo
        aparecen en el texto que el clínico acaba de escribir. Sin ella,
        un «bebedor de riesgo con litiasis biliar» arrancaría con la
        prevalencia de la población general.

        Limitación conocida: el emparejamiento de factores es por
        subcadena, así que no entiende negaciones. Una nota que diga «no
        consume alcohol» activaría igualmente un factor «alcohol». Es el
        precio de no meter otra llamada al modelo en el camino, y por eso
        la traza muestra siempre qué factor se aplicó y con qué peso.
        """
        historicos = " ".join(i.termino for i in self.linea_tiempo)
        contexto = f"{self.antecedentes} {historicos} {texto_actual}"
        return {
            "edad": self.edad,
            "sexo": self.sexo,
            "antecedentes": contexto.lower().strip(),
        }


# --- DTOs de la API ---------------------------------------------------


class CrystallizeRequest(BaseModel):
    texto: str = Field(min_length=1, description="Narrativa clínica en bruto")
    paciente_id: str = "default"
    skill: str | None = Field(
        default=None, description="Fuerza una skill y salta el triaje automático"
    )
    origen: OrigenTic = OrigenTic.CONSULTA
    actor: str | None = None


class ChatRequest(BaseModel):
    mensaje: str = Field(min_length=1)
    paciente_id: str = "default"


class PacienteCreate(BaseModel):
    nombre: str = Field(min_length=1)
    edad: int | None = None
    sexo: str | None = None
    telefono: str | None = None
    antecedentes: str = ""


class CitaCreate(BaseModel):
    paciente_id: str
    fecha: str = Field(description="Fecha en lenguaje natural o ISO")
    motivo: str = "Control"
