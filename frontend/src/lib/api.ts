import type {
  EntradaHistorial,
  Infon,
  EstadoSistema,
  Grafo,
  Paciente,
  Problema,
  RespuestaChat,
  ResultadoTic,
  Skill,
} from './types';

// En desarrollo Vite hace de proxy, así que basta con rutas relativas.
const BASE = import.meta.env.VITE_API_URL ?? '';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  let respuesta: Response;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
  } catch {
    throw new ApiError('No se pudo contactar con el servidor', 0);
  }

  if (!respuesta.ok) {
    // FastAPI explica el motivo en `detail`; se prefiere ese texto al
    // genérico porque suele decir exactamente qué falta.
    let detalle = respuesta.statusText;
    try {
      const cuerpo = await respuesta.json();
      if (typeof cuerpo?.detail === 'string') detalle = cuerpo.detail;
    } catch {
      /* la respuesta no era JSON */
    }
    throw new ApiError(detalle, respuesta.status);
  }

  return respuesta.json() as Promise<T>;
}

const q = encodeURIComponent;

export const api = {
  estado: () => pedir<EstadoSistema>('/health'),
  skills: () => pedir<Skill[]>('/api/skills'),

  cristalizar: (texto: string, pacienteId: string, skill?: string) =>
    pedir<ResultadoTic>('/api/crystallize', {
      method: 'POST',
      body: JSON.stringify({ texto, paciente_id: pacienteId, skill: skill ?? null }),
    }),

  chat: (mensaje: string, pacienteId: string) =>
    pedir<RespuestaChat>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ mensaje, paciente_id: pacienteId }),
    }),

  pacientes: () => pedir<Paciente[]>('/api/pacientes'),

  crearPaciente: (datos: {
    nombre: string;
    edad?: number | null;
    sexo?: string | null;
    antecedentes?: string;
  }) =>
    pedir<Paciente>('/api/pacientes', {
      method: 'POST',
      body: JSON.stringify(datos),
    }),

  historial: (pacienteId: string) =>
    pedir<EntradaHistorial[]>(`/api/pacientes/${q(pacienteId)}/historial`),

  problemas: (pacienteId: string) =>
    pedir<Problema[]>(`/api/pacientes/${q(pacienteId)}/problemas`),

  grafoPaciente: (pacienteId: string) => pedir<Grafo>(`/api/grafo/paciente/${q(pacienteId)}`),

  tic: (ticId: string) =>
    pedir<{ texto_original: string; infones: Infon[] }>(`/api/tics/${q(ticId)}`),

  cohorte: (codigo: string, sistema = 'holonmed') =>
    pedir<{ pacientes: { id: string; nombre: string; hallazgos: number }[]; total: number }>(
      `/api/grafo/cohorte?codigo=${q(codigo)}&sistema=${q(sistema)}`,
    ),

  subirLaboratorio: async (pacienteId: string, archivo: File) => {
    const cuerpo = new FormData();
    cuerpo.append('archivo', archivo);
    const respuesta = await fetch(`${BASE}/api/labs/upload?paciente_id=${q(pacienteId)}`, {
      method: 'POST',
      body: cuerpo,
    });
    if (!respuesta.ok) {
      const error = await respuesta.json().catch(() => null);
      throw new ApiError(error?.detail ?? 'Error subiendo el archivo', respuesta.status);
    }
    return respuesta.json() as Promise<{ resultado: ResultadoTic }>;
  },
};
