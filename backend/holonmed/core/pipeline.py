"""El pipeline de cristalización: de narrativa libre a infones validados.

Aquí es donde los dos proyectos se encuentran. HolonMed aportaba el rigor
del validador de tres capas pero corría en un script de Streamlit;
InfonMed aportaba la API, la persistencia y la interfaz pero validaba con
una sola búsqueda difusa. Este módulo pone el motor de HolonMed dentro del
cuerpo de InfonMed.

Un *tic* es un ciclo completo:

    triaje → extracción → validación (3 capas) → inferencia bayesiana

Principio de diseño: cada etapa degrada de forma segura. Si el triaje
falla se usa el protocolo general; si el LLM cae la extracción devuelve
vacío en vez de inventar; si el validador no puede confirmar un hallazgo
lo marca como ruido en lugar de dejarlo pasar. El sistema prefiere no
decir nada antes que decir algo falso.
"""

import logging
from collections.abc import Sequence

from ..config import Settings, get_settings
from ..llm import LLMUnavailable, OllamaClient
from ..models import (
    CandidataAbductiva,
    EstadoInfon,
    HolonPaciente,
    Infon,
    Polaridad,
    ResultadoTic,
)
from .acoplamiento import MedidorDeAcoplamiento
from .bayes import AntigenPresentingCell
from .clasificacion import Clasificador
from .duda import ReabridorDeIndagacion
from .skills import Skill, SkillManager
from .validator import OntologyValidator
from .veredicto import EvaluadorDeVeredicto
from .verifier import ClinicalVerifier

logger = logging.getLogger(__name__)

# Peso de cada capa en la confianza final. La ontología pesa más porque es
# determinista: o el concepto existe en SNOMED o no. La auditoría lógica
# depende del juicio de un LLM y por eso pondera menos.
PESO_ONTOLOGICO = 0.6
PESO_LOGICO = 0.4


PROMPT_EXTRACCION = """{protocolo}

---
ROL: ANALISTA CLÍNICO
Lee la narrativa del paciente y extrae hallazgos médicos ATÓMICOS.

{vocabulario}

REGLA DE ORO PARA LABORATORIO:
No extraigas números sueltos: INTERPRÉTALOS con los 'criterios_laboratorio'
del protocolo de arriba.
- "Calcio 7.5"        -> termino_clinico: "Hipocalcemia"
- "Leucocitos 18.500" -> termino_clinico: "Leucocitosis"
- "FC 115"            -> termino_clinico: "Taquicardia"
- Si el texto ya trae la interpretación ("hipocalcemia leve"), úsala.

REGLAS DE PRECISIÓN:
1. IDIOMA: español técnico.
2. ATOMICIDAD: un hallazgo por infón.
3. GRANULARIDAD: no sustituyas un síntoma por una enfermedad.
   "Dolor epigástrico" NO es "Pancreatitis". Extrae el síntoma.
4. BIOQUÍMICA: no confundas amilasa con lipasa, ni enzimas con lípidos.
5. VOCABULARIO: si el protocolo tiene el término exacto, úsalo.
6. LIMPIEZA: sólo el nombre del hallazgo ("Hiperamilasemia", no "Amilasa 1200").
7. POLARIDAD — esto es importante y tiene tres casos, no dos:
   - El texto AFIRMA el hallazgo -> "presente": true
     «vómitos repetidos», «amilasa 1200»
   - El texto lo NIEGA o lo da por normal -> "presente": false
     «no refiere fiebre», «sin dolor torácico», «lipasa 45» (normal)
     Estos NO se descartan: una prueba negativa es evidencia, y de las
     fuertes. Extráelos con presente=false.
   - El texto NO DICE NADA del hallazgo -> no lo extraigas en absoluto.
     No inventes ausencias. Que no se mencione algo no significa que no
     esté: significa que no se sabe, y eso no es un hallazgo.

FORMATO JSON:
{{"resumen": "una frase clínica", "infones": [{{"texto_origen": "cita textual", "termino_clinico": "término normalizado", "presente": true}}]}}"""


