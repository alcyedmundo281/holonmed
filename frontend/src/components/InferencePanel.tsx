import { Activity, ArrowRight } from 'lucide-react';
import type { InferenciaBayesiana } from '../lib/types';
import { UMBRAL_CONFIRMADA, UMBRAL_PROBABLE } from '../lib/types';

/**
 * Presenta la hipótesis diagnóstica junto a su razonamiento completo.
 *
 * La probabilidad sola sería una caja negra. Lo que hace útil a este panel
 * es la traza: de dónde salió la probabilidad previa y qué hallazgo movió
 * la aguja y cuánto. Un clínico puede discrepar de un paso concreto.
 */
export function InferencePanel({ inferencia }: { inferencia: InferenciaBayesiana }) {
  const p = inferencia.probabilidad_porcentaje;

  const tono =
    p > UMBRAL_CONFIRMADA
      ? { barra: 'bg-emerald-500', texto: 'text-emerald-700', etiqueta: 'Hipótesis sostenida' }
      : p > UMBRAL_PROBABLE
        ? { barra: 'bg-amber-500', texto: 'text-amber-700', etiqueta: 'Probable' }
        : { barra: 'bg-slate-400', texto: 'text-slate-600', etiqueta: 'Baja sospecha' };

  return (
    <section className="border border-slate-200 rounded-lg bg-white p-4 mb-4 shadow-sm">
      <header className="flex items-center gap-2 mb-3">
        <Activity size={16} className="text-indigo-600" aria-hidden />
        <h3 className="font-semibold text-slate-800 text-sm">Inferencia abductiva</h3>
      </header>

      <div className="flex items-baseline justify-between mb-1">
        <span className="font-medium text-slate-900">{inferencia.diagnostico}</span>
        <span className={`text-2xl font-bold tabular-nums ${tono.texto}`}>{p.toFixed(1)}%</span>
      </div>

      <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-1">
        <div
          className={`h-full ${tono.barra} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(100, p)}%` }}
        />
      </div>

      <p className="text-xs text-slate-500 mb-4 flex items-center gap-1.5">
        <span>{tono.etiqueta}</span>
        <span aria-hidden>·</span>
        <span className="tabular-nums">
          previa {inferencia.probabilidad_previa.toFixed(1)}%
        </span>
        <ArrowRight size={11} aria-hidden />
        <span className="tabular-nums">posterior {p.toFixed(1)}%</span>
      </p>

      <div className="space-y-3 text-xs">
        <div>
          <h4 className="font-medium text-slate-700 mb-1">Probabilidad a priori</h4>
          <ul className="space-y-0.5">
            {inferencia.traza_logica.map((paso, i) => (
              <li key={i} className="text-slate-600 pl-3 border-l-2 border-slate-200">
                {paso}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="font-medium text-slate-700 mb-1">
            Evidencia aplicada
            {inferencia.evidencia_utilizada.length === 0 && (
              <span className="font-normal text-slate-400"> — ninguna</span>
            )}
          </h4>
          {inferencia.evidencia_utilizada.length > 0 ? (
            <ul className="space-y-0.5">
              {inferencia.evidencia_utilizada.map((ev, i) => (
                <li key={i} className="text-slate-700 pl-3 border-l-2 border-indigo-300">
                  {ev}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 pl-3">
              Sólo la evidencia validada actualiza la probabilidad. Los hallazgos
              en alerta o descartados se muestran, pero no cuentan.
            </p>
          )}
        </div>
      </div>

      <p className="mt-3 pt-2 border-t border-slate-100 text-[11px] text-slate-400 leading-relaxed">
        Estimación estadística a partir del protocolo activo. No es un diagnóstico
        ni sustituye la valoración clínica.
      </p>
    </section>
  );
}
