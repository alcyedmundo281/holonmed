// Espejo de los modelos de `backend/holonmed/models.py`.
// Si cambias uno, cambia el otro.

export type EstadoInfon = 'VALIDADO' | 'ALERTA' | 'RUIDO';

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
  codigo: string | null;
  sistema: string | null;
  concepto_id: number | null;
  cie10_code: string | null;
  linaje_clinico: string | null;
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
  /** Φ ∈ [−1, +1] */
  phi: number;
  coseno: number;
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

export interface ResultadoTic {
  tic_id: string | null;
  timestamp: string;
  paciente_id: string;
  texto_original: string;
  origen: OrigenTic;
  actor: string | null;
  skill_activa: string;
  resumen: string;
  infones: Infon[];
  inferencia: InferenciaBayesiana | null;
  acoplamiento: Acoplamiento | null;
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
