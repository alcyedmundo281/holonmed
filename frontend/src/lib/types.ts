// Espejo de los modelos de `backend/holonmed/models.py`.
// Si cambias uno, cambia el otro.
//
// Eso último era hasta hoy una promesa escrita en un comentario, y se
// rompió: este archivo se quedó sin nueve campos de `Acoplamiento` y sin
// siete de `ResultadoTic` sin que nada protestara, porque un tipo que
// promete de menos no rompe la compilación. Ahora lo comprueba
// `backend/tests/test_contrato_frontend.py`, que compara los campos en
// los dos sentidos.
//
// Lo que se refleja es el JSON QUE VIAJA, no la clase de Python. La
// distinción importa porque en el backend hay valores derivados —`duda`,
// `phi_legible`, `InferenciaBayesiana.veredicto`, `cumple`— declarados
// como `@property` y no como campos, de modo que Pydantic **no los
// serializa**. Declararlos aquí sería una promesa que el servidor no
// cumple, y TypeScript la dejaría pasar hasta que algo leyera
// `undefined` en pantalla. Donde falta un derivado, el frontend lo
// calcula con los umbrales del final de este archivo.

export type EstadoInfon = 'VALIDADO' | 'ALERTA' | 'RUIDO';

/**
 * Si el hallazgo consta presente o consta ausente. No es un detalle de
 * presentación: invierte el sentido del dato, porque una ausencia
 * documentada resta peso de evidencia en vez de sumarlo.
 */
export type Polaridad = 'presente' | 'ausente';

/** Qué proceso del entorno clínico produjo un tic. */
export type OrigenTic =
  | 'consulta'
  | 'laboratorio'
  | 'farmacia'
  | 'enfermeria'
  | 'imagen'
  | 'otro';

export interface Infon {
  timestamp: string;
  texto_origen: string;
  termino_propuesto: string;
  termino: string;
  polaridad: Polaridad;
  codigo: string | null;
  sistema: string | null;
  concepto_id: number | null;
  cie10_code: string | null;
  linaje_clinico: string | null;
  /**
   * De qué hallazgos se dedujo éste. Un infón derivado —el trastorno que
   * acuña el clasificador— no es evidencia nueva: es la hipótesis misma,
   * y por eso Φ lo excluye de su vector.
   */
  derivado_de: string[];
  /** El criterio del protocolo que lo acuñó, si vino de uno. */
  criterio: string | null;
  estado: EstadoInfon;
  confianza: number;
  score_ontologico: number;
  score_logico: number;
  razon_auditoria: string;
  origen_skill: string;
}

export interface InferenciaBayesiana {
  diagnostico: string;
  probabilidad_porcentaje: number;
  probabilidad_previa: number;
  traza_logica: string[];
  evidencia_utilizada: string[];
}

export type EstadoDimension =
  | 'concuerda'
  | 'contradice'
  | 'sin_medir'
  | 'no_simbolizado';

export type VeredictoSemiotico =
  | 'ARMONIA'
  | 'ACOPLAMIENTO_PARCIAL'
  | 'INERCIA'
  | 'FRICCION'
  | 'DESARMONIA';

export interface ComponenteAcoplamiento {
  dimension: string;
  rol: string;
  /** hᵢ: ln(LR+) que exige el caso de libro */
  esperado: number;
  /** eᵢ: peso de evidencia que aporta el registro */
  observado: number;
  estado: EstadoDimension;
  detalle: string;
  infon: string | null;
  confianza: number;
}

/**
 * Segundo eje de lectura, independiente de la probabilidad: cuánto
 * armoniza la hipótesis con el paciente entero. Se muestra junto a
 * `inferencia`, nunca en su lugar.
 */
export interface Acoplamiento {
  /** Φ ∈ [−1, +1]. Lectura ponderada: vale 0 si el protocolo no declara LR. */
  phi: number;
  coseno: number;

  /**
   * La lectura de ±1 sobre TODOS los signos declarados, que es la única
   * posible cuando el protocolo declara categorías y no cocientes — el
   * caso de casi todos los criterios publicados. `null` si no hay ni un
   * signo del que leerla.
   */
  phi_categorico: number | null;
  coseno_categorico: number | null;
  dimensiones_categoricas: number;

