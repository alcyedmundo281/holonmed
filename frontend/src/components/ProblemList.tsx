import { CalendarClock, Layers } from 'lucide-react';
import type { Problema } from '../lib/types';

/**
 * Lista de problemas del paciente.
 *
 * Es la primera vista que mira un clínico al abrir una historia. Se
 * construye sólo con hallazgos validados y deduplicados por concepto; las
 * fechas de primera y última aparición son lo que distingue un problema
 * agudo de uno arrastrado, así que se muestran siempre.
 */
export function ProblemList({
  problemas,
  onExplorar,
}: {
  problemas: Problema[];
  onExplorar?: (problema: Problema) => void;
}) {
  if (problemas.length === 0) {
    return (
      <p className="text-sm text-slate-500 bg-white border border-slate-200 rounded-lg p-6 text-center">
        Sin problemas registrados. Procesa una nota clínica para empezar a
        construir la historia.
      </p>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
          <tr>
            <th className="text-left font-medium px-4 py-2">Problema</th>
            <th className="text-left font-medium px-3 py-2">Código</th>
            <th className="text-right font-medium px-3 py-2">Veces</th>
            <th className="text-left font-medium px-3 py-2">Primera</th>
            <th className="text-left font-medium px-4 py-2">Última</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {problemas.map((p) => (
            <tr
              key={p.codigo ?? p.termino}
              onClick={() => p.codigo && onExplorar?.(p)}
              className={`hover:bg-slate-50 ${p.codigo && onExplorar ? 'cursor-pointer' : ''}`}
            >
              <td className="px-4 py-2.5">
                <div className="font-medium text-slate-800">{p.termino}</div>
                {p.linaje && (
                  <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                    <Layers size={10} aria-hidden />
                    {p.linaje}
                  </div>
                )}
              </td>
              <td className="px-3 py-2.5">
                <div className="flex flex-col gap-1 items-start">
                  {p.codigo && (
                    <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200">
                      {p.codigo}
                    </span>
                  )}
                  {p.cie10 && (
                    <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-violet-50 text-violet-700 border border-violet-200">
                      CIE-10 {p.cie10}
                    </span>
                  )}
                </div>
              </td>
              <td className="px-3 py-2.5 text-right tabular-nums text-slate-600">
                {p.apariciones}
              </td>
              <td className="px-3 py-2.5 text-xs text-slate-500 whitespace-nowrap">
                {fecha(p.primera)}
              </td>
              <td className="px-4 py-2.5 text-xs text-slate-700 whitespace-nowrap">
                <span className="flex items-center gap-1">
                  <CalendarClock size={11} className="text-slate-400" aria-hidden />
                  {fecha(p.ultima)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function fecha(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString('es', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function fechaHora(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('es', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}
