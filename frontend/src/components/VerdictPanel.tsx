import { Ban, Check, Flag, Scale } from 'lucide-react';
import type { VeredictoDeclarado } from '../lib/types';

/**
 * El criterio publicado, contado.
 *
 * Es el tercer eje y se lee junto a los otros dos, nunca fundido con
 * ellos: cuando el criterio contado y la aritmética discrepan, la
 * discrepancia es información clínica. Los enteros los declara el
 * protocolo tomándolos del criterio publicado con su cita — no son
 * umbrales que el sistema calibre.
 */
export function VerdictPanel({ veredicto }: { veredicto: VeredictoDeclarado }) {
  // El veto no es una probabilidad baja: es una imposibilidad estructural,
  // y por eso se muestra antes que nada y con el peso visual de una
  // parada. Un veto que actúa callado retira un diagnóstico sin decir por
  // qué.
  if (veredicto.veto) {
    return (
      <section className="border-2 border-rose-300 rounded-lg bg-rose-50 p-4 mb-4 shadow-sm">
        <header className="flex items-center gap-2 mb-2">
          <Ban size={16} className="text-rose-700" aria-hidden />
          <h3 className="font-semibold text-rose-900 text-sm">
            Hipótesis retirada
          </h3>
        </header>

        <p className="text-sm text-rose-900 mb-1">
          <span className="font-medium">{veredicto.veto.hipotesis}</span>{' '}
          queda descartada.
        </p>
        <p className="text-sm text-rose-800 mb-3">{veredicto.veto.motivo}</p>

        {veredicto.fuente && (
          <p className="text-[11px] text-rose-700/80 mb-2">
            Criterio: {veredicto.fuente}
          </p>
        )}

        <p className="pt-2 border-t border-rose-200 text-[11px] text-rose-700/80 leading-relaxed">
          Una exclusión absoluta no es una probabilidad baja: es una
          imposibilidad, y ninguna cantidad de evidencia la contrarresta. Si el
          antecedente que la dispara está mal registrado, corrígelo antes de
          seguir.
        </p>
      </section>
    );
  }

  const { apoyos, banderas_rojas: banderas, nivel } = veredicto;

  return (
    <section className="border border-slate-200 rounded-lg bg-white p-4 mb-4 shadow-sm">
      <header className="flex items-center gap-2 mb-3">
        <Scale size={16} className="text-indigo-600" aria-hidden />
        <h3 className="font-semibold text-slate-800 text-sm">Criterio publicado</h3>
        {nivel ? (
          <span className="ml-auto text-[11px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-medium">
            {nivel}
          </span>
        ) : (
          <span className="ml-auto text-[11px] text-slate-500">
            no alcanza ningún nivel
          </span>
        )}
      </header>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <Lista
          titulo="Apoyos"
          Icono={Check}
          color="text-emerald-700"
          borde="border-emerald-300"
          items={apoyos}
          vacio="Ninguno consta"
        />
        <Lista
          titulo="Banderas rojas"
          Icono={Flag}
          color="text-amber-700"
          borde="border-amber-300"
          items={banderas}
          vacio="Ninguna consta"
        />
      </div>

      {veredicto.traza.length > 0 && (
        <ul className="space-y-0.5 mb-3">
          {veredicto.traza.map((paso, i) => (
            <li key={i} className="text-[11px] text-slate-600 pl-3 border-l-2 border-slate-200">
              {paso}
            </li>
          ))}
        </ul>
      )}

      <p className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 leading-relaxed">
        {veredicto.fuente ? `Enteros declarados por: ${veredicto.fuente}. ` : ''}
        Los umbrales los fija el criterio publicado, no el sistema. Se lee junto
        a la probabilidad y al acoplamiento, nunca en su lugar.
      </p>
    </section>
  );
}

function Lista({
  titulo,
  Icono,
  color,
  borde,
  items,
  vacio,
}: {
  titulo: string;
  Icono: typeof Check;
  color: string;
  borde: string;
  items: string[];
  vacio: string;
}) {
  return (
    <div>
      <h4 className={`text-xs font-medium mb-1 flex items-center gap-1.5 ${color}`}>
        <Icono size={12} aria-hidden />
        {titulo} ({items.length})
      </h4>
      {items.length > 0 ? (
        <ul className="space-y-0.5">
          {items.map((item) => (
            <li key={item} className={`text-xs text-slate-700 pl-2 border-l-2 ${borde}`}>
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-400 italic">{vacio}</p>
      )}
    </div>
  );
}
