import { Activity, FileText } from 'lucide-react';
import type { EntradaHistorial } from '../lib/types';
import { fechaHora } from './ProblemList';

/**
 * Línea de tiempo de consultas.
 *
 * Cada entrada muestra cuántos hallazgos se validaron sobre el total. Esa
 * proporción es un indicador útil por sí misma: si baja de golpe, o el
 * texto era pobre o el validador está rechazando de más, y en ambos casos
 * conviene mirar el tic concreto.
 */
export function HistoryTimeline({
  historial,
  onAbrir,
}: {
  historial: EntradaHistorial[];
  onAbrir?: (id: string) => void;
}) {
  if (historial.length === 0) {
    return (
      <p className="text-sm text-slate-500 bg-white border border-slate-200 rounded-lg p-6 text-center">
        Sin consultas registradas todavía.
      </p>
    );
  }

  return (
    <ol className="relative border-l-2 border-slate-200 ml-3 space-y-4">
      {historial.map((entrada) => {
        const ratio = entrada.total_infones
          ? entrada.validados / entrada.total_infones
          : 0;
        return (
          <li key={entrada.id} className="ml-5">
            <span
              className="absolute -left-[7px] w-3 h-3 rounded-full bg-indigo-500 ring-4 ring-white"
              aria-hidden
            />
            <button
              type="button"
              onClick={() => onAbrir?.(entrada.id)}
              className="w-full text-left bg-white border border-slate-200 rounded-lg p-3
                         hover:border-indigo-300 transition-colors"
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-xs text-slate-500">{fechaHora(entrada.fecha)}</span>
                <code className="text-[11px] text-slate-500">{entrada.skill}</code>
              </div>

              {entrada.resumen && (
                <p className="text-sm text-slate-800 mt-1.5">{entrada.resumen}</p>
              )}

              <div className="flex items-center gap-3 mt-2 text-xs">
                <span className="flex items-center gap-1 text-slate-600">
                  <FileText size={11} aria-hidden />
                  <span className="tabular-nums">
                    {entrada.validados}/{entrada.total_infones}
                  </span>
                  validados
                </span>

                <div className="flex-1 h-1 bg-slate-100 rounded-full overflow-hidden max-w-[120px]">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${ratio * 100}%` }}
                  />
                </div>

                {entrada.inferencia && (
                  <span className="flex items-center gap-1 text-indigo-700 ml-auto">
                    <Activity size={11} aria-hidden />
                    {entrada.inferencia.diagnostico}{' '}
                    <span className="tabular-nums font-medium">
                      {entrada.inferencia.probabilidad_porcentaje.toFixed(0)}%
                    </span>
                  </span>
                )}
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
