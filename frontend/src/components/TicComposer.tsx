import { FileUp, Loader2, Sparkles } from 'lucide-react';
import { useRef, useState } from 'react';
import { api } from '../lib/api';
import type { ResultadoTic, Skill } from '../lib/types';

interface Props {
  pacienteId: string;
  skills: Skill[];
  onResultado: (resultado: ResultadoTic) => void;
}

/**
 * Entrada del *tic*: la narrativa clínica en bruto.
 *
 * El protocolo puede dejarse en automático (lo elige el triaje) o forzarse.
 * Forzarlo es útil cuando el clínico ya sabe qué está mirando y no quiere
 * gastar una llamada al modelo en decidirlo.
 */
export function TicComposer({ pacienteId, skills, onResultado }: Props) {
  const [texto, setTexto] = useState('');
  const [skill, setSkill] = useState('');
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputArchivo = useRef<HTMLInputElement>(null);

  async function procesar() {
    if (!texto.trim() || procesando) return;
    setProcesando(true);
    setError(null);
    try {
      onResultado(await api.cristalizar(texto, pacienteId, skill || undefined));
      setTexto('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido');
    } finally {
      setProcesando(false);
    }
  }

  async function subirPdf(archivo: File) {
    setProcesando(true);
    setError(null);
    try {
      const { resultado } = await api.subirLaboratorio(pacienteId, archivo);
      onResultado(resultado);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error subiendo el archivo');
    } finally {
      setProcesando(false);
      if (inputArchivo.current) inputArchivo.current.value = '';
    }
  }

  return (
    <div className="border border-slate-200 rounded-lg bg-white p-4 shadow-sm">
      <textarea
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        onKeyDown={(e) => {
          // Ctrl/Cmd+Enter procesa. Enter solo hace salto de línea: una
          // narrativa clínica es multilínea por naturaleza.
          if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') procesar();
        }}
        placeholder="Nota de ingreso, evolución o resultado de laboratorio…"
        rows={7}
        disabled={procesando}
        className="w-full text-sm border border-slate-200 rounded-md p-3 resize-y
                   focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent
                   disabled:bg-slate-50 disabled:text-slate-400"
      />

      <div className="flex items-center gap-2 mt-3">
        <select
          value={skill}
          onChange={(e) => setSkill(e.target.value)}
          disabled={procesando}
          aria-label="Protocolo clínico"
          className="text-xs border border-slate-200 rounded-md px-2 py-1.5 bg-white
                     focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">Protocolo: automático</option>
          {skills.map((s) => (
            <option key={s.nombre} value={s.nombre}>
              {s.nombre}
            </option>
          ))}
        </select>

        <input
          ref={inputArchivo}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const archivo = e.target.files?.[0];
            if (archivo) void subirPdf(archivo);
          }}
        />
        <button
          type="button"
          onClick={() => inputArchivo.current?.click()}
          disabled={procesando}
          title="Subir un informe de laboratorio en PDF"
          className="text-xs px-2.5 py-1.5 border border-slate-200 rounded-md text-slate-600
                     hover:bg-slate-50 disabled:opacity-50 flex items-center gap-1.5"
        >
          <FileUp size={13} aria-hidden />
          PDF
        </button>

        <div className="flex-1" />

        <button
          type="button"
          onClick={procesar}
          disabled={procesando || !texto.trim()}
          className="text-sm px-4 py-1.5 rounded-md bg-indigo-600 text-white font-medium
                     hover:bg-indigo-700 disabled:bg-slate-300 flex items-center gap-2"
        >
          {procesando ? (
            <>
              <Loader2 size={15} className="animate-spin" aria-hidden />
              Procesando…
            </>
          ) : (
            <>
              <Sparkles size={15} aria-hidden />
              Cristalizar
            </>
          )}
        </button>
      </div>

      {procesando && (
        <p className="text-xs text-slate-500 mt-2">
          Triaje, extracción, validación en tres capas e inferencia. Con modelos
          locales puede tardar entre unos segundos y un minuto.
        </p>
      )}

      {error && (
        <p role="alert" className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-md p-2 mt-2">
          {error}
        </p>
      )}
    </div>
  );
}
