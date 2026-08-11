import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import { useState } from 'react';
import type { EstadoSistema } from '../lib/types';

/**
 * Aviso de arranque cuando falta algo del entorno.
 *
 * Es deliberadamente explícito sobre qué falta y qué comando lo arregla:
 * el fallo más común al instalar esto es tener Ollama sin modelos o SNOMED
 * sin descargar, y un error genérico no ayudaría a resolverlo.
 */
export function SystemStatus({ estado }: { estado: EstadoSistema | null }) {
  const [cerrado, setCerrado] = useState(false);

  if (!estado) {
    return (
      <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 text-xs text-slate-400">
        Contactando con el servidor…
      </div>
    );
  }

  if (estado.operativo && estado.base_datos.conectada) {
    return null;
  }
  if (cerrado) return null;

  const problemas: { texto: string; remedio: string; critico: boolean }[] = [];

  if (!estado.llm.disponible) {
    problemas.push({
      texto: `Ollama no responde en ${estado.llm.host}`,
      remedio: 'ollama serve',
      critico: true,
    });
  } else {
    for (const modelo of estado.llm.faltantes) {
      problemas.push({
        texto: `Falta el modelo ${modelo}`,
        remedio: `ollama pull ${modelo}`,
        critico: true,
      });
    }
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

  if (problemas.length === 0) return null;

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
          onClick={() => setCerrado(true)}
          aria-label="Ocultar aviso"
          className="shrink-0 opacity-60 hover:opacity-100"
        >
          <X size={14} aria-hidden />
        </button>
      </div>
    </div>
  );
}