# La pasada genérica extrae con `general_triage`, que no declara ni un
# corte de laboratorio. Pedirle al modelo que interprete números sin
# tenerlos es pedirle que se los invente: está medido en VALIDACION.md
# —el formato `minimo` inventó el corte en 9 de 15 auditorías— y el
# conversor lo documenta con un caso propio, «lipasa 890» auditada como
# «>3x el límite normal (aprox. 250-300)» cuando el protocolo declara 60.
#
# Aquí importa más que en ninguna otra parte, porque lo que salga de esta
# pasada es el conjunto COMÚN contra el que compiten TODAS las candidatas.
# Un corte inventado no desvía una hipótesis: desvía la competencia
# entera, y todas compiten contra un paciente que no existe.
PROMPT_EXTRACCION_GENERICA = """ROL: ANALISTA CLÍNICO
Lee la narrativa del paciente y extrae hallazgos médicos ATÓMICOS.

REGLA DE ORO — LOS NÚMEROS NO SE INTERPRETAN:
Este protocolo NO declara cortes de laboratorio, así que **no puedes saber
si un valor es alto o bajo**. No los conviertas en diagnósticos.
- "Calcio 7.5"          -> NO extraigas nada. No sabes cuál es el corte.
- "Leucocitos 18.500"   -> NO extraigas nada.
- "Lipasa 890"          -> NO extraigas nada.
- "hipocalcemia leve"   -> SÍ: el texto ya trae la interpretación, úsala.
- "fiebre de 38.5"      -> SÍ: «Fiebre», que el texto afirma con palabras.
La diferencia es si la interpretación la hace el texto o la harías tú.

REGLAS DE PRECISIÓN:
1. IDIOMA: español técnico.
2. ATOMICIDAD: un hallazgo por infón.
3. GRANULARIDAD: no sustituyas un síntoma por una enfermedad.
   "Dolor epigástrico" NO es "Pancreatitis". Extrae el síntoma.
4. LIMPIEZA: sólo el nombre del hallazgo.
5. POLARIDAD — tres casos y no dos:
   - El texto AFIRMA el hallazgo -> "presente": true
   - El texto lo NIEGA o lo da por normal -> "presente": false
   - El texto NO DICE NADA -> no lo extraigas. No inventes ausencias.

FORMATO JSON:
{{"resumen": "una frase clínica", "infones": [{{"texto_origen": "cita textual", "termino_clinico": "término normalizado", "presente": true}}]}}"""


