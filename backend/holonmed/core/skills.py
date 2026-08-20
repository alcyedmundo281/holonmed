"""Skills clínicas: los protocolos que el sistema puede activar.

Una *skill* es un archivo Markdown con dos partes que cumplen funciones
distintas:

* **Frontmatter YAML** — conocimiento estructurado que consume el código:
  códigos verificados, puntos de corte de laboratorio, likelihood ratios y
  el ámbito del grafo sobre el que actúa el protocolo.
* **Cuerpo Markdown** — instrucciones en prosa que entran en el prompt del
  modelo.

Antes el conocimiento estructurado iba en bloques JSON embebidos en la
prosa, que había que rascar con expresiones regulares y limpiar de
`&nbsp;`, escapes y vallas de código. Un error de sintaxis producía un
skill silenciosamente vacío: sin hints, sin cortes y sin modelo bayesiano,
pero cargado y en uso. El frontmatter se parsea de forma determinista y
falla de forma ruidosa, que es lo que se quiere de algo que decide qué
hallazgos entran en una historia clínica.

Se mantiene la lectura del formato antiguo para no romper protocolos
escritos antes del cambio.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..config import Settings, get_settings
from ..llm import OllamaClient

logger = logging.getLogger(__name__)

SKILL_POR_DEFECTO = "general_triage"

# Sistema de codificación preferido al resolver un hint. El semilla del
# proyecto va primero porque es el único que está garantizado presente.
PRIORIDAD_SISTEMAS = ("holonmed", "snomed", "hpo", "icd10")

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


# Papel de un signo dentro del razonamiento diagnóstico. No es una
# etiqueta descriptiva: determina en qué dirección mueve la probabilidad.
#
#   manifestacion      fija la probabilidad pre-test
#   prueba_sensible    su LR- descarta cuando es negativa (SnNOut)
#   prueba_especifica  su LR+ confirma cuando es positiva  (SpPIn)
#   apoyo              aporta poco por sí solo
ROLES = ("manifestacion", "prueba_sensible", "prueba_especifica", "apoyo", "imagen")

# Cómo entra un signo en la DECISIÓN, que es un eje distinto de `rol`.
# `rol` dice qué clase de signo es —una manifestación, una prueba sensible—;
# `efecto` dice qué hace con el diagnóstico. Una prueba específica es a la vez
# `prueba_especifica` y `apoya`. Una apendicectomía no es una prueba, no tiene
# cociente de verosimilitud, y sin embargo decide: excluye.
#
# La forma viene de los criterios MDS 2015 para Parkinson (Postuma RB et al,
# Mov Disord 2015;30:1591-601), que separan explícitamente los tres niveles:
# criterios de exclusión absoluta, banderas rojas contrarrestables, y
# criterios de apoyo.
EFECTOS = ("apoya", "bandera_roja", "excluye")
POLARIDADES = ("presente", "ausente")


@dataclass
class Signo:
    """Un signo o síntoma que el protocolo reconoce."""

    nombre: str
    codigos: dict[str, str] = field(default_factory=dict)
    rol: str = "apoyo"
    lr: float | None = None            # LR+ (alias histórico: `lr`)
    lr_negativo: float | None = None   # LR- cuando consta como ausente
    fuente: str = ""

    # Los dos ejes de la decisión. Por defecto un signo apoya cuando está
    # presente, que es lo que declaran todos los protocolos escritos antes
    # de existir estas claves: así siguen valiendo sin tocarlos.
    efecto: str = "apoya"
    dispara_si: str = "presente"       # la polaridad que activa el efecto

    @property
    def polaridad_adversa(self) -> str:
        """La polaridad que va EN CONTRA del diagnóstico.

        Para un apoyo es la contraria a la que lo dispara: si la fiebre
        apoya estando presente, su ausencia documentada resta. Para una
        bandera roja es la que la dispara: si la bandera es «no hay dolor
        en fosa ilíaca derecha», la ausencia es lo que resta.
        """
        if self.efecto == "bandera_roja":
            return self.dispara_si
        return "ausente" if self.dispara_si == "presente" else "presente"

    @property
    def lr_positivo(self) -> float | None:
        return self.lr

    def codigo_preferido(self) -> tuple[str, str] | None:
        for sistema in PRIORIDAD_SISTEMAS:
            if sistema in self.codigos:
                return sistema, str(self.codigos[sistema])
        if self.codigos:
            sistema = next(iter(self.codigos))
            return sistema, str(self.codigos[sistema])
        return None


@dataclass
class CriterioLaboratorio:
    """Un punto de corte que convierte una cifra en un concepto clínico."""

    parametro: str
    corte_superior: float | None = None
    corte_inferior: float | None = None
    multiplicador: float | None = None
    termino_si_alto: str = ""
    termino_si_bajo: str = ""
    codigos: dict[str, str] = field(default_factory=dict)

    def terminos(self) -> list[str]:
        return [t for t in (self.termino_si_alto, self.termino_si_bajo) if t]


@dataclass
class Criterio:
    """Un criterio de clasificación diagnóstica.

    Se satisface si alguno de sus conceptos aparece entre los hallazgos
    validados y presentes.
    """

    nombre: str
    rol: str = "apoyo"
    satisface_si: list[str] = field(default_factory=list)


@dataclass
class CampoOperativo:
    """Un dato que el registro de un rol debe contener.

    Cada actor documenta cosas distintas: enfermería necesita el horario
    indicado y el administrado; farmacia, el lote y las condiciones de
    elaboración. En vez de codificar esas diferencias, cada rol las declara
    en su propio protocolo.

    Un registro al que le falte un campo obligatorio no se puede facturar,
    y ésa es una causa real de que los procedimientos se queden sin cobrar:
    no es que no se hagan, es que se documentan a medias.
    """

    nombre: str
    etiqueta: str = ""
    requerido: bool = False
    descripcion: str = ""

    @property
    def titulo(self) -> str:
        return self.etiqueta or self.nombre.replace("_", " ").capitalize()


@dataclass
class Clasificacion:
    """Criterios publicados que convierten hallazgos en un trastorno.

    Es el paso que da el clínico experimentado cuando reúne varios
    hallazgos anormales y acuña un término nuevo. No es subjetivo: hay
    criterios de clasificación usados en investigación —Atlanta, Duke,
    ACR/EULAR, Light— que definen cuándo un caso *cuenta como* la entidad.

    Parecen booleanos y en el fondo son bayesianos: la manifestación fija
    la probabilidad pre-test, la prueba sensible descarta si es negativa y
    la específica confirma si es positiva. El «2 de 3» es la abreviatura,
    acordada por un panel, de que el posterior cruza el umbral.
    """

    nombre: str = ""
    fuente: str = ""
    requiere: int = 0
    criterios: list[Criterio] = field(default_factory=list)
    produce: dict[str, Any] = field(default_factory=dict)

    @property
    def declarada(self) -> bool:
        return bool(self.criterios and self.produce.get("termino"))


@dataclass
class Nucleo:
    """El rasgo central sin el cual el criterio ni siquiera se aplica.

    MDS lo dice en ese orden: primero se documenta el parkinsonismo motor
    —bradicinesia más temblor de reposo o rigidez— y **sólo después** se
    determina si la causa es la enfermedad de Parkinson. Sin el núcleo no
    hay criterio que evaluar.

    No es una exclusión: no dice que el diagnóstico sea imposible, dice que
    la pregunta todavía no se puede hacer. Y no es un apoyo: no suma, es
    condición previa.

    Su ausencia es lo que impide el fallo que este bloque vino a tapar: sin
    núcleo, un balance que admite «cero apoyos mínimos» daba por probable
    un diagnóstico en un paciente del que no consta absolutamente nada.
    """

    requiere: list[str] = field(default_factory=list)          # todos
    y_al_menos_uno_de: list[str] = field(default_factory=list)  # al menos uno

    @property
    def declarado(self) -> bool:
        return bool(self.requiere or self.y_al_menos_uno_de)

    def satisfecho(self, empareja) -> bool:
        """`empareja(termino)` decide si ese término consta como presente.

        Se recibe el emparejador en vez de un conjunto de cadenas para que
        el núcleo case igual que todo lo demás: por subcadena, con
        `bayes.emparejar_termino`. Comparar aquí por igualdad exacta hacía
        que un infón «Bradicinesia leve» satisficiera un signo y no el
        núcleo — la clase de divergencia silenciosa que la §3.3 de
        ACOPLAMIENTO.md existe para impedir.
        """
        if any(not empareja(t) for t in self.requiere):
            return False
        if self.y_al_menos_uno_de:
            return any(empareja(t) for t in self.y_al_menos_uno_de)
        return True


@dataclass
class NivelCerteza:
    """Un grado de certeza declarado, con su regla de conteo.

    MDS 2015 declara dos: «establecida», que maximiza especificidad
    exigiendo dos apoyos y ninguna bandera roja, y «probable», que
    equilibra permitiendo hasta dos banderas si van contrarrestadas.
    """

    nombre: str
    apoyos_minimos: int = 0
    banderas_maximas: int = 0
    contrapeso: int = 0   # apoyos exigidos POR CADA bandera roja presente

    def satisface(self, apoyos: int, banderas: int) -> bool:
        if apoyos < self.apoyos_minimos:
            return False
        if banderas > self.banderas_maximas:
            return False
        return apoyos >= banderas * self.contrapeso


@dataclass
class Balance:
    """La regla que equilibra apoyos contra banderas rojas.

    No se deriva: se declara, igual que los likelihood ratios. Quien
    escribe el criterio publicado fija los enteros —«al menos dos
    apoyos», «uno por uno», «máximo dos banderas»— y el sistema los
    aplica. Buscar un umbral universal por simulación fue un error de
    categoría: el umbral es específico de la enfermedad y lo pone el panel
    que redacta el criterio.

    Los niveles se evalúan en el orden en que se declaran, del más
    estricto al más laxo, y gana el primero que se satisface.
    """

    niveles: list[NivelCerteza] = field(default_factory=list)
    fuente: str = ""

    @property
    def declarado(self) -> bool:
        return bool(self.niveles)

    @property
    def banderas_tolerables(self) -> int:
        """El tope duro: ni el nivel más laxo admite más que esto.

        Superarlo no es «peor balance», es un veto. Medido contra MDS: un
        coseno es continuo y monótono en el balance, así que no puede
        expresar un tope — cuatro apoyos con tres banderas sale rechazado
        por el criterio y con Φ positiva. El tope va fuera del coeficiente.
        """
        return max((n.banderas_maximas for n in self.niveles), default=0)


@dataclass
class ModeloBayesiano:
    probabilidad_base: float = 0.0
    factores_riesgo: dict[str, float] = field(default_factory=dict)

    @property
    def declarado(self) -> bool:
        return self.probabilidad_base > 0


class Skill:
    """Un protocolo clínico cargado y parseado."""

    def __init__(self, nombre: str, contenido: str):
        self.nombre = nombre
        self.contenido_completo = contenido

        meta, cuerpo = self._separar(contenido)
        self.meta: dict[str, Any] = meta
        # El cuerpo es lo que entra en el prompt. El frontmatter no: es
        # para el código, y meterlo confundiría al modelo con sintaxis
        # que no necesita interpretar.
        self.cuerpo = cuerpo

        self.titulo: str = str(meta.get("titulo") or nombre)
        self.version: str = str(meta.get("version", "0"))
        self.condicion: dict[str, Any] = meta.get("condicion") or {}
        self.ambito_grafo: list[str] = [str(a) for a in (meta.get("ambito_grafo") or [])]
        # 'clinico' extrae hallazgos; 'documento' sólo da formato a algo
        # que el profesional ya decidió (una receta, un informe).
        self.tipo: str = str(meta.get("tipo", "clinico"))

        self.signos = self._parsear_signos()
        self.laboratorio = self._parsear_laboratorio()
        self.bayes = self._parsear_bayes()
        self.balance = self._parsear_balance()
        self.nucleo = self._parsear_nucleo()
        self.clasificacion = self._parsear_clasificacion()
        # Un protocolo operativo pertenece a un rol y declara qué debe
        # contener su registro. Se busca por este campo y no por el nombre
        # del archivo: cada centro nombra sus protocolos como quiera.
        self.rol: str = str(meta.get("rol", ""))
        self.campos = self._parsear_campos()

    # --- Parseo -------------------------------------------------------

    def _separar(self, contenido: str) -> tuple[dict[str, Any], str]:
        match = _FRONTMATTER.match(contenido)
        if not match:
            return self._migrar_formato_antiguo(contenido)

        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            # Ruidoso a propósito: un frontmatter roto deja el protocolo
            # sin códigos ni cortes, y eso no puede pasar en silencio.
            logger.error("Frontmatter inválido en '%s': %s", self.nombre, exc)
            return {}, match.group(2)

        if not isinstance(meta, dict):
            logger.error("El frontmatter de '%s' no es un mapa YAML", self.nombre)
            return {}, match.group(2)
        return meta, match.group(2)

    def _migrar_formato_antiguo(self, contenido: str) -> tuple[dict[str, Any], str]:
        """Lee protocolos con JSON-LD embebido en la prosa.

        Formato anterior al frontmatter. Se traduce al vuelo para que los
        skills antiguos sigan funcionando sin reescribirlos.
        """
        import json

        limpio = (
            contenido.replace("&nbsp;", " ").replace("\xa0", " ").replace("\\", "")
        )
        inicio, fin = limpio.find("{"), limpio.rfind("}")
        if inicio == -1 or fin <= inicio:
            return {}, contenido

        try:
            crudo = json.loads(limpio[inicio : fin + 1])
        except json.JSONDecodeError:
            return {}, contenido
        if not isinstance(crudo, dict):
            return {}, contenido

        logger.info("Skill '%s' usa el formato antiguo; se traduce", self.nombre)
        modelo = crudo.get("modelo_bayesiano") or {}
        criterios = (crudo.get("criterios_laboratorio") or {}).get("reglas") or []

        def codigos(d: dict) -> dict[str, str]:
            cid = d.get("snomed_id") or (d.get("code") or {}).get("codeValue")
            return {"snomed": str(cid)} if cid else {}

        return {
            "titulo": crudo.get("name", self.nombre),
            "condicion": {"nombre": crudo.get("name"), "codigos": codigos(crudo)},
            "modelo_bayesiano": {
                "probabilidad_base": modelo.get("probabilidad_base", 0),
                "factores_riesgo": {
                    k: v
                    for k, v in (modelo.get("factores_riesgo_a_priori") or {}).items()
                    if not k.startswith("_")
                },
            },
            "signos": [
                {
                    "nombre": s.get("name"),
                    "codigos": codigos(s),
                    "lr": s.get("bayes_lr"),
                    "fuente": s.get("description", ""),
                }
                for s in (crudo.get("signDetected") or [])
                if isinstance(s, dict) and s.get("name")
            ],
            "laboratorio": [
                {
                    "parametro": r.get("parametro"),
                    "corte_superior": r.get("corte_superior"),
                    "corte_inferior": r.get("corte_inferior")
                    or r.get("corte_inferior_sistolica"),
                    "multiplicador": r.get("multiplicador_pancreatitis"),
                    "termino_si_alto": r.get("termino_si_alto", ""),
                    "termino_si_bajo": r.get("termino_si_bajo", ""),
                    "codigos": codigos(r),
                }
                for r in criterios
                if isinstance(r, dict)
            ],
        }, contenido

    def _parsear_signos(self) -> list[Signo]:
        salida = []
        for s in self.meta.get("signos") or []:
            if not isinstance(s, dict) or not s.get("nombre"):
                continue
            rol = str(s.get("rol", "apoyo"))
            efecto = str(s.get("efecto", "apoya"))
            dispara = str(s.get("dispara_si", "presente"))
            salida.append(
                Signo(
                    nombre=str(s["nombre"]),
                    codigos={k: str(v) for k, v in (s.get("codigos") or {}).items()},
                    rol=rol if rol in ROLES else "apoyo",
                    lr=_num(s.get("lr") if "lr" in s else s.get("lr_positivo")),
                    lr_negativo=_num(s.get("lr_negativo")),
                    fuente=str(s.get("fuente", "")),
                    efecto=efecto if efecto in EFECTOS else "apoya",
                    dispara_si=dispara if dispara in POLARIDADES else "presente",
                )
            )
        return salida

    def _parsear_campos(self) -> list[CampoOperativo]:
        salida = []
        for c in self.meta.get("campos") or []:
            if isinstance(c, str):
                salida.append(CampoOperativo(nombre=c))
                continue
            if not isinstance(c, dict) or not c.get("nombre"):
                continue
            salida.append(
                CampoOperativo(
                    nombre=str(c["nombre"]),
                    etiqueta=str(c.get("etiqueta", "")),
                    requerido=bool(c.get("requerido", False)),
                    descripcion=str(c.get("descripcion", "")),
                )
            )
        return salida

    @property
    def campos_requeridos(self) -> list[CampoOperativo]:
        return [c for c in self.campos if c.requerido]

    def _parsear_clasificacion(self) -> Clasificacion:
        bloque = self.meta.get("clasificacion")
        if not isinstance(bloque, dict):
            return Clasificacion()

        criterios = []
        for c in bloque.get("criterios") or []:
            if not isinstance(c, dict):
                continue
            codigos = [str(x) for x in (c.get("satisface_si") or [])]
            if not codigos:
                continue
            rol = str(c.get("rol", "apoyo"))
            criterios.append(
                Criterio(
                    nombre=str(c.get("nombre") or rol),
                    rol=rol if rol in ROLES else "apoyo",
                    satisface_si=codigos,
                )
            )

        return Clasificacion(
            nombre=str(bloque.get("nombre", "")),
            fuente=str(bloque.get("fuente", "")),
            requiere=int(bloque.get("requiere", 0) or 0),
            criterios=criterios,
            produce=bloque.get("produce") or {},
        )

    def _parsear_nucleo(self) -> Nucleo:
        bloque = self.meta.get("nucleo")
        if not isinstance(bloque, dict):
            return Nucleo()
        return Nucleo(
            requiere=[str(x) for x in (bloque.get("requiere") or [])],
            y_al_menos_uno_de=[
                str(x) for x in (bloque.get("y_al_menos_uno_de") or [])
            ],
        )

    def _parsear_balance(self) -> Balance:
        bloque = self.meta.get("balance")
        if not isinstance(bloque, dict):
            return Balance()
        niveles = []
        for nombre, regla in bloque.items():
            if nombre == "fuente" or not isinstance(regla, dict):
                continue
            niveles.append(
                NivelCerteza(
                    nombre=str(nombre),
                    apoyos_minimos=int(regla.get("apoyos_minimos", 0) or 0),
                    banderas_maximas=int(regla.get("banderas_maximas", 0) or 0),
                    contrapeso=int(regla.get("contrapeso", 0) or 0),
                )
            )
        return Balance(niveles=niveles, fuente=str(bloque.get("fuente", "")))

    def _parsear_laboratorio(self) -> list[CriterioLaboratorio]:
        salida = []
        for r in self.meta.get("laboratorio") or []:
            if not isinstance(r, dict) or not r.get("parametro"):
                continue
            salida.append(
                CriterioLaboratorio(
                    parametro=str(r["parametro"]),
                    corte_superior=_num(r.get("corte_superior")),
                    corte_inferior=_num(r.get("corte_inferior")),
                    multiplicador=_num(r.get("multiplicador")),
                    termino_si_alto=str(r.get("termino_si_alto", "")),
                    termino_si_bajo=str(r.get("termino_si_bajo", "")),
                    codigos={k: str(v) for k, v in (r.get("codigos") or {}).items()},
                )
            )
        return salida

    def _parsear_bayes(self) -> ModeloBayesiano:
        m = self.meta.get("modelo_bayesiano") or {}
        if not isinstance(m, dict):
            return ModeloBayesiano()
        factores = {
            str(k).lower(): float(v)
            for k, v in (m.get("factores_riesgo") or {}).items()
            if isinstance(v, (int, float)) and not str(k).startswith("_")
        }
        return ModeloBayesiano(
            probabilidad_base=_num(m.get("probabilidad_base")) or 0.0,
            factores_riesgo=factores,
        )

    # --- Consumo ------------------------------------------------------

    @property
    def descripcion(self) -> str:
        """Frase que ve el triaje al elegir protocolo."""
        if self.meta.get("descripcion"):
            return str(self.meta["descripcion"])
        if self.meta.get("titulo"):
            return str(self.meta["titulo"])
        for linea in self.cuerpo.splitlines():
            limpia = linea.strip().lstrip("#").strip()
            if limpia:
                return limpia
        return self.nombre

    @property
    def contenido(self) -> str:
        """Sólo la prosa, sin el frontmatter."""
        return self.cuerpo.strip() or self.contenido_completo

    # --- Proyección al prompt ------------------------------------------
    #
    # El frontmatter es la fuente de verdad y lo consume el código, pero el
    # modelo también necesita parte de ese conocimiento: no puede comparar
    # un valor contra un corte que nadie le ha dicho.
    #
    # Excluirlo del prompt fue un error concreto y medible: al auditar
    # "lipasa 890" el modelo escribió ">3x el límite normal (aprox.
    # 250-300)" cuando el protocolo declara 60. Se lo inventó porque no
    # tenía otro número.
    #
    # De ahí que haya varios formatos: cómo se presenta la misma
    # información cambia si el modelo la encuentra o la fabrica.

    FORMATOS = ("minimo", "prosa", "etiquetas")

    def para_prompt(self, formato: str = "etiquetas") -> str:
        """Renderiza el protocolo tal como lo verá el modelo."""
        cuerpo = self.contenido
        if formato == "minimo":
            return cuerpo
        bloque = (
            self._contexto_etiquetas()
            if formato == "etiquetas"
            else self._contexto_prosa()
        )
        return "\n\n".join([cuerpo, bloque]) if bloque else cuerpo

    def _contexto_prosa(self) -> str:
        """El conocimiento estructurado, redactado como texto corrido."""
        partes: list[str] = []

        if self.laboratorio:
            lineas = []
            for c in self.laboratorio:
                if c.corte_superior is not None and c.termino_si_alto:
                    umbral = (
                        f"{c.corte_superior} (y más de {c.multiplicador}x ese valor "
                        f"para el término con multiplicador)"
                        if c.multiplicador
                        else str(c.corte_superior)
                    )
                    lineas.append(
                        f"- {c.parametro}: por encima de {umbral} se extrae "
                        f"«{c.termino_si_alto}»."
                    )
                if c.corte_inferior is not None and c.termino_si_bajo:
                    lineas.append(
                        f"- {c.parametro}: por debajo de {c.corte_inferior} se extrae "
                        f"«{c.termino_si_bajo}»."
                    )
            if lineas:
                encabezado = "VALORES DE REFERENCIA DE ESTE PROTOCOLO:"
                partes.append(encabezado + "\n" + "\n".join(lineas))

        if self.signos:
            nombres = ", ".join(f"«{s.nombre}»" for s in self.signos)
            partes.append(f"TÉRMINOS QUE RECONOCE ESTE PROTOCOLO: {nombres}.")

        return "\n\n".join(partes)

    def _contexto_etiquetas(self) -> str:
        """El mismo conocimiento, delimitado.

        La hipótesis es que localizar «el corte de la lipasa» es más fácil
        sobre atributos delimitados que sobre prosa, donde hay que leer y
        deducir. Ver docs/VALIDACION.md para la comparación medida.
        """
        partes: list[str] = []

        if self.laboratorio:
            filas = []
            for c in self.laboratorio:
                attrs = [f'parametro="{c.parametro}"']
                if c.corte_superior is not None:
                    attrs.append(f'corte_superior="{c.corte_superior}"')
                if c.corte_inferior is not None:
                    attrs.append(f'corte_inferior="{c.corte_inferior}"')
                if c.multiplicador:
                    attrs.append(f'multiplicador="{c.multiplicador}"')
                if c.termino_si_alto:
                    attrs.append(f'termino_si_alto="{c.termino_si_alto}"')
                if c.termino_si_bajo:
                    attrs.append(f'termino_si_bajo="{c.termino_si_bajo}"')
                filas.append(f"  <criterio {' '.join(attrs)}/>")
            partes.append(_envolver("valores_de_referencia", filas))

        if self.signos:
            filas = [f'  <signo nombre="{s.nombre}"/>' for s in self.signos]
            partes.append(_envolver("terminos_reconocidos", filas))

        return "\n\n".join(partes)

    def hints(self) -> dict[str, str]:
        """Diccionario término→código con lo que el protocolo declara.

        Son códigos revisados por un humano, así que ganan a cualquier
        búsqueda difusa. Salen tanto de los signos como de los términos
        derivados de los cortes de laboratorio.
        """
        salida: dict[str, str] = {}

        for signo in self.signos:
            preferido = signo.codigo_preferido()
            if preferido:
                salida[signo.nombre.strip().lower()] = preferido[1]

        for criterio in self.laboratorio:
            codigo = Signo("", criterio.codigos).codigo_preferido()
            if not codigo:
                continue
            for termino in criterio.terminos():
                salida.setdefault(termino.strip().lower(), codigo[1])

        return salida

    # Nombre anterior, conservado para no romper llamadas existentes.
    hints_snomed = hints

    def vocabulario_preferido(self) -> list[str]:
        """Términos que el protocolo prefiere, para guiar la extracción."""
        terminos = [s.nombre for s in self.signos]
        for criterio in self.laboratorio:
            terminos.extend(criterio.terminos())
        return sorted(set(terminos))

    def para_bayes(self) -> dict[str, Any]:
        """Estructura que espera el motor de inferencia."""
        if not self.bayes.declarado:
            return {"name": self.titulo}
        return {
            "name": self.condicion.get("nombre") or self.titulo,
            "modelo_bayesiano": {
                "probabilidad_base": self.bayes.probabilidad_base,
                "factores_riesgo_a_priori": self.bayes.factores_riesgo,
            },
            "signDetected": [
                {
                    "name": s.nombre,
                    "bayes_lr": s.lr,
                    "bayes_lr_negativo": s.lr_negativo,
                }
                for s in self.signos
                if s.lr is not None or s.lr_negativo is not None
            ],
        }

    # Nombre anterior, conservado para no romper llamadas existentes.
    @property
    def json_principal(self) -> dict[str, Any]:
        return self.para_bayes()

    def problemas(self, index=None) -> list[str]:
        """Revisa el protocolo y devuelve lo que está mal.

        Si se pasa un índice terminológico, comprueba además que cada
        código declarado exista de verdad. Un hint que apunta a un
        concepto inexistente no falla: produce un infón sin linaje ni
        mapeo, en silencio. Esto lo saca a la luz.
        """
        fallos: list[str] = []

        if not self.meta:
            fallos.append("sin frontmatter YAML ni JSON embebido legible")
        # Una skill de documento (una receta, un informe) no extrae
        # hallazgos, así que exigirle signos sería un falso positivo.
        if self.tipo == "clinico" and not self.signos and not self.laboratorio:
            fallos.append("no declara signos ni criterios de laboratorio")

        if self.tipo == "operativo":
            if not self.rol:
                fallos.append("es operativo pero no declara `rol`")
            if not self.campos:
                fallos.append("es operativo pero no declara campos que registrar")
            elif not self.campos_requeridos:
                fallos.append("ningún campo es obligatorio: nada podría faltar")

        for signo in self.signos:
            if signo.lr is not None and signo.lr <= 0:
                fallos.append(f"signo '{signo.nombre}': LR inválido ({signo.lr})")
            if signo.lr is not None and signo.lr != 1.0 and not signo.fuente:
                fallos.append(f"signo '{signo.nombre}': LR sin fuente citada")
            if not signo.codigo_preferido():
                fallos.append(f"signo '{signo.nombre}': sin código")

        for criterio in self.laboratorio:
            if criterio.corte_superior is None and criterio.corte_inferior is None:
                fallos.append(f"criterio '{criterio.parametro}': sin ningún corte")
            if not criterio.terminos():
                fallos.append(f"criterio '{criterio.parametro}': sin término asociado")

        if self.bayes.declarado and not any(s.lr for s in self.signos):
            fallos.append("declara modelo bayesiano pero ningún signo aporta LR")

        if index is not None:
            for termino, codigo in self.hints().items():
                if index.buscar_exacto(termino) is None:
                    fallos.append(
                        f"'{termino}' (código {codigo}) no existe en el vocabulario"
                    )
            for rama in self.ambito_grafo:
                if index.buscar_codigo(rama) is None:
                    fallos.append(f"ámbito de grafo '{rama}' no existe")

            # Los términos que el protocolo ACUÑA, que hasta ahora no se
            # comprobaban. Es el hueco más peligroso de los tres: un hint
            # colgado degrada un hallazgo, pero un `produce` colgado hace
            # que el clasificador emita el DIAGNÓSTICO sin linaje ni mapeo
            # CIE-10, en silencio y con todos los criterios satisfechos.
            fallos.extend(self._problemas_acunados(index))

        return fallos

    def _problemas_acunados(self, index) -> list[str]:
        """Comprueba los conceptos que el protocolo acuña, no los que consume.

        Un protocolo declara dos cosas que no son hints y que hasta ahora
        nadie validaba: la `condicion` que representa y el término que su
        bloque `clasificacion` produce cuando los criterios se satisfacen.
        Ninguno pasa por `hints()`, porque no sirven para normalizar la
        entrada: se emiten a la salida.

        Un concepto se da por anclado si **cualquiera** de sus asas llega al
        vocabulario cargado: cualquiera de sus códigos, o su nombre. Exigir
        que resuelva el código preferente marcaría como rota la
        pancreatitis del propio repositorio, que sólo declara su código
        SNOMED y corre sin SNOMED cargado. Un validador que falla nada más
        instalarlo no se lee: se ignora, y entonces deja de proteger de lo
        que sí importa.

        Sigue teniendo dientes donde hacen falta. Si el concepto desaparece
        del vocabulario se van con él todas sus asas a la vez —código y
        término son el mismo registro— y la comprobación falla igual.
        """
        fallos: list[str] = []

        def anclado(codigos: dict, nombre: str) -> bool:
            for codigo in (codigos or {}).values():
                if codigo and index.buscar_codigo(str(codigo)) is not None:
                    return True
            return bool(nombre) and index.buscar_exacto(nombre) is not None

        nombre_condicion = str(self.condicion.get("nombre") or "").strip()
        codigos_condicion = self.condicion.get("codigos") or {}
        if (codigos_condicion or nombre_condicion) and not anclado(
            codigos_condicion, nombre_condicion
        ):
            fallos.append(
                f"la condición '{nombre_condicion or self.titulo}' no existe en "
                f"el vocabulario: ni por código ni por término"
            )

        if self.clasificacion.declarada:
            produce = self.clasificacion.produce
            termino = str(produce.get("termino") or "").strip()
            if not anclado(produce.get("codigos") or {}, termino):
                fallos.append(
                    f"la clasificación acuña '{termino}', que no existe en el "
                    f"vocabulario: el diagnóstico saldría sin linaje ni CIE-10"
                )

        return fallos


class SkillManager:
    """Descubre, carga y selecciona skills."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.directorio = Path(self.settings.skills_dir)
        self.directorio.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Skill] = {}

    def listar(self) -> list[str]:
        return sorted(p.stem for p in self.directorio.glob("*.md"))

    def catalogo(self) -> str:
        """Menú legible que se le presenta al triaje."""
        lineas = []
        for nombre in self.listar():
            skill = self.cargar(nombre)
            if skill:
                lineas.append(f"- {nombre}: {skill.descripcion}")
        return "\n".join(lineas) or f"- {SKILL_POR_DEFECTO}: Triaje general"

    def cargar(self, nombre: str) -> Skill | None:
        # El nombre puede venir de una respuesta del LLM: se sanea contra
        # traversal antes de tocar el sistema de archivos.
        limpio = Path(nombre.strip().strip("'\"")).name
        if limpio.endswith(".md"):
            limpio = limpio[:-3]
        if not limpio or limpio.startswith("."):
            return None

        if limpio in self._cache:
            return self._cache[limpio]

        ruta = self.directorio / f"{limpio}.md"
        try:
            ruta_real = ruta.resolve()
            if self.directorio.resolve() not in ruta_real.parents:
                logger.warning("Ruta de skill fuera del directorio: %s", nombre)
                return None
            contenido = ruta_real.read_text(encoding="utf-8")
        except (OSError, ValueError):
            return None

        skill = Skill(limpio, contenido)
        self._cache[limpio] = skill
        return skill

    def cargar_o_defecto(self, nombre: str | None) -> Skill:
        skill = self.cargar(nombre) if nombre else None
        if skill:
            return skill
        defecto = self.cargar(SKILL_POR_DEFECTO)
        if defecto:
            return defecto
        # Último recurso: un skill vacío mantiene el pipeline vivo.
        return Skill(SKILL_POR_DEFECTO, "# Triaje general\nExtrae hallazgos clínicos.")

    def para_concepto(self, codigos_ancestros: set[str]) -> list[Skill]:
        """Protocolos cuyo ámbito de grafo cubre alguno de esos conceptos.

        Es lo que permite preguntarle al sistema «¿qué protocolos aplican
        a este paciente?» a partir de los hallazgos que ya tiene, en vez
        de que el triaje decida sólo con el texto de hoy.
        """
        salida = []
        for nombre in self.listar():
            skill = self.cargar(nombre)
            if skill and set(skill.ambito_grafo) & codigos_ancestros:
                salida.append(skill)
        return salida

    async def triaje(self, texto_clinico: str, llm: OllamaClient) -> str:
        """Decide qué protocolo activar. El *primer tic* del sistema."""
        disponibles = self.listar()
        if not disponibles:
            return SKILL_POR_DEFECTO
        if len(disponibles) == 1:
            return disponibles[0]

        prompt = f"""TAREA: clasifica el texto clínico en uno de estos protocolos.

PROTOCOLOS DISPONIBLES:
{self.catalogo()}

TEXTO: "{texto_clinico[:500]}"

Responde ÚNICAMENTE con el nombre exacto del protocolo, sin explicación.
Si ninguno encaja claramente, responde: {SKILL_POR_DEFECTO}
PROTOCOLO:"""

        return await llm.elegir_opcion(
            prompt,
            opciones_validas=disponibles,
            defecto=(
                SKILL_POR_DEFECTO if SKILL_POR_DEFECTO in disponibles else disponibles[0]
            ),
        )


def _num(valor: Any) -> float | None:
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        try:
            return float(valor.strip())
        except ValueError:
            return None
    return None


def _envolver(etiqueta: str, filas: list[str]) -> str:
    """Envuelve unas filas en una etiqueta con su cierre."""
    interior = "\n".join(filas)
    return f"<{etiqueta}>\n{interior}\n</{etiqueta}>"
