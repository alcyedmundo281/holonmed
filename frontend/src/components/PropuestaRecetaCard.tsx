import { ExternalLink } from 'lucide-react';
import { useState } from 'react';
import { api } from '../lib/api';
import type { PropuestaReceta, RecetaEmitida } from '../lib/types';

/**
 * La aprobación de una receta. Enseña todo lo que se va a escribir y no
 * deja confirmar sin el nombre de quien aprueba, que nunca viene relleno.
 */
export function PropuestaRecetaCard({ propuesta }: { propuesta: PropuestaReceta }) {
  const [nombre, setNombre] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const [emitida, setEmitida] = useState<RecetaEmitida | null>(null);

  async function confirmar() {
    if (!nombre.trim() || enviando) return;
    setEnviando(true);
    setError('');
    try {
      setEmitida(
        await api.confirmarReceta(propuesta.propuesta_id, propuesta.paciente_id, nombre.trim()),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mt-2 pt-2 border-t border-slate-300/40 text-xs space-y-1.5">
      <p>
        <span className="font-medium">Paciente:</span> {propuesta.paciente_nombre}
      </p>
      <p className="break-words">
        <span className="font-medium">Petición:</span> {propuesta.texto_original}
      </p>
      <ul className="list-disc pl-4 space-y-1">
        {propuesta.items.map((item, i) => (
          <li key={i} className="break-words">
            <span className="font-medium">{item.farmaco}</span>{' '}
            {item.concentracion || '(sin concentración)'}
            <br />
            {item.indicaciones || '(sin indicaciones)'}
          </li>
        ))}
      </ul>
      {propuesta.indicaciones_generales && (
        <p className="break-words">
          <span className="font-medium">Indicaciones generales (no salen en el PDF):</span>{' '}
          {propuesta.indicaciones_generales}
        </p>
      )}

      {emitida ? (
        <>
          <p className="text-[11px] text-amber-700">
            Registrada. Confirmó: {emitida.confirmado_por}. {emitida.aviso}
          </p>
          <a
            href={emitida.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 font-medium text-indigo-700 hover:underline"
          >
            Abrir PDF
            <ExternalLink size={12} aria-hidden />
          </a>
        </>
      ) : (
        <>
          <p className="text-[11px] text-amber-700">
            Todavía no se ha registrado nada. Compruébalo contra la petición; si algo está mal, no
            confirmes y vuelve a pedirla.
          </p>
          <input
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Nombre de quien confirma"
            aria-label="Nombre de quien confirma"
            disabled={enviando}
            className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-slate-800"
          />
          <button
            type="button"
            onClick={confirmar}
            disabled={enviando || !nombre.trim()}
            className="px-3 py-1 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-slate-400"
          >
            {enviando ? 'Registrando…' : 'Confirmar y registrar'}
          </button>
          {error && <p className="text-red-700">{error}</p>}
        </>
      )}
    </div>
  );
}