def _normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar lo que dice el texto."""
    import unicodedata

    plano = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in plano if not unicodedata.combining(c))


def _sin_cortes_inventados(
    crudos: list[dict], autorizados: set[str]
) -> tuple[list[dict], list[str]]:
    """Retira las interpretaciones de números que ningún corte respalda.

    El prompt de la pasada genérica ya se lo pide al modelo, y esto lo
    comprueba: una regla que sólo vive en un prompt es una recomendación,
    no una garantía, y el modelo que la incumpla lo hará justo donde más
    caro sale — el conjunto COMÚN contra el que compite todo el mundo. Un
    corte inventado ahí no desvía una hipótesis: desvía la competencia
    entera, y todas compiten contra un paciente que no existe.

    LA REGLA NO ES «HAY UN NÚMERO»

    `general_triage` **sí** declara cortes: Temperatura 38.0 → Fiebre,
    FC 100/60 → Taquicardia/Bradicardia, Leucocitos → Leucocitosis. Son
    los universales, y convertirlos es exactamente lo que se le pide. Lo
    que no declara son los de cada enfermedad —lipasa, amilasa, calcio—,
    que es donde el modelo se los inventa: está medido en VALIDACION.md
    y el conversor documenta el suyo, «lipasa 890» auditada como «>3x el
    límite normal (aprox. 250-300)» cuando el protocolo declara 60.

    De modo que la pasada genérica puede volver concepto un número
    **sólo si el término resultante es uno que ella misma declara**. Un
    hallazgo se retira cuando se cumplen las tres:

      · la cita trae un número,
      · el término no aparece en esa misma cita, y
      · el protocolo no autoriza ese término.

    Se compara contra **la cita y no contra la narrativa entera**, que es
    la evidencia que el propio modelo alega. Con la narrativa entera basta
    que la palabra salga en otra frase para colar una interpretación
    inventada: un texto que dice «hipocalcemia leve» en la anamnesis
    dejaría pasar un «Hipocalcemia» derivado del «calcio 6.8» del
    laboratorio, que es justo el caso que hay que cazar.

    Retirar de más es barato: la pasada 1 sólo necesita conceptos con los
    que buscar candidatas en el grafo, y lo que se pierda lo recupera la
    pasada 2, ya con los cortes del protocolo ganador delante. Retirar de
    menos no lo es.
    """
    conservados, retirados = [], []
    for crudo in crudos:
        cita = str(crudo.get("texto_origen", ""))
        termino = str(crudo.get("termino_clinico", "")).strip()
        plano = _normalizar(termino)
        if (
            any(c.isdigit() for c in cita)
            and plano not in _normalizar(cita)
            and plano not in autorizados
        ):
            retirados.append(termino)
            continue
        conservados.append(crudo)
    return conservados, retirados


def _terminos_autorizados(skill: Skill) -> set[str]:
    """Los conceptos que este protocolo puede derivar de una cifra.

    Salen de sus propios criterios de laboratorio, que son los cortes que
    alguien declaró con su fuente. Un signo declarado sin corte no
    autoriza nada: el protocolo dice que le interesa, no en qué cifra
    empieza.
    """
    return {_normalizar(t) for criterio in skill.laboratorio for t in criterio.terminos()}


class CrystallizationPipeline:
    """Orquesta el ciclo completo de un tic clínico."""

    def __init__(
        self,
        llm: OllamaClient,
        skills: SkillManager,
        validador: OntologyValidator,
        verificador: ClinicalVerifier,
        bayes: AntigenPresentingCell | None = None,
        settings: Settings | None = None,
        clasificador: Clasificador | None = None,
        acoplamiento: MedidorDeAcoplamiento | None = None,
        veredicto: EvaluadorDeVeredicto | None = None,
        duda: ReabridorDeIndagacion | None = None,
    ):
        self.llm = llm
        self.skills = skills
        self.validador = validador
        self.verificador = verificador
        self.bayes = bayes or AntigenPresentingCell()
        self.clasificador = clasificador or Clasificador()
        self.acoplamiento = acoplamiento or MedidorDeAcoplamiento()
        self.veredicto = veredicto or EvaluadorDeVeredicto()
        self.duda = duda or ReabridorDeIndagacion()
        self.settings = settings or get_settings()

    async def ejecutar(
        self,
        texto: str,
        holon: HolonPaciente,
        skill_forzada: str | None = None,
    ) -> ResultadoTic:
        """Un tic completo, con la abducción delante.

        El orden invierte el de siempre, y la razón es que el de siempre
        estaba al revés. La etapa que se llamaba «inferencia abductiva»
        era Bayes, y Bayes no genera hipótesis: pesa una que ya alguien
        eligió. La abducción real ocurría en el triaje —un prompt— y de
        él colgaban la validación, el veto, los cocientes y el coseno.

        Ahora la hipótesis la elige la competencia sobre el grafo del
        paciente, que es la regla peirceana escrita como argmax: se
        observa el hecho sorprendente C; si A fuera verdadera, C sería de
        curso natural; luego hay razón para sospechar A. Un coseno alto
        es exactamente eso.

        Las dos pasadas son la consecuencia de un bloqueo real: Φ necesita
        infones, los infones necesitan la skill, y la skill es lo que se
        está eligiendo. Se rompe extrayendo primero con el vocabulario
        genérico —el conjunto COMÚN contra el que compiten todas— y
        volviendo a leer después con los hints de la ganadora. Esa segunda
        lectura **es** el paso deductivo aplicado al texto que ya está en
        la mano: antes de preguntarle nada al paciente, se relee la nota
        buscando lo que la hipótesis predice y la pasada genérica no supo
        ver.
        """
        # --- ETAPA 1: TRIAJE, que ya no decide ------------------------
        # Sigue corriendo, y no por inercia: comparar lo que dice el
        # prompt con lo que elige el grafo es la cifra que justifica
        # haberlo sustituido, y dejar de calcularla sería quedarse sin la
        # prueba justo cuando empieza a importar. También es la red: si el
        # grafo no propone nada, aquí está la hipótesis de siempre.
        if skill_forzada:
            triaje = self.skills.cargar_o_defecto(skill_forzada)
        else:
            try:
                nombre = await self.skills.triaje(texto, self.llm)
            except LLMUnavailable:
                nombre = None
            triaje = self.skills.cargar_o_defecto(nombre)

        resultado = ResultadoTic(
            paciente_id=holon.paciente_id,
            texto_original=texto,
            skill_activa=triaje.nombre,
            skill_version=triaje.version,
        )

        # --- ETAPA 2: LA EXTRACCIÓN -----------------------------------
        # El interruptor gobierna la FORMA del tic y no sólo quién vota.
        # Encendido: se lee primero con el vocabulario genérico, porque el
        # protocolo es lo que se está eligiendo y no se puede leer con él.
        # Apagado: se lee con el del triaje y una sola vez, que es como
        # corría antes del ciclo 7 — apagar la inversión no puede costar
        # la llamada de más que la inversión necesita.
        #
        # La competencia mide en los dos modos. Apagada, mide sobre el
        # conjunto que extrajo el triaje, que es exactamente lo que medía
        # antes; la lectura neutral llega con la inversión.
        decide = self.settings.abduccion_decide
        generico = self.skills.cargar_o_defecto(None)
        base = generico if decide else triaje

        extraidos, resumen = await self._extraer(texto, base, generica=decide)
        resultado.resumen = resumen
        if not extraidos:
            logger.info("Sin hallazgos extraíbles en el tic")
            return resultado

        hints_base = base.hints_snomed()
        for crudo in extraidos:
            infon = await self._validar_hallazgo(crudo, texto, base, hints_base)
            if infon:
                resultado.infones.append(infon)

        # --- ETAPA 3: LA COMPETENCIA ABDUCTIVA, que ahora decide ------
        # Corre sobre el conjunto común y ANTES de la clasificación: la
        # clasificación acuña un infón específico de la hipótesis y lo
        # mete en la lista, así que compitiendo después cada candidata
        # competiría contra un paciente distinto —el suyo, con su propio
        # trastorno inyectado—, que es la forma más literal de usar el
        # dato dos veces.
        try:
            self._competir(resultado, holon)
        except Exception:  # noqa: BLE001 — la competencia no puede tumbar el tic
            logger.exception("La competencia abductiva falló; decide el triaje")

        skill = self._elegir_hipotesis(resultado, triaje, skill_forzada)
        if skill is None:
            return resultado
        resultado.skill_activa = skill.nombre
        resultado.skill_version = skill.version
        logger.info("Tic para %s — hipótesis: %s", holon.paciente_id, skill.nombre)

        # --- ETAPA 4: PASADA 2, la deducción sobre el texto -----------
        # La condición es «la hipótesis difiere de aquello con lo que ya
        # se leyó», y vale en los dos modos: apagada, `base` ES el triaje
        # y la ganadora también, de modo que no hay nada que releer y no
        # hace falta consultar el interruptor otra vez.
        if skill.nombre != base.nombre:
            await self._segunda_pasada(texto, skill, resultado)

        # --- ETAPA 5: CLASIFICACIÓN ------------------------------------
        # Sólo la de la ganadora, y después de competir.
        try:
            resultado.clasificacion = self.clasificador.evaluar(skill, resultado.infones)
            if resultado.clasificacion and resultado.clasificacion.trastorno:
                resultado.infones.append(resultado.clasificacion.trastorno)
        except Exception:  # noqa: BLE001 — un fallo aquí no anula el tic
            logger.exception("Clasificador falló; el tic conserva sus infones")

        # --- ETAPA 6: EL VEREDICTO DECLARADO ---------------------------
        # El veto de la ganadora ya se evaluó en la competencia y no la
        # retiró; esto recalcula el veredicto sobre el conjunto final, que
        # incluye lo que la pasada 2 añadió y el trastorno acuñado.
        try:
            resultado.veredicto_declarado = self.veredicto.evaluar(
                skill, list(holon.linea_tiempo) + resultado.infones
            )
        except Exception:  # noqa: BLE001 — un fallo aquí no anula el tic
            logger.exception("Evaluador de veredicto falló; el tic sigue en pie")

        if resultado.veredicto_declarado and resultado.veredicto_declarado.veto:
            # Puede aparecer aquí y no en la competencia: la pasada 2 lee
            # con los hints de la ganadora y puede sacar el antecedente
            # que la excluye. Es un hallazgo, no una anomalía.
            logger.info(
                "Hipótesis '%s' retirada tras la segunda pasada: %s",
                skill.nombre,
                resultado.veredicto_declarado.veto.motivo,
            )
            return resultado

        # --- ETAPA 6: INFERENCIA ABDUCTIVA ----------------------------
        try:
            resultado.inferencia = self.bayes.calcular(
                holon.metadatos_para_bayes(texto),
                skill.json_principal,
                resultado.infones,
            )
        except Exception:  # noqa: BLE001 — un fallo de Bayes no anula el tic
            logger.exception("Motor bayesiano falló; el tic conserva sus infones")

        # --- ETAPA 7: VALIDACIÓN SEMIÓTICA ----------------------------
        # Bayes ya dijo cuánta evidencia hay. Falta la otra pregunta: si
        # esta hipótesis, tomada como regla de acción, armoniza con el
        # paciente entero o deja fricción. Es aritmética determinista
        # sobre lo que las etapas anteriores ya auditaron — ninguna
        # llamada más al modelo — y en ningún caso toca la probabilidad.
        try:
            resultado.acoplamiento = self.acoplamiento.medir(
                skill,
                # Se mide contra el paciente completo, no sólo contra el
                # texto de hoy: una hipótesis puede encajar en la consulta
                # de esta mañana y desentonar con el hallazgo de la
                # semana pasada. Esa desafinación es justo lo que Φ existe
                # para hacer visible.
                list(holon.linea_tiempo) + resultado.infones,
                resultado.inferencia,
            )
        except Exception:  # noqa: BLE001 — un fallo de Φ no anula el tic
            logger.exception("Medidor de acoplamiento falló; el tic sigue en pie")

        # --- ETAPA 8: LA DUDA REABRE LA INDAGACIÓN --------------------
        # El cierre del bucle de Peirce, y la única etapa que puede decir
        # que el tic no llegó a ninguna parte. Φ ya calculó que la
        # hipótesis dejó de funcionar como regla de acción; hasta aquí
        # nadie leía ese número y el tic terminaba igual que si todo
        # hubiera encajado.
        #
        # No retira nada —eso es el veto— y no vuelve a correr la
        # competencia: la competencia ya corrió en la etapa 3b, sobre el
        # mismo paciente, así que la vuelta a la abducción está calculada
        # y sólo hay que decir a dónde apunta.
        # El Φ anterior de esta misma hipótesis viene en el holón, cargado
        # por quien lo construyó: el pipeline no habla con la base de datos.
        # Sin él la duda sería una foto; con él se puede decir si la
        # creencia se rompió o si nunca llegó a arraigar, que son dos
        # situaciones clínicas distintas.
        try:
            resultado.reapertura = self.duda.reabrir(
                resultado.acoplamiento,
                resultado.ganadora_abductiva,
                holon.phi_previo.get(
                    resultado.acoplamiento.hipotesis if resultado.acoplamiento else ""
                ),
            )
        except Exception:  # noqa: BLE001 — un fallo aquí no anula el tic
            logger.exception("Reabridor de indagación falló; el tic sigue en pie")

        return resultado

    def _elegir_hipotesis(
        self,
        resultado: ResultadoTic,
        triaje: Skill,
        skill_forzada: str | None,
    ) -> Skill | None:
        """Qué hipótesis se usa, y `None` si no hay ninguna que usar.

        El orden de preferencia dice quién manda, y cada escalón tiene su
        razón:

        1. **Lo forzado**, que es alguien pidiendo un protocolo concreto.
           Ni el grafo ni el prompt discuten una orden explícita.
        2. **La ganadora de la competencia**, que es la abducción. Ésta es
           la inversión.
        3. **El triaje**, cuando el grafo no propuso nada admisible: el
           paciente puede no tener todavía conceptos que cubran ningún
           ámbito, y quedarse sin hipótesis por eso sería peor que usar la
           de siempre.

        Y un caso que no es ninguno de los tres: **todas vetadas**. Si el
        grafo propuso candidatas y el veto las retiró todas, no se cae al
        triaje. Sería tapar un hallazgo con el comportamiento anterior: lo
        que el sistema sabe es que *todo lo que este paciente sugiere es
        estructuralmente imposible*, y eso o significa que hay que ampliar
        el ámbito o que los antecedentes están mal. Es un estado clínico
        propio y merece decirse.
        """
        if skill_forzada:
            return triaje

        # El interruptor no apaga la competencia, sólo su voto: el triaje
        # y el grafo siguen corriendo los dos y `triaje_coincide` se
        # registra igual, que es la cifra que decide si esto puede
        # encenderse con fundamento.
        if not self.settings.abduccion_decide:
            return triaje

        if resultado.competencia and all(c.vetada for c in resultado.competencia):
            motivos = [c.motivo_veto for c in resultado.competencia if c.motivo_veto]
            cuantas = len(resultado.competencia)
            resultado.todas_vetadas = (
                (
                    "La única hipótesis que el grafo propone para este paciente "
                    "está vetada: "
                    if cuantas == 1
                    else f"Las {cuantas} hipótesis que el grafo propone para este "
                    "paciente están vetadas: "
                )
                + "; ".join(motivos)
                + ". O hay que ampliar el ámbito de los protocolos, o los "
                "antecedentes que las excluyen están mal registrados."
            )
            logger.warning("%s", resultado.todas_vetadas)
            return None

        if resultado.ganadora_abductiva:
            ganadora = self.skills.cargar(resultado.ganadora_abductiva)
            if ganadora:
                return ganadora
            logger.warning(
                "La competencia eligió '%s' y no se pudo cargar; decide el triaje",
                resultado.ganadora_abductiva,
            )

        return triaje

    async def _segunda_pasada(
        self, texto: str, skill: Skill, resultado: ResultadoTic
    ) -> None:
        """Relee la nota con los hints de la ganadora: la deducción.

        No es repetir la extracción con otro prompt. La pasada 1 corrió a
        ciegas y sin poder interpretar un solo número; ésta corre sabiendo
        qué hipótesis se está sosteniendo, con su vocabulario y con sus
        cortes de laboratorio declarados. Lo que aparece aquí es
        literalmente *lo que la hipótesis predice y la lectura genérica no
        supo ver* — el paso deductivo aplicado al texto que ya está en la
        mano, antes de preguntarle nada al paciente.

        Se fusiona por término y gana la pasada 2: su normalización es
        mejor, porque tenía el vocabulario del protocolo delante. Lo que
        la pasada 1 vio y la 2 no, se conserva: la 2 lee con la hipótesis
        puesta y puede desatender lo que no le concierne, y eso es
        justamente el resto no simbolizado que Φ necesita para delatar una
        hipótesis ajena al paciente.
        """
        try:
            extraidos, _ = await self._extraer(texto, skill)
        except Exception:  # noqa: BLE001 — sin segunda pasada el tic sigue en pie
            logger.exception("La segunda pasada falló; se conserva la genérica")
            return
        if not extraidos:
            return

        hints = skill.hints_snomed()
        nuevos: list[Infon] = []
        for crudo in extraidos:
            infon = await self._validar_hallazgo(crudo, texto, skill, hints)
            if infon:
                nuevos.append(infon)

        por_termino = {_normalizar(i.termino): i for i in resultado.infones}
        anteriores = len(por_termino)
        for infon in nuevos:
            por_termino[_normalizar(infon.termino)] = infon
        resultado.infones = list(por_termino.values())

        logger.info(
            "Segunda pasada con '%s': %d hallazgo(s), %d nuevo(s) sobre los %d "
            "de la lectura genérica",
            skill.nombre,
            len(nuevos),
            len(por_termino) - anteriores,
            anteriores,
        )

    def _competir(self, resultado: ResultadoTic, holon: HolonPaciente) -> None:
        """La regla de selección abductiva, corrida para medir y no para decidir.

        Peirce: se observa el hecho sorprendente C; si A fuera verdadera, C
        sería de curso natural; luego hay razón para sospechar A. Un coseno
        alto es exactamente eso, así que elegir la A que maximiza cos(h,e)
        **es** la regla abductiva y no una analogía de ella.

        La regla tiene cuatro pasos y los cuatro importan:

            1. VETO       por candidata. Una hipótesis imposible no puede
                          aportar un coseno a la comparación: un coseno
                          bonito sobre una imposibilidad es ruido con
                          formato numérico.
            2. ADMISIÓN   α > 0. Sin ninguna procedencia el argumento no
                          está anclado a nada medido, y no compite.
            3. ORDEN      por coseno descendente. Por coseno y no por Φ:
                          ordenar por Φ escogería la mejor documentada en
                          vez de la mejor acoplada, porque α es una
                          propiedad del protocolo y no del paciente.
            4. AVISO      si la de mayor coseno quedó fuera por α, se dice.
                          Es la mitad del diseño: la compuerta callada hace
                          que el sistema trate otra cosa sin explicar por
                          qué. En voz alta, manda a arreglar el índice.

        Las candidatas salen del **grafo del paciente** —los ancestros de
        sus conceptos validados— y no de un prompt. Ésa es la sustitución
        que este paso prepara; hoy sólo la mide.
        """
        validados = resultado.infones_validados
        if not validados:
            return

        codigos = self.validador.index.cobertura_de_grafo(
            i.concepto_id for i in validados if i.concepto_id
        )
        candidatas = self.skills.para_concepto(codigos) if codigos else []
        if not candidatas:
            return

        # El mismo conjunto para todas: se compite contra UN paciente, no
        # contra uno por hipótesis.
        comun = list(holon.linea_tiempo) + validados

        for skill in candidatas:
            fila = CandidataAbductiva(skill=skill.nombre)

            veredicto = None
            try:
                veredicto = self.veredicto.evaluar(skill, comun)
            except Exception:  # noqa: BLE001 — una candidata rota no anula el resto
                logger.exception("Veredicto falló para la candidata '%s'", skill.nombre)
            if veredicto and veredicto.veto:
                fila.vetada = True
                fila.motivo_veto = veredicto.veto.motivo
                resultado.competencia.append(fila)
                continue

            acoplamiento = None
            try:
                acoplamiento = self.acoplamiento.medir(skill, comun)
            except Exception:  # noqa: BLE001
                logger.exception("Φ falló para la candidata '%s'", skill.nombre)
            if acoplamiento is None:
                resultado.competencia.append(fila)
                continue

            # `cobertura is None` dice que el protocolo no declara un solo
            # LR: la lectura ponderada no existe y la clave es la
            # categórica. Las dos leen en la misma unidad —la categórica es
            # la ponderada con pesos uniformes— así que se comparan sin
            # traducir.
            ponderada = acoplamiento.cobertura is not None
            fila.lectura = "ponderada" if ponderada else "categorica"
            fila.clave = (
                acoplamiento.coseno if ponderada else acoplamiento.coseno_categorico
            )
            fila.anclaje = acoplamiento.anclaje
            fila.cobertura = (
                acoplamiento.cobertura if ponderada else acoplamiento.cobertura_categorica
            )
            fila.explicacion = (
                acoplamiento.explicacion
                if ponderada
                else acoplamiento.explicacion_categorica
            )
            fila.admitida = acoplamiento.anclaje > 0 and fila.clave is not None
            resultado.competencia.append(fila)

        ganadora, aviso = self._ordenar_candidatas(resultado.competencia)
        if ganadora is None:
            return

        resultado.ganadora_abductiva = ganadora.skill
        resultado.triaje_coincide = ganadora.skill == resultado.skill_activa
        resultado.aviso_competencia = aviso
        if aviso:
            logger.warning("%s", aviso)

        logger.info(
            "Competencia abductiva: %d candidatas, gana '%s' (%s %.4f); "
            "el triaje dijo '%s' — %s",
            len(resultado.competencia),
            ganadora.skill,
            ganadora.lectura,
            ganadora.clave,
            resultado.skill_activa,
            "coinciden" if resultado.triaje_coincide else "DISCREPAN",
        )

    @staticmethod
    def _ordenar_candidatas(
        filas: Sequence[CandidataAbductiva],
    ) -> tuple[CandidataAbductiva | None, str | None]:
        """Los pasos 3 y 4 de la regla, aparte para poder probarlos solos.

        Se ordena **por coseno y no por Φ**, y ésa es la decisión con
        contenido. Φ = α · cos, y α mide la calidad documental del
        protocolo: es una propiedad del índice, no del paciente. Ordenar
        por Φ escoge la hipótesis mejor documentada en vez de la mejor
        acoplada, y con eso el sistema trataría una diverticulitis a un
        paciente cuya apendicitis encaja con coseno 1.00.

        α no desaparece: actúa como **compuerta** en el paso 2, no como
        peso en el orden. Sin ninguna procedencia el argumento no está
        anclado a nada medido y no compite; con alguna, compite en pie de
        igualdad con las demás y decide el ajuste con el paciente.

        Y si la mejor acoplada quedó fuera por la compuerta, se devuelve
        un aviso. Ese aviso es la mitad del diseño: callada, la compuerta
        hace que el sistema trate otra cosa sin decir por qué; en voz alta
        es una frase verdadera y accionable que manda a arreglar el índice.
        """
        con_clave = [c for c in filas if not c.vetada and c.clave is not None]
        admitidas = [c for c in con_clave if c.admitida]
        if not admitidas:
            return None, None

        # `clave` es opcional en el tipo porque una candidata sin lectura
        # ponderada ni categórica no tiene ninguno. El filtro de arriba ya
        # las quitó, así que el `0.0` no se alcanza: existe para que el tipo
        # afirme lo que hoy sólo garantiza esa línea, tres más arriba.
        def coseno(c: CandidataAbductiva) -> float:
            return c.clave if c.clave is not None else 0.0

        ganadora = max(admitidas, key=coseno)
        mejor = max(con_clave, key=coseno)
        if mejor.admitida:
            return ganadora, None

        return ganadora, (
            f"La hipótesis que mejor encaja con este paciente es '{mejor.skill}', "
            f"coseno {mejor.clave:.2f}, y no compite porque su protocolo no cita "
            f"sus cocientes (α = {mejor.anclaje:.2f}). Se usa '{ganadora.skill}', "
            f"coseno {ganadora.clave:.2f}."
        )

    async def _extraer(self, texto: str, skill: Skill, generica: bool = False):
        """El LLM propone hallazgos. Nada se da por bueno todavía.

        `generica` es la primera de las dos pasadas: extrae sin protocolo
        porque el protocolo es justo lo que se está eligiendo. Usa un
        prompt que prohíbe interpretar números —sin cortes declarados, el
        modelo se los inventa— y lo que salga pasa además por
        `_sin_cortes_inventados`, que lo comprueba en vez de confiar.
        """
        if generica:
            prompt = PROMPT_EXTRACCION_GENERICA
        else:
            vocabulario = ""
            preferidos = skill.vocabulario_preferido()
            if preferidos:
                vocabulario = f"VOCABULARIO PREFERIDO: {preferidos}"

            prompt = PROMPT_EXTRACCION.format(
                protocolo=skill.para_prompt(self.settings.formato_protocolo)[:8000],
                vocabulario=vocabulario,
            )

        try:
            data = await self.llm.generar_json(
                f"{prompt}\n\nNARRATIVA CLÍNICA:\n{texto}\n\nJSON:",
                model=self.settings.model_clinical,
                timeout=self.settings.llm_timeout_slow,
                num_ctx=8192,
            )
        except LLMUnavailable as exc:
            logger.error("Extracción imposible: %s", exc)
            return [], f"Extracción no disponible: {exc}"

        crudos = data.get("infones")
        if not isinstance(crudos, list):
            return [], data.get("resumen", "")

        limpios = [
            item
            for item in crudos
            if isinstance(item, dict) and str(item.get("termino_clinico", "")).strip()
        ]

        if generica:
            limpios, retirados = _sin_cortes_inventados(
                limpios, _terminos_autorizados(skill)
            )
            if retirados:
                logger.info(
                    "Pasada genérica: %d interpretación(es) de números retirada(s) "
                    "por no tener corte declarado: %s",
                    len(retirados),
                    ", ".join(retirados),
                )

        return limpios, str(data.get("resumen", ""))

    async def _validar_hallazgo(
        self,
        crudo: dict[str, str],
        texto_original: str,
        skill: Skill,
        hints: dict[str, str],
    ) -> Infon | None:
        termino = str(crudo.get("termino_clinico", "")).strip()
        cita = str(crudo.get("texto_origen", "")).strip()
        if not termino:
            return None

        # Por defecto presente: si el modelo no se pronuncia, no vamos a
        # inventarle una ausencia, que es la dirección peligrosa.
        presente = crudo.get("presente", True)
        polaridad = Polaridad.AUSENTE if presente is False else Polaridad.PRESENTE

        # CAPAS 0-1-2: ¿existe este concepto en la ontología?
        match = await self.validador.validar(termino, hints=hints)

        # CAPA 3: ¿lo sostiene la evidencia? Sólo se audita si la ontología
        # dio una señal mínima — auditar ruido es gastar cómputo en nada.
        certeza_logica = 0.0
        razon = "No auditado (score ontológico insuficiente)"
        es_logico = False

        if match.score >= self.settings.threshold_audit:
            auditoria = await self.verificador.auditar(
                termino,
                texto_original,
                skill.para_prompt(self.settings.formato_protocolo),
                ausente=(polaridad is Polaridad.AUSENTE),
            )
            es_logico = auditoria.es_valido
            razon = auditoria.razon
            certeza_logica = auditoria.certeza

        # Veredicto
        if match.score >= self.settings.threshold_validated and es_logico:
            estado = EstadoInfon.VALIDADO
            confianza = match.score * PESO_ONTOLOGICO + certeza_logica * PESO_LOGICO
        elif match.score >= self.settings.threshold_alert:
            # Acierto ontológico sin respaldo lógico: se muestra al clínico
            # marcado, nunca se descarta en silencio ni se da por bueno.
            estado = EstadoInfon.ALERTA
            confianza = match.score
        else:
            estado = EstadoInfon.RUIDO
            confianza = match.score

        # Un infón descartado conserva lo que dijo el clínico, no lo que el
        # motor estuvo a punto de elegir: mostrar "otro concepto" donde el
        # médico escribió "coluria" confundiría al revisar el descarte. El
        # casi-match queda en la traza, que es donde sirve para auditar.
        if estado == EstadoInfon.RUIDO:
            termino_final = termino
            concepto_id = codigo = sistema = cie10 = linaje = None
            if match.codigo:
                razon = f"descartado (casi coincidió con '{match.termino}'): {razon}"
        else:
            termino_final = match.termino
            concepto_id, codigo, sistema = match.concepto_id, match.codigo, match.sistema
            cie10, linaje = match.cie10, match.linaje

        return Infon(
            texto_origen=cita or texto_original[:120],
            termino_propuesto=termino,
            termino=termino_final,
            polaridad=polaridad,
            codigo=codigo,
            sistema=sistema,
            concepto_id=concepto_id,
            cie10_code=cie10,
            linaje_clinico=linaje,
            estado=estado,
            confianza=round(confianza, 2),
            score_ontologico=round(match.score, 2),
            score_logico=round(certeza_logica, 2),
            razon_auditoria=f"[{match.metodo}] {razon}",
            origen_skill=skill.nombre,
        )
