import { Loader2, PenLine } from 'lucide-react';
import { useState } from 'react';
import { api } from '../lib/api';

/**
 * Pide al modelo que corrija la redacción de una respuesta libre del chat.
 *
 * Lo corregido es una propuesta que se enseña debajo del original: no lo
 * sustituye ni se guarda, así que no hay nada que aceptar. El servidor ya la
 * ha comprobado; si cambiaba algo más que la redacción, llega el motivo.
 *
 * Su estado vive dentro del chat, que se monta por paciente: una corrección
 * que llegue tarde se descarta con él.
 */
export function CorreccionRedaccion({
  respuestaId,
  pacienteId,
}: {
  respuestaId: string;
  pacienteId: string;
}) {
  const [abierto, setAbierto] = useState(false);
  const [instruccion, setInstruccion] = useState('');
  const [pidiendo, setPidiendo] = useState(false);
  const [propuesta, setPropuesta] = useState<string | null>(null);
  const [error, setError] = useState('');

  async function pedir() {
    if (pidiendo) return;
    setPidiendo(true);
    setError('');
    setPropuesta(null);
    try {
      const r = await api.corregirRedaccion(respuestaId, pacienteId, instruccion.trim());
      setPropuesta(r.corregido);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error');
    } finally {
      setPidiendo(false);
    }
  }

  function descartar() {
    setPropuesta(null);
    setError('');
    setAbierto(false);
  }

  if (!abierto) {
    return (
      <button
        type="button"
        onClick={() => setAbierto(true)}
        className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-indigo-700 hover:underline"
      >
        <PenLine size={12} aria-hidden />
        Corregir redacción
      </button>
    );
  }

  return (
    <div className="mt-2 pt-2 border-t border-slate-300/60 text-xs space-y-1.5">
      <p className="text-[11px] text-slate-500">
        Sólo se admiten cambios de puntuación, mayúsculas, tildes que falten, artículos y
        formato. Si cambia cualquier otra cosa, se descarta.
      </p>
      <div className="flex gap-1.5">
        <input
          value={instruccion}
          onChange={(e) => setInstruccion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && pedir()}
          maxLength={500}
          disabled={pidiendo}
          aria-label="Instrucción para la corrección (opcional)"
          placeholder="Instrucción (opcional)"
          className="flex-1 min-w-0 border border-slate-300 rounded-md px-2 py-1 bg-white
                     focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <button
          type="button"
          onClick={pedir}
          disabled={pidiendo}
          className="px-2.5 py-1 rounded-md bg-indigo-600 text-white font-medium
                     hover:bg-indigo-700 disabled:bg-slate-300 flex items-center gap-1.5"
        >
          {pidiendo && <Loader2 size={12} className="animate-spin" aria-hidden />}
          Proponer
        </button>
        <button
          type="button"
          onClick={descartar}
          disabled={pidiendo}
          className="px-2 py-1 rounded-md border border-slate-300 text-slate-600 hover:bg-white"
        >
          Descartar
        </button>
      </div>

      {error && (
        <p role="alert" className="text-rose-700 bg-rose-50 border border-rose-200 rounded-md p-2">
          {error}
        </p>
      )}

      {propuesta !== null && (
        <section className="bg-white border border-indigo-200 rounded-md p-2">
          <h4 className="text-[11px] font-semibold text-indigo-800 mb-1">
            Propuesta de corrección · no sustituye al original ni se guarda
          </h4>
          <p className="text-sm whitespace-pre-wrap break-words">{propuesta}</p>
          <p className="text-[11px] text-amber-700 mt-1.5">
            Compárala con el original: una coma o una tilde también pueden cambiar el sentido.
          </p>
        </section>
      )}
    </div>
  );
}