  /**
   * Los tres factores de `coseno`: `cos = dirección · √cobertura ·
   * √explicación`. Se informan para poder leer *por qué* salió ese
   * número, y **nunca se vuelven a aplicar**: ya están dentro de
   * `coseno`, así que multiplicar cualquiera otra vez lo contaría dos
   * veces.
   *
   * `null` no es 0. Sin ninguna dimensión a la vez declarada y medida no
   * hay ángulo del que hablar, de modo que `direccion` no vale 0: no
   * existe. `cobertura` en ese mismo caso **sí** vale 0, y es una
   * afirmación cierta — no se ha mirado nada de lo que la hipótesis
   * exige.
   *
   * Al mostrarlos: se publican redondeados a cuatro decimales mientras
   * el producto se calcula sin redondear, así que recomponer la
   * multiplicación en pantalla puede dar un número distinto de `coseno`
   * por un cuanto de redondeo. El que manda es `coseno`.
   */
  direccion: number | null;
  cobertura: number | null;
  explicacion: number | null;

  /** Los mismos tres, para la lectura categórica: Σeᵢ/m, m/D y m/(m+r). */
  direccion_categorica: number | null;
  cobertura_categorica: number | null;
  explicacion_categorica: number | null;

  /** α ∈ [0,1]: cuánto está anclado el argumento a lo medido. */
  anclaje: number;
  hipotesis: string;
  veredicto: VeredictoSemiotico;
  cuadrante: string;
  componentes: ComponenteAcoplamiento[];
  resto_no_simbolizado: string[];
  indagacion: string[];
  anclaje_detalle: Record<string, number>;
  traza: string[];
}

/**
 * Cuál de los tres factores rompió la creencia. No son tres intensidades
 * de lo mismo: cada una manda a un sitio distinto — `direccion` a cambiar
 * de hipótesis, `cobertura` a indagar, `explicacion` a volver a la
 * abducción.
 */
export type CausaDeLaDuda = 'direccion' | 'cobertura' | 'explicacion';

/**
 * Si la creencia se rompió o si nunca llegó a arraigar. Un Φ bajo hoy no
 * distingue las dos, y no son la misma situación clínica: `se_rompio` es
 * la creencia establecida que la experiencia desbarató —lo que la
 * disparó está en los hallazgos nuevos— y `nunca_arraigo` es una
 * hipótesis que se viene midiendo y nunca funcionó.
 *
 * No hay valor para «no hay tic anterior»: eso es `null`. Un literal que
 * dijera «estable» afirmaría una trayectoria que nadie ha medido.
 */
export type TrayectoriaDeLaCreencia = 'se_rompio' | 'nunca_arraigo';

/**
 * Lo que la duda abre cuando Φ dice que la creencia dejó de funcionar
 * como regla de acción. No retira la hipótesis —eso es el veto— ni
 * resuelve nada dentro del tic: la respuesta a lo que pregunta llega en
 * otro tic. Es la salida accionable.
 *
 * `null` en `ResultadoTic` significa que no hay duda que reabrir.
 */
export interface ReaperturaDeIndagacion {
  hipotesis: string;
  /** El Φ legible que quedó bajo el mínimo. */
  phi: number;
  /** `null` cuando no hay ningún factor definido con el que responder. */
  causa: CausaDeLaDuda | null;
  motivo: string;
  /** Hacia dónde indagar, heredado de `Acoplamiento.indagacion`. */
  preguntas: string[];
  /** La hipótesis que la abducción prefiere, si difiere de la que corrió. */
  alternativa: string | null;

  /**
   * dΦ/dt. `phi_previo` es lo que esta misma hipótesis dio la última vez
   * que se midió sobre este paciente, y `trayectoria` lo interpreta.
   * Ambos `null` si nunca se midió antes: no es que la creencia estuviera
   * estable, es que no hay con qué compararla.
   */
  phi_previo: number | null;
  trayectoria: TrayectoriaDeLaCreencia | null;

  traza: string[];
}

