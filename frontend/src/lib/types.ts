// Espejo de los modelos de `backend/holonmed/models.py`.
// Si cambias uno, cambia el otro.

export type EstadoInfon = 'VALIDADO' | 'ALERTA' | 'RUIDO';

export interface Infon {
  timestamp: string;
  texto_origen: string;
  termino_propuesto: string;
  termino_snomed: string;
  snomed_id: string | null;
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

export interface ResultadoTic {
  tic_id: string | null;
  timestamp: string;
  paciente_id: string;
  texto_original: string;
  skill_activa: string;
  resumen: string;
  infones: Infon[];
  inferencia: InferenciaBayesiana | null;
}

export interface Paciente {
  _key: string;
  nombre: string;
  edad?: number | null;
  sexo?: string | null;
  telefono?: string | null;
  antecedentes?: string;
}

export interface EntradaHistorial {
  id: string;
  fecha: string;
  skill: string;
  resumen: string;
  total_infones: number;
  validados: number;
  inferencia: InferenciaBayesiana | null;
}

export interface Skill {
  nombre: string;
  descripcion: string;
  hints_snomed: number;
  vocabulario: string[];
  tiene_modelo_bayesiano: boolean;
}

export interface EstadoSistema {
  operativo: boolean;
  base_datos: { conectada: boolean; error: string | null };
  snomed: { backend: string; disponible: boolean };
  skills: string[];
  llm: {
    host: string;
    disponible: boolean;
    modelos: string[];
    configurados: { clinico: string; router: string };
  };
}

export type RespuestaChat =
  | { tipo: 'texto'; datos: { respuesta: string } }
  | { tipo: 'tic'; datos: ResultadoTic }
  | { tipo: 'receta'; datos: { url: string; items: unknown[]; aviso: string } }
  | { tipo: 'agenda'; datos: { legible: string; motivo: string; estado: string } }
  | { tipo: 'whatsapp'; datos: { url: string; telefono: string; mensaje: string; aviso: string } }
  | { tipo: 'paciente'; datos: Paciente | null; encontrado?: boolean; creado?: boolean }
  | { tipo: 'error'; mensaje: string };

// Umbral a partir del cual una hipótesis se presenta como probable.
// Coincide con el veredicto que calcula el backend.
export const UMBRAL_PROBABLE = 50;
export const UMBRAL_CONFIRMADA = 90;
