"""Criterios de clasificación diagnóstica: de hallazgos a trastorno.

Es el paso que da el clínico experimentado cuando reúne varios hallazgos
anormales y acuña un término nuevo. Ese paso no es libre ni subjetivo:
existen criterios de clasificación publicados —Atlanta para pancreatitis,
Duke para endocarditis, ACR/EULAR para enfermedades reumáticas, Light para
derrames— que definen cuándo un caso *cuenta como* la entidad, y que se
usan en los propios estudios de los que salen los likelihood ratios.

Parecen lógica booleana y en el fondo son bayesianos. La estructura típica
es constante:

    manifestación de alta sospecha  →  fija la probabilidad pre-test
  + prueba sensible                 →  su LR- descarta si es negativa
  + prueba específica               →  su LR+ confirma si es positiva

El «2 de 3» es la abreviatura, acordada por un panel de consenso, de que el
posterior cruza el umbral de tratamiento. Por eso este módulo devuelve las
dos lecturas —qué criterios se cumplen y con qué probabilidad— en vez de
elegir una: son el mismo cálculo a distinta resolución.

Dos reglas de seguridad:

* Sólo satisfacen criterios los infones **VALIDADO y presentes**. Un
  hallazgo en alerta no puede acuñar un diagnóstico.
* El trastorno derivado hereda la confianza más baja de los hallazgos que
  lo sostienen. Un diagnóstico no puede ser más firme que su evidencia más
  floja, por mucho que venga con criterios y cita.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

from ..models import EstadoInfon, Infon, Polaridad
from .skills import Clasificacion, Criterio, Skill

logger = logging.getLogger(__name__)

# Roles cuya falta de información merece interrumpir al clínico. Un signo
# de apoyo que no consta no cambia la conducta; una prueba sensible que no
# se ha pedido impide descartar, y eso sí.
ROLES_QUE_PIDEN = ("manifestacion", "prueba_sensible", "prueba_especifica", "imagen")

POR_QUE_IMPORTA = {
    "prueba_sensible": "sin ella no se puede descartar",
    "prueba_especifica": "sin ella no se puede confirmar",
    "manifestacion": "define la sospecha de partida",
    "imagen": "es uno de los criterios diagnósticos",
}


class EstadoCriterio(str, Enum):
    """Un criterio no cumplido no siempre significa lo mismo.

    Distinguir «se buscó y no está» de «no se buscó» es la diferencia
    entre una prueba negativa —que descarta— y un vacío —que se pregunta.
    Confundirlos convertiría un silencio en evidencia.
    """

    SATISFECHO = "satisfecho"       # hay hallazgo presente que lo cumple
    DESCARTADO = "descartado"       # consta explícitamente que no está
    SIN_CONFIRMAR = "sin_confirmar"  # hay dato, pero no superó la auditoría
    SIN_DATOS = "sin_datos"         # nadie lo ha mirado: esto se pregunta


@dataclass
class CriterioEvaluado:
    criterio: Criterio
    estado: EstadoCriterio
    por: list[Infon] = field(default_factory=list)

    @property
    def satisfecho(self) -> bool:
        return self.estado is EstadoCriterio.SATISFECHO

    @property
    def descripcion(self) -> str:
        terminos = ", ".join(i.termino for i in self.por)
        if self.estado is EstadoCriterio.SATISFECHO:
            return f"{self.criterio.nombre}: sí ({terminos})"
        if self.estado is EstadoCriterio.DESCARTADO:
            return f"{self.criterio.nombre}: no ({terminos})"
        if self.estado is EstadoCriterio.SIN_CONFIRMAR:
            return f"{self.criterio.nombre}: sin confirmar ({terminos})"
        return f"{self.criterio.nombre}: sin datos"


@dataclass
class Vacio:
    """Un criterio que impide concluir, con lo que habría que hacer.

    Distingue dos peticiones que no son la misma: pedir una prueba que no
    se ha hecho, y confirmar un dato que sí está pero no superó la
    auditoría. Pedir de nuevo algo ya hecho es la vía rápida para que el
    clínico deje de leer los avisos.
    """

    criterio: str
    rol: str
    conceptos: list[str]
    hay_dato: bool = False
    terminos: list[str] = field(default_factory=list)

    @property
    def sugerencia(self) -> str:
        if self.hay_dato:
            visto = ", ".join(self.terminos) or self.criterio.lower()
            return f"Revisa «{visto}»: hay dato pero la auditoría no lo confirmó."
        motivo = POR_QUE_IMPORTA.get(self.rol, "es un criterio diagnóstico")
        return f"No consta {self.criterio.lower()}; {motivo}."


@dataclass
class ResultadoClasificacion:
    """Veredicto de los criterios, con su desglose."""

    nombre: str
    fuente: str
    requiere: int
    evaluados: list[CriterioEvaluado] = field(default_factory=list)
    trastorno: Infon | None = None

    @property
    def satisfechos(self) -> int:
        return sum(1 for e in self.evaluados if e.satisfecho)

    @property
    def cumple(self) -> bool:
        return self.requiere > 0 and self.satisfechos >= self.requiere

    @property
    def resumen(self) -> str:
        return f"{self.nombre}: {self.satisfechos} de {self.requiere} criterios"

    def desglose(self) -> list[str]:
        return [e.descripcion for e in self.evaluados]

    @property
    def vacios(self) -> list[Vacio]:
        """Criterios sin información, que es lo que hay que preguntar.

        Sólo cuando aún pueden cambiar el veredicto: si los criterios ya
        se cumplen, pedir más pruebas es sobrediagnóstico, no rigor.
        """
        if self.cumple:
            return []
        return [
            Vacio(
                criterio=e.criterio.nombre,
                rol=e.criterio.rol,
                conceptos=list(e.criterio.satisface_si),
                hay_dato=e.estado is EstadoCriterio.SIN_CONFIRMAR,
                terminos=[i.termino for i in e.por],
            )
            for e in self.evaluados
            if e.estado
            in (EstadoCriterio.SIN_DATOS, EstadoCriterio.SIN_CONFIRMAR)
            and e.criterio.rol in ROLES_QUE_PIDEN
        ]

    @property
    def alcanzable(self) -> bool:
        """¿Podría llegar a cumplirse si se resolvieran los vacíos?"""
        posibles = self.satisfechos + sum(
            1
            for e in self.evaluados
            if e.estado
            in (EstadoCriterio.SIN_DATOS, EstadoCriterio.SIN_CONFIRMAR)
        )
        return self.requiere > 0 and posibles >= self.requiere


class Clasificador:
    """Evalúa los criterios de un protocolo sobre los infones de un tic."""

    def evaluar(
        self,
        skill: Skill,
        infones: list[Infon],
    ) -> ResultadoClasificacion | None:
        clasificacion: Clasificacion = skill.clasificacion
        if not clasificacion.declarada:
            return None  # El protocolo no declara criterios: no se inventan.

        # Sólo cuenta la evidencia firme. Un hallazgo en alerta —el
        # concepto existe pero la auditoría no lo confirmó— no puede
        # satisfacer un criterio diagnóstico.
        presentes = [i for i in infones if i.confirma]
        ausentes = [i for i in infones if i.descarta]
        # Un hallazgo que no superó la auditoría no satisface ni descarta,
        # pero demuestra que alguien miró. Confundirlo con «no hay datos»
        # haría que el sistema pidiera una prueba ya realizada.
        sin_confirmar = [i for i in infones if not i.es_valido]

        resultado = ResultadoClasificacion(
            nombre=clasificacion.nombre,
            fuente=clasificacion.fuente,
            requiere=clasificacion.requiere,
        )

        for criterio in clasificacion.criterios:
            aceptados = [i for i in presentes if self._satisface(i, criterio)]
            if aceptados:
                estado, por = EstadoCriterio.SATISFECHO, aceptados
            else:
                negados = [i for i in ausentes if self._satisface(i, criterio)]
                dudosos = [i for i in sin_confirmar if self._satisface(i, criterio)]
                # Se buscó y no está, se buscó y no se pudo confirmar, o no
                # lo ha mirado nadie. Los tres exigen conductas distintas.
                if negados:
                    estado, por = EstadoCriterio.DESCARTADO, negados
                elif dudosos:
                    estado, por = EstadoCriterio.SIN_CONFIRMAR, dudosos
                else:
                    estado, por = EstadoCriterio.SIN_DATOS, []
            resultado.evaluados.append(CriterioEvaluado(criterio, estado, por))

        if resultado.cumple:
            resultado.trastorno = self._acunar(clasificacion, resultado, skill)

        return resultado

    @staticmethod
    def _satisface(infon: Infon, criterio: Criterio) -> bool:
        """¿Este hallazgo satisface el criterio?

        Se compara por código, no por término: el criterio referencia
        conceptos del vocabulario, y un mismo concepto puede haber entrado
        por cualquiera de sus sinónimos.
        """
        if infon.codigo and infon.codigo in criterio.satisface_si:
            return True
        # Respaldo por nombre, para criterios que citan un término sin
        # código o cuando el vocabulario no estaba cargado.
        objetivo = infon.termino.strip().lower()
        return any(c.strip().lower() == objetivo for c in criterio.satisface_si)

    @staticmethod
    def _acunar(
        clasificacion: Clasificacion,
        resultado: ResultadoClasificacion,
        skill: Skill,
    ) -> Infon:
        """Crea el infón de nivel 2: el trastorno derivado."""
        produce = clasificacion.produce
        sostienen = [i for e in resultado.evaluados if e.satisfecho for i in e.por]

        # Un diagnóstico no puede ser más firme que su evidencia más floja.
        confianza = min((i.confianza for i in sostienen), default=0.0)

        codigos = produce.get("codigos") or {}
        sistema, codigo = None, None
        for candidato in ("holonmed", "snomed", "icd10"):
            if candidato in codigos:
                sistema, codigo = candidato, str(codigos[candidato])
                break

        cumplidos = "; ".join(
            e.descripcion for e in resultado.evaluados if e.satisfecho
        )
        fuente = f" [{clasificacion.fuente}]" if clasificacion.fuente else ""

        return Infon(
            # Su procedencia no es una cita de la narrativa sino los
            # hallazgos que lo sostienen. Es lo que lo hace desplegable.
            texto_origen=cumplidos,
            termino_propuesto=str(produce.get("termino", "")),
            termino=str(produce.get("termino", "")),
            polaridad=Polaridad.PRESENTE,
            codigo=codigo,
            sistema=sistema,
            derivado_de=[i.termino for i in sostienen],
            criterio=clasificacion.nombre,
            estado=EstadoInfon.VALIDADO,
            confianza=round(confianza, 2),
            score_ontologico=100.0,
            score_logico=confianza,
            razon_auditoria=(
                f"Derivado por {resultado.resumen}{fuente}. {cumplidos}"
            ),
            origen_skill=skill.nombre,
        )