/** Una exclusión absoluta: no resta probabilidad, retira la hipótesis. */
export interface Veto {
  tipo: string;
  motivo: string;
  termino: string | null;
  hipotesis: string;
}

/**
 * El criterio publicado, contado. Se lee junto a `inferencia` y
 * `acoplamiento`, nunca fundido con ellos: cuando el criterio contado y
 * la aritmética discrepan, la discrepancia es información clínica.
 */
export interface VeredictoDeclarado {
  /** El grado de certeza alcanzado, o `null` si no alcanza ninguno. */
  nivel: string | null;
  apoyos: string[];
  banderas_rojas: string[];
  veto: Veto | null;
  fuente: string;
  traza: string[];
}

/**
 * Una hipótesis que compitió por explicar al paciente. Las perdedoras se
 * conservan: «se consideró diverticulitis y sacó 0.25» *es* la traza de
 * auditoría, y sin ella se muestra una conclusión sin decir contra qué
 * compitió.
 */
export interface CandidataAbductiva {
  skill: string;
  /** La clave de orden: el coseno de la lectura que este protocolo permite. */
  clave: number | null;
  lectura: string;
  anclaje: number;
  cobertura: number | null;
  explicacion: number | null;
  vetada: boolean;
  motivo_veto: string | null;
  /** Pasó la compuerta de α > 0. Sin procedencia, la hipótesis no compite. */
  admitida: boolean;
}

export type EstadoCriterio =
  | 'satisfecho'
  | 'descartado'
  | 'sin_confirmar'
  | 'sin_datos';

export interface Criterio {
  nombre: string;
  rol: string;
  satisface_si: string[];
}

export interface CriterioEvaluado {
  criterio: Criterio;
  estado: EstadoCriterio;
  /** Los infones que lo satisfacen o lo descartan. */
  por: Infon[];
}

/**
 * El veredicto de los criterios de clasificación, con su desglose.
 *
 * En el backend es un `@dataclass`, no un modelo Pydantic, así que sólo
 * viajan sus campos declarados: `satisfechos`, `cumple`, `resumen` y
 * `vacios` son propiedades y se quedan en el servidor. Los dos primeros
 * se derivan aquí contando `evaluados`.
 */
export interface ResultadoClasificacion {
  nombre: string;
  fuente: string;
  requiere: number;
  evaluados: CriterioEvaluado[];
  /** El infón que acuña el diagnóstico, si se cumplió. */
  trastorno: Infon | null;
}

export interface ResultadoTic {
  tic_id: string | null;
  timestamp: string;
  paciente_id: string;
  texto_original: string;
  origen: OrigenTic;
  actor: string | null;
  skill_activa: string;
  /**
   * La versión del protocolo, junto a su nombre. Es lo que convierte
   * recomputar en auditar: sin ella, volver a pasar los infones de aquel
   * día por el protocolo de hoy responde a otra pregunta.
   */
  skill_version: string | null;
  resumen: string;
  infones: Infon[];
  clasificacion: ResultadoClasificacion | null;
  inferencia: InferenciaBayesiana | null;
  acoplamiento: Acoplamiento | null;
  veredicto_declarado: VeredictoDeclarado | null;

  /**
   * La competencia abductiva, que hoy sólo MIDE. El protocolo que se usó
   * sigue siendo `skill_activa`, elegido por el prompt de triaje; esto
   * registra cuál habría elegido el grafo y si coinciden.
   */
  competencia: CandidataAbductiva[];
  ganadora_abductiva: string | null;
  /** `null` —y no `false`— si no hubo competencia con la que comparar. */
  triaje_coincide: boolean | null;
  /**
   * Se dice en voz alta cuando la de mayor coseno quedó fuera por α:
   * «encaja mejor y no puedo usarla porque su protocolo no cita». Si la
   * compuerta actúa callada, el sistema trata otra cosa sin explicar por
   * qué.
   */
  aviso_competencia: string | null;

  /** `null` si la creencia sigue siendo operable. */
  reapertura: ReaperturaDeIndagacion | null;

