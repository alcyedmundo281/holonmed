import type { NotaEvolucion, OrigenTic, ProblemaEvolucion } from '../lib/types';
import { fecha as fechaLegible } from './ProblemList';

const SIN_DATO = 'sin dato declarado';

// A y P son texto fijo y no un dato: el modelo `NotaEvolucion` no tiene dónde
// traerlos. Los escribe el profesional.
const SIN_VALORACION = 'sin valoración; la escribe el profesional';
const SIN_PLAN = 'sin plan; lo escribe el profesional';

const PROCEDENCIA: Record<string, string> = {
  subjetivo: 'S',
  objetivo: 'O',
  derivado: 'derivado',
};

/**
 * La evolución SOAP por problema de un tic, como borrador sin firma.
 *
 * S y O sólo traen lo que la narrativa declaró con «S:» u «O:». Lo que no
 * está validado se muestra aparte, fuera de la nota. El resumen libre del
 * modelo no entra aquí.
 */
export function EvolutionNote({
  nota,
  fecha,
  origen,
}: {
  nota: NotaEvolucion;
  fecha: string;
  origen: OrigenTic;
}) {
  return (
    <section className="bg-white border border-slate-300 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-slate-800">
        Nota de evolución{' '}
        <span className="font-normal text-amber-700">· borrador sin firma</span>
      </h3>
      <p className="text-xs text-slate-500 mb-3">
        {fechaLegible(fecha)} · origen: {origen}
      </p>

      {nota.avisos.map((aviso) => (
        <p
          key={aviso}
          role="alert"
          className="text-sm text-amber-900 bg-amber-50 border-2 border-amber-300 rounded p-2 mb-3"
        >
          {aviso}
        </p>
      ))}

      {nota.problemas.length === 0 && (
        <p className="text-sm text-slate-600">
          Sin problemas: ningún hallazgo validado y presente.
        </p>
      )}

      <div className="space-y-3">
        {nota.problemas.map((p) => (
          <Problema key={p.codigo ?? p.termino} problema={p} />
        ))}
      </div>

      <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-4 mb-1">
        Negativos documentados (no son problemas)
      </h4>
      {nota.negativos.length === 0 ? (
        <p className="text-sm text-slate-500">Ninguno.</p>
      ) : (
        <ul className="text-sm text-slate-700">
          {nota.negativos.map((n, i) => (
            <li key={i}>
              {n.termino}: ausente · «{n.cita}»{' '}
              <span className="text-xs text-slate-400">
                [{PROCEDENCIA[n.procedencia] ?? 'sin clasificar S/O'}]
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 pt-3 border-t border-dashed border-slate-300">
        <h4 className="text-xs font-semibold text-amber-800 uppercase tracking-wide mb-1">
          Fuera de la nota (no validado, para revisar)
        </h4>
        {nota.fuera_de_la_nota.length === 0 ? (
          <p className="text-sm text-slate-500">Nada.</p>
        ) : (
          <ul className="text-sm text-slate-600">
            {nota.fuera_de_la_nota.map((f, i) => (
              <li key={i}>
                [{f.estado}] {f.termino} · «{f.cita}»
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function Problema({ problema }: { problema: ProblemaEvolucion }) {
  return (
    <article>
      <h4 className="text-sm font-semibold text-slate-800">
        {problema.numero === null ? '(sin número)' : `#${problema.numero}`}{' '}
        {problema.termino}
        {problema.codigo && (
          <span className="ml-2 text-[11px] font-mono font-normal text-slate-400">
            {problema.codigo}
          </span>
        )}
      </h4>
      <dl className="text-sm grid grid-cols-[auto_1fr] gap-x-3 pl-4 mt-0.5">
        <Linea etiqueta="S" valor={citas(problema.subjetivo)} />
        <Linea etiqueta="O" valor={citas(problema.objetivo)} />
        {problema.sin_clasificar.length > 0 && (
          <Linea etiqueta="Sin clasificar S/O" valor={citas(problema.sin_clasificar)} />
        )}
        {problema.derivado.length > 0 && (
          <Linea
            etiqueta="Derivado, no escrito en la nota"
            valor={problema.derivado.join('; ')}
          />
        )}
        <Linea etiqueta="A" valor={SIN_VALORACION} vacia />
        <Linea etiqueta="P" valor={SIN_PLAN} vacia />
      </dl>
    </article>
  );
}

function Linea({
  etiqueta,
  valor,
  vacia = false,
}: {
  etiqueta: string;
  valor: string;
  vacia?: boolean;
}) {
  const atenuada = vacia || valor === SIN_DATO;
  return (
    <>
      <dt className="font-semibold text-slate-500">{etiqueta}</dt>
      <dd className={atenuada ? 'text-slate-400 italic' : 'text-slate-800'}>{valor}</dd>
    </>
  );
}

function citas(lista: string[]): string {
  return lista.length ? lista.map((c) => `«${c}»`).join(' · ') : SIN_DATO;
}
