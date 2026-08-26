import { AlertTriangle, Ban, Swords } from 'lucide-react';
import { cifra, porcentaje } from '../lib/phi';
import type { CandidataAbductiva, ResultadoTic } from '../lib/types';

/**
 * La competencia abductiva: contra qué compitió la hipótesis que se usó.
 *
 * Hoy sólo MIDE. El protocolo que corrió lo eligió el prompt de triaje;
 * esto registra cuál habría elegido el grafo del paciente y si coinciden.
 * Mostrar las perdedoras no es adorno: «se consideró diverticulitis y sacó
 * 0.25» *es* la traza de auditoría, y sin ella se enseña una conclusión
 * sin decir contra qué compitió.
 */
export function CompetitionPanel({ tic }: { tic: ResultadoTic }) {
  if (tic.competencia.length === 0) return null;

  // Se ordena por la clave —el coseno de la lectura que cada protocolo
  // permite— igual que el backend. Las vetadas y las no admitidas van al
  // final: no compiten, pero se enseñan con su motivo.
  const ordenadas = [...tic.competencia].sort((a, b) => {
    const compite = (c: CandidataAbductiva) => !c.vetada && c.admitida;
    if (compite(a) !== compite(b)) return compite(a) ? -1 : 1;
    return (b.clave ?? -Infinity) - (a.clave ?? -Infinity);
  });

  return (
    <section className="border border-slate-200 rounded-lg bg-white p-4 mb-4 shadow-sm">
      <header className="flex items-center gap-2 mb-3">
        <Swords size={16} className="text-indigo-600" aria-hidden />
        <h3 className="font-semibold text-slate-800 text-sm">
          Competencia abductiva
        </h3>
        <span className="text-[11px] text-slate-500 ml-auto">
          {tic.competencia.length} candidata
          {tic.competencia.length === 1 ? '' : 's'}
        </span>
      </header>

      <Acuerdo tic={tic} />

      {/* La compuerta de α, dicha en voz alta. Es la mitad del diseño: si
          actúa callada, el sistema trata otra cosa sin explicar por qué. */}
      {tic.aviso_competencia && (
        <div className="flex items-start gap-2 text-xs bg-amber-50 border border-amber-200 rounded-md p-2 mb-3">
          <AlertTriangle size={13} className="text-amber-600 shrink-0 mt-0.5" aria-hidden />
          <p className="text-amber-900">{tic.aviso_competencia}</p>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead className="text-slate-500">
            <tr>
              <th className="font-medium py-1 pr-2">Hipótesis</th>
              <th className="font-medium py-1 pr-2 text-right">clave</th>
              <th className="font-medium py-1 pr-2 text-right">α</th>
              <th className="font-medium py-1 pr-2 text-right">cob.</th>
              <th className="font-medium py-1 pr-2 text-right">expl.</th>
              <th className="font-medium py-1">estado</th>
            </tr>
          </thead>
          <tbody>
            {ordenadas.map((c) => (
              <Fila key={c.skill} candidata={c} activa={c.skill === tic.skill_activa} />
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 pt-2 border-t border-slate-100 text-[11px] text-slate-400 leading-relaxed">
        Las candidatas salen del grafo del paciente, no de un prompt. Se ordenan
        por el coseno y no por Φ: ordenar por Φ escogería la mejor documentada
        en vez de la mejor acoplada, porque α es una propiedad del protocolo y
        no del paciente. Hoy esto sólo mide — el protocolo que se usó lo sigue
        eligiendo el triaje.
      </p>
    </section>
  );
}

/**
 * `triaje_coincide === null` NO es «discrepan»: es que no hubo competencia
 * con la que comparar. Colapsarlo a falso contaría como desacuerdo un tic
 * donde nadie compitió.
 */
function Acuerdo({ tic }: { tic: ResultadoTic }) {
  if (tic.triaje_coincide === null) {
    return (
      <p className="text-xs text-slate-500 italic mb-3">
        No hubo ninguna candidata admitida con la que comparar el triaje.
      </p>
    );
  }

  return (
    <p className="text-xs mb-3">
      {tic.triaje_coincide ? (
        <span className="text-emerald-700">
          El triaje y el grafo coinciden en{' '}
          <span className="font-medium">{tic.ganadora_abductiva}</span>.
        </span>
      ) : (
        <span className="text-amber-700">
          <span className="font-medium">Discrepan:</span> el triaje usó{' '}
          <code className="text-slate-700">{tic.skill_activa}</code> y el grafo
          habría elegido{' '}
          <span className="font-medium">{tic.ganadora_abductiva}</span>.
        </span>
      )}
    </p>
  );
}

function Fila({
  candidata,
  activa,
}: {
  candidata: CandidataAbductiva;
  activa: boolean;
}) {
  const apagada = candidata.vetada || !candidata.admitida;

  return (
    <tr
      className={`border-t border-slate-200 ${apagada ? 'text-slate-400' : 'text-slate-700'} ${
        activa ? 'bg-indigo-50/60' : ''
      }`}
    >
      <td className="py-1 pr-2">
        {candidata.skill}
        {activa && (
          <span className="ml-1.5 text-[10px] px-1.5 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
            en uso
          </span>
        )}
      </td>
      <td className="py-1 pr-2 text-right tabular-nums">{cifra(candidata.clave)}</td>
      <td className="py-1 pr-2 text-right tabular-nums">
        {candidata.anclaje.toFixed(2)}
      </td>
      <td className="py-1 pr-2 text-right tabular-nums">
        {porcentaje(candidata.cobertura)}
      </td>
      <td className="py-1 pr-2 text-right tabular-nums">
        {porcentaje(candidata.explicacion)}
      </td>
      <td className="py-1">
        {candidata.vetada ? (
          <span className="flex items-center gap-1 text-rose-600" title={candidata.motivo_veto ?? ''}>
            <Ban size={11} aria-hidden />
            vetada
          </span>
        ) : !candidata.admitida ? (
          <span className="text-slate-500" title="Sin procedencia: α = 0, no compite">
            sin anclaje
          </span>
        ) : (
          <span className="text-slate-500">{candidata.lectura}</span>
        )}
      </td>
    </tr>
  );
}
