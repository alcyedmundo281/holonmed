import { ArrowRight, HelpCircle, RotateCcw, TrendingDown } from 'lucide-react';
import type { CausaDeLaDuda, ReaperturaDeIndagacion } from '../lib/types';

/**
 * Lo que la duda abre cuando Φ dice que la creencia dejó de ser operable.
 *
 * No es un veto: una exclusión absoluta dice que el diagnóstico es
 * imposible y termina la pregunta; la duda dice que el argumento dejó de
 * sostenerse con lo que hay, y la reabre. Tampoco resuelve nada en este
 * tic — la respuesta a lo que pregunta llega en el siguiente.
 */

// Las tres clases de duda mandan a sitios opuestos, y por eso cada una
// lleva su propio consejo y su propio color. Fundirlas en «Φ bajo» sería
// perder exactamente lo que se ganó al partir el coseno en tres.
const CAUSAS: Record<
  CausaDeLaDuda,
  { titulo: string; consejo: string; color: string; fondo: string }
> = {
  direccion: {
    titulo: 'Lo que se ha mirado disiente',
    consejo:
      'No se arregla mirando más: cada dato que confirme lo ya visto la hunde ' +
      'más. Lo que toca es cambiar de hipótesis.',
    color: 'text-rose-700',
    fondo: 'bg-rose-50 border-rose-200',
  },
  cobertura: {
    titulo: 'Casi nada se ha puesto a prueba',
    consejo:
      'La hipótesis puede ser buena y estar sin comprobar. Ésta es la duda ' +
      'que se resuelve indagando, y abajo está por dónde.',
    color: 'text-amber-700',
    fondo: 'bg-amber-50 border-amber-200',
  },
  explicacion: {
    titulo: 'No explica al paciente',
    consejo:
      'Puede ser cierta y no ser la pregunta: es la forma que toma el sesgo ' +
      'de anclaje. Lo que falta está fuera de esta hipótesis.',
    color: 'text-violet-700',
    fondo: 'bg-violet-50 border-violet-200',
  },
};

export function DoubtPanel({ reapertura }: { reapertura: ReaperturaDeIndagacion }) {
  const causa = reapertura.causa ? CAUSAS[reapertura.causa] : null;

  return (
    <section
      className={`border rounded-lg p-4 mb-4 shadow-sm ${
        causa ? causa.fondo : 'bg-slate-50 border-slate-200'
      }`}
    >
      <header className="flex items-center gap-2 mb-3">
        <RotateCcw size={16} className="text-slate-700" aria-hidden />
        <h3 className="font-semibold text-slate-800 text-sm">
          La indagación se reabre
        </h3>
        <span className="text-[11px] tabular-nums text-slate-500 ml-auto">
          Φ {reapertura.phi.toFixed(4)}
        </span>
      </header>

      <p className="text-sm text-slate-800 mb-1">
        <span className="font-medium">{reapertura.hipotesis}</span> ha dejado de
        funcionar como regla de acción.
      </p>

      {causa ? (
        <>
          <p className={`text-sm font-medium ${causa.color} mb-1`}>{causa.titulo}</p>
          <p className="text-xs text-slate-600 mb-3">{causa.consejo}</p>
        </>
      ) : (
        <p className="text-xs text-slate-600 mb-3">
          No hay ningún factor definido con el que responder por qué: no se ha
          medido nada. {reapertura.motivo}
        </p>
      )}

      <Trayectoria reapertura={reapertura} />

      {reapertura.alternativa && (
        <div className="flex items-start gap-2 text-xs bg-white/70 border border-slate-200 rounded-md p-2 mb-3">
          <ArrowRight size={13} className="text-indigo-600 shrink-0 mt-0.5" aria-hidden />
          <p className="text-slate-700">
            La competencia abductiva prefiere{' '}
            <span className="font-medium text-slate-900">{reapertura.alternativa}</span>.
            La vuelta a la abducción ya tiene a dónde ir.
          </p>
        </div>
      )}

      {reapertura.preguntas.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-medium text-slate-700 mb-1 flex items-center gap-1.5">
            <HelpCircle size={12} aria-hidden />
            Qué mirar ahora
          </h4>
          <ul className="space-y-0.5">
            {reapertura.preguntas.map((pregunta, i) => (
              <li
                key={i}
                className="text-xs text-slate-700 pl-3 border-l-2 border-slate-300"
              >
                {pregunta}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="pt-2 border-t border-slate-200/70 text-[11px] text-slate-400 leading-relaxed">
        Esto no retira el diagnóstico —eso es una exclusión absoluta, y es otra
        cosa— ni se resuelve en esta consulta: la respuesta a lo que pregunta
        llega con la evidencia del siguiente tic.
      </p>
    </section>
  );
}

/**
 * dΦ/dt. Los tres estados no son tres intensidades: una creencia que
 * funcionaba y se rompió manda a mirar los hallazgos de hoy, y una que
 * nunca arraigó no reabre nada porque nunca se cerró.
 *
 * `null` se dice en voz alta y no se calla: callarlo dejaría al clínico
 * suponiendo que la creencia venía estable, que es justo lo que no se
 * sabe.
 */
function Trayectoria({ reapertura }: { reapertura: ReaperturaDeIndagacion }) {
  const { trayectoria, phi_previo } = reapertura;

  if (trayectoria === null) {
    return (
      <p className="text-xs text-slate-500 italic mb-3">
        Primera vez que esta hipótesis se mide en este paciente: no hay con qué
        comparar, así que no se puede decir si la creencia se rompió o si nunca
        llegó a sostenerse.
      </p>
    );
  }

  const rota = trayectoria === 'se_rompio';

  return (
    <div className="flex items-start gap-2 text-xs mb-3">
      <TrendingDown
        size={13}
        className={`shrink-0 mt-0.5 ${rota ? 'text-rose-600' : 'text-slate-400'}`}
        aria-hidden
      />
      <p className="text-slate-700">
        {rota ? (
          <>
            <span className="font-medium text-rose-700">La creencia se rompió.</span>{' '}
            Venía en Φ{' '}
            <span className="tabular-nums">{phi_previo?.toFixed(4)}</span> y ha
            caído: algo de lo que entró desbarató la regla de acción, y está en
            los hallazgos de esta consulta.
          </>
        ) : (
          <>
            <span className="font-medium text-slate-700">Nunca llegó a arraigar.</span>{' '}
            La vez anterior ya daba Φ{' '}
            <span className="tabular-nums">{phi_previo?.toFixed(4)}</span>: no se
            ha roto nada, esta hipótesis lleva sin sostenerse desde antes.
          </>
        )}
      </p>
    </div>
  );
}
