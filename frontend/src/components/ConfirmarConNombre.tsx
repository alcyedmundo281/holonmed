import { useState, type ReactNode } from 'react';

/**
 * La aprobación de una escritura propuesta: no deja confirmar sin el nombre
 * de quien aprueba, que nunca viene relleno.
 */
export function ConfirmarConNombre<T>({
  confirmar,
  registrado,
}: {
  confirmar: (nombre: string) => Promise<T>;
  registrado: (resultado: T) => ReactNode;
}) {
  const [nombre, setNombre] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState<{ valor: T } | null>(null);

  async function enviar() {
    if (!nombre.trim() || enviando) return;
    setEnviando(true);
    setError('');
    try {
      setResultado({ valor: await confirmar(nombre.trim()) });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error');
    } finally {
      setEnviando(false);
    }
  }

  if (resultado) return <>{registrado(resultado.valor)}</>;

  return (
    <>
      <p className="text-[11px] text-amber-700">
        Todavía no se ha registrado nada. Compruébalo contra la petición; si algo está mal, no
        confirmes y vuelve a pedirlo.
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
        onClick={enviar}
        disabled={enviando || !nombre.trim()}
        className="px-3 py-1 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-slate-400"
      >
        {enviando ? 'Registrando…' : 'Confirmar y registrar'}
      </button>
      {error && <p className="text-red-700">{error}</p>}
    </>
  );
}
