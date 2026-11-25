import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import { useState } from 'react';
import type { SaludDelSistema } from '../lib/useEstadoSistema';

/**
 * Aviso de arranque cuando falta algo del entorno.
 *
 * Es deliberadamente explícito sobre qué falta y qué comando lo arregla:
 * el fallo más común al instalar esto es tener el servidor de modelos sin los
 * modelos o SNOMED sin descargar, y un error genérico no ayudaría a resolverlo.
 */
export function SystemStatus({ salud }: { salud: SaludDelSistema }) {
  // Se recuerda QUÉ avisos se ocultaron: si cambian, el aviso vuelve a salir.
  const [ocultado, setOcultado] = useState<string | null>(null);

  if (salud.fase !== 'respondio') {
    return (
      <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 text-xs text-slate-400">
        {salud.fase === 'comprobando'
          ? 'Contactando con el servidor…'
          : 'No se pudo contactar con el servidor de HolonMed. Se reintenta solo.'}
      </div>
    );
  }
  const { estado } = salud;

  if (estado.operativo && estado.base_datos.conectada) {
    return null;
  }

  const problemas: { texto: string; remedio: string; critico: boolean }[] = [];

  // `openai` es el protocolo de LM Studio y llama.cpp; los comandos son los de LM Studio.
  const lmStudio = estado.llm.backend === 'openai';

  if (estado.llm.estado === 'sin_conexion') {
    problemas.push({
      texto: `El servidor de modelos no responde en ${estado.llm.host}`,
      remedio: lmStudio ? 'lms server start' : 'ollama serve',
      critico: true,
    });
  } else if (estado.llm.estado === 'falta_modelo') {
    for (const modelo of estado.llm.faltantes) {
      problemas.push({
        texto: `Falta el modelo ${modelo}`,
        remedio: lmStudio ? `lms load ${modelo}` : `ollama pull ${modelo}`,
        critico: true,
      });
    }
  } else if (estado.llm.estado !== 'conectado') {
    problemas.push({
      texto: `No se pudo comprobar el modelo en ${estado.llm.host}`,
      remedio: 'revisa que ese puerto sea el del servidor de modelos',
      critico: true,
    });
  }

  if (!estado.vocabulario.disponible) {
    problemas.push({
      texto: 'Sin vocabulario clínico: los hallazgos no se podrán validar',
      remedio: 'python scripts/importar_terminologia.py --semilla',
      critico: true,
    });
  }

  if (!estado.base_datos.conectada) {
    problemas.push({
      texto: `No se pudo abrir la base de datos: ${estado.base_datos.error ?? ''}`,
      remedio: 'comprueba los permisos de escritura en backend/data/',
      critico: true,
    });
  }

  const firma = problemas.map((p) => p.texto).join('|');
  if (problemas.length === 0 || ocultado === firma) return null;

  const hayCriticos = problemas.some((p) => p.critico);

  return (
    <div
      role="status"
      className={`px-4 py-2.5 border-b text-xs ${
        hayCriticos
          ? 'bg-amber-50 border-amber-200 text-amber-900'
          : 'bg-sky-50 border-sky-200 text-sky-900'
      }`}
    >
      <div className="flex items-start gap-2">
        {hayCriticos ? (
          <AlertCircle size={14} className="mt-0.5 shrink-0" aria-hidden />
        ) : (
          <CheckCircle2 size={14} className="mt-0.5 shrink-0" aria-hidden />
        )}

        <ul className="flex-1 space-y-1">
          {problemas.map((p, i) => (
            <li key={i} className="flex flex-wrap items-baseline gap-x-2">
              <span>{p.texto}</span>
              <code className="px-1.5 py-0.5 rounded bg-white/60 border border-current/20 font-mono text-[11px]">
                {p.remedio}
              </code>
            </li>
          ))}
        </ul>

        <button
          type="button"
          onClick={() => setOcultado(firma)}
          aria-label="Ocultar aviso"
          className="shrink-0 opacity-60 hover:opacity-100"
        >
          <X size={14} aria-hidden />
        </button>
      </div>
    </div>
  );
}