  /**
   * Se rellena cuando el grafo propuso candidatas y el veto las retiró
   * TODAS. No es «no encontré hipótesis»: es que todo lo que este
   * paciente sugiere es estructuralmente imposible, y eso o pide ampliar
   * el ámbito de los protocolos o dice que los antecedentes están mal.
   * Es un estado clínico propio y se muestra como tal.
   */
  todas_vetadas: string | null;
}

export interface Paciente {
  id: string;
  nombre: string;
  edad?: number | null;
  sexo?: string | null;
  telefono?: string | null;
  antecedentes?: string;
  tics?: number;
  ultima_visita?: string | null;
}

export interface EntradaHistorial {
  id: string;
  fecha: string;
  origen: OrigenTic;
  actor: string | null;
  skill: string;
  resumen: string;
  total_infones: number;
  validados: number;
  documentos: number;
  inferencia: InferenciaBayesiana | null;
}

export interface ResumenOrigen {
  origen: OrigenTic;
  tics: number;
  ultimo: string;
}

export interface Documento {
  id: string;
  tic_id: string | null;
  tipo: string;
  archivo: string | null;
  datos: { items?: { farmaco?: string; concentracion?: string }[] } | null;
  creado: string;
}

export interface Problema {
  termino: string;
  codigo: string | null;
  sistema: string | null;
  cie10: string | null;
  linaje: string | null;
  apariciones: number;
  primera: string;
  ultima: string;
  confianza: number;
}

export interface NodoGrafo {
  id: number;
  codigo: string;
  sistema: string;
  termino: string;
  tipo: 'hallazgo' | 'agrupacion';
  peso: number;
}

export interface Grafo {
  nodos: NodoGrafo[];
  aristas: { origen: number; destino: number }[];
}

export interface Skill {
  nombre: string;
  descripcion: string;
  hints_snomed: number;
  vocabulario: string[];
  tiene_modelo_bayesiano: boolean;
}

/**
 * Un borrador de orden salido del plan. No existe en la base: mientras
 * sea esto, no obliga a nadie a nada ni puede generar ningún cargo.
 */
export interface OrdenPropuesta {
  termino: string;
  texto_origen: string;
  detalle: Record<string, string>;
  codigo: string | null;
  sistema: string | null;
  concepto_id: number | null;
  /** El sistema encontró el término en el vocabulario y podrá tarifarlo. */
  reconocida: boolean;
  /** Campos que el plan no especificaba. Se muestran, no se rellenan. */
  faltantes: string[];
  /** El modelo devolvió una categoría en vez del fármaco. Hay que corregirlo. */
  generico: boolean;
}

/** Una orden ya firmada. A partir de aquí la cadena puede facturar. */
export interface Orden {
  id: string | null;
  paciente_id: string;
  timestamp: string;
  termino: string;
  codigo: string | null;
  sistema: string | null;
  texto_origen: string;
  prescriptor: string | null;
  detalle: Record<string, string>;
  estado: 'pendiente' | 'cumplida' | 'anulada';
}

export interface EstadoSistema {
  operativo: boolean;
  base_datos: {
    conectada: boolean;
    ruta: string;
    error: string | null;
    estadisticas: Record<string, number>;
  };
  vocabulario: { disponible: boolean; sistemas: Record<string, number> };
  skills: string[];
  llm: {
    host: string;
    disponible: boolean;
    modelos: string[];
    faltantes: string[];
    configurados: { clinico: string; router: string };
  };
}

export type RespuestaChat =
  | { tipo: 'texto'; datos: { respuesta: string } }
  | { tipo: 'tic'; datos: ResultadoTic }
  | { tipo: 'receta'; datos: { url: string; items: unknown[]; aviso: string } }
  | { tipo: 'agenda'; datos: { legible: string; motivo: string; estado: string } }
  | {
      tipo: 'whatsapp';
      datos: { url: string; telefono: string; mensaje: string; aviso: string };
    }
  | { tipo: 'paciente'; datos: Paciente | null; encontrado?: boolean; creado?: boolean }
  | { tipo: 'error'; mensaje: string };

// Umbrales de presentación. Coinciden con el veredicto del backend.
export const UMBRAL_PROBABLE = 50;
export const UMBRAL_CONFIRMADA = 90;
