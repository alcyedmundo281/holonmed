import { Activity, FileText, Paperclip } from 'lucide-react';
import { useState } from 'react';
import type { EntradaHistorial, OrigenTic } from '../lib/types';
import { ORIGENES, OrigenBadge, etiquetaOrigen } from './OrigenBadge';
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
  const [filtro, setFiltro] = useState<OrigenTic | null>(null);

  // Se filtra en cliente: la lista de una historia individual cabe en
  // memoria, y así alternar entre orígenes es instantáneo.
  const visibles = filtro ? historial.filter((e) => e.origen === filtro) : historial;
  const presentes = ORIGENES.filter((o) => historial.some((e) => e.origen === o));

  if (historial.length === 0) {
    return (
      <p className="text-sm text-slate-500 bg-white border border-slate-200 rounded-lg p-6 text-center">
        Sin registros todavía. La historia se alimenta de la consulta, del
        laboratorio y de la farmacia.
      </p>
    );
  }

  return (
    <div>
      {presentes.length > 1 && (
        <div className="flex flex-wrap gap-1.5 mb-4" role="group" aria-label="Filtrar por origen">
          <button
            type="button"
            onClick={() => setFiltro(null)}
            aria-pressed={filtro === null}
            className={`text-xs px-2.5 py-1 rounded-full border ${
              filtro === null
                ? 'bg-slate-800 text-white border-slate-800'
                : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
            }`}
          >
            Todo ({historial.length})
          </button>
          {presentes.map((o) => {
            const n = historial.filter((e) => e.origen === o).length;
            return (
              <button
                key={o}
                type="button"
                onClick={() => setFiltro(filtro === o ? null : o)}
                aria-pressed={filtro === o}
                className={`text-xs px-2.5 py-1 rounded-full border ${
                  filtro === o
                    ? 'bg-slate-800 text-white border-slate-800'
                    : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
                }`}
              >
                {etiquetaOrigen(o)} ({n})
              </button>
            );
          })}
        </div>
      )}

      <ol className="relative border-l-2 border-slate-200 ml-3 space-y-4">
      {visibles.map((entrada) => {
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
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <span className="flex items-center gap-2">
                  <OrigenBadge origen={entrada.origen} actor={entrada.actor} />
                  <span className="text-xs text-slate-500">{fechaHora(entrada.fecha)}</span>
                </span>
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

                {entrada.documentos > 0 && (
                  <span className="flex items-center gap-1 text-slate-600">
                    <Paperclip size={11} aria-hidden />
                    {entrada.documentos}
                  </span>
                )}

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
    </div>
  );
}
