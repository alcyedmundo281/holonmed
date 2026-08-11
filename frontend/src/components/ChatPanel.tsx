import { ExternalLink, Loader2, Send } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import type { RespuestaChat } from '../lib/types';

interface Mensaje {
  autor: 'usuario' | 'sistema';
  texto: string;
  accion?: { etiqueta: string; url: string; aviso?: string };
}

/**
 * Chat de acciones.
 *
 * Nada de lo que se decide aquí sale del sistema por su cuenta: si la
 * intención es enviar un WhatsApp o emitir una receta, la respuesta es un
 * enlace que una persona debe abrir y confirmar.
 */
export function ChatPanel({ pacienteId }: { pacienteId: string }) {
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [entrada, setEntrada] = useState('');
  const [esperando, setEsperando] = useState(false);
  const finRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensajes]);

  // Al cambiar de paciente se limpia la conversación: arrastrar el contexto
  // de un paciente a otro es exactamente el error que no queremos.
  useEffect(() => {
    setMensajes([]);
  }, [pacienteId]);

  async function enviar() {
    const texto = entrada.trim();
    if (!texto || esperando) return;

    setMensajes((m) => [...m, { autor: 'usuario', texto }]);
    setEntrada('');
    setEsperando(true);

    try {
      const respuesta = await api.chat(texto, pacienteId);
      setMensajes((m) => [...m, interpretar(respuesta)]);
    } catch (e) {
      setMensajes((m) => [
        ...m,
        { autor: 'sistema', texto: e instanceof Error ? e.message : 'Error' },
      ]);
    } finally {
      setEsperando(false);
    }
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {mensajes.length === 0 && (
          <p className="text-xs text-slate-400 text-center mt-8 px-4 leading-relaxed">
            Pide una cita, redacta una receta o consulta el historial.
            <br />
            Para procesar una narrativa clínica, usa el panel de cristalización.
          </p>
        )}

        {mensajes.map((m, i) => (
          <div key={i} className={m.autor === 'usuario' ? 'text-right' : ''}>
            <div
              className={`inline-block max-w-[92%] text-left rounded-lg px-3 py-2 text-sm ${
                m.autor === 'usuario'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-800'
              }`}
            >
              <p className="whitespace-pre-wrap break-words">{m.texto}</p>

              {m.accion && (
                <div className="mt-2 pt-2 border-t border-slate-300/40">
                  {m.accion.aviso && (
                    <p className="text-[11px] text-amber-700 mb-1.5">{m.accion.aviso}</p>
                  )}
                  <a
                    href={m.accion.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-700 hover:underline"
                  >
                    {m.accion.etiqueta}
                    <ExternalLink size={12} aria-hidden />
                  </a>
                </div>
              )}
            </div>
          </div>
        ))}

        {esperando && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Loader2 size={13} className="animate-spin" aria-hidden />
            Pensando…
          </div>
        )}
        <div ref={finRef} />
      </div>

      <div className="border-t border-slate-700 p-2 flex gap-2 shrink-0">
        <input
          value={entrada}
          onChange={(e) => setEntrada(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && enviar()}
          placeholder="Escribe una instrucción…"
          disabled={esperando}
          className="flex-1 text-sm bg-slate-700 text-slate-100 placeholder-slate-400
                     rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <button
          type="button"
          onClick={enviar}
          disabled={esperando || !entrada.trim()}
          aria-label="Enviar"
          className="px-3 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-slate-600"
        >
          <Send size={15} aria-hidden />
        </button>
      </div>
    </div>
  );
}

function interpretar(r: RespuestaChat): Mensaje {
  switch (r.tipo) {
    case 'texto':
      return { autor: 'sistema', texto: r.datos.respuesta };

    case 'receta':
      return {
        autor: 'sistema',
        texto: `Borrador de receta con ${r.datos.items.length} medicamento(s).`,
        accion: { etiqueta: 'Abrir PDF', url: r.datos.url, aviso: r.datos.aviso },
      };

    case 'agenda':
      return { autor: 'sistema', texto: `Cita ${r.datos.estado}: ${r.datos.legible} — ${r.datos.motivo}` };

    case 'whatsapp':
      return {
        autor: 'sistema',
        texto: `Mensaje preparado para ${r.datos.telefono}:\n\n«${r.datos.mensaje}»`,
        accion: { etiqueta: 'Abrir en WhatsApp', url: r.datos.url, aviso: r.datos.aviso },
      };

    case 'paciente':
      return {
        autor: 'sistema',
        texto: r.datos ? `Paciente: ${r.datos.nombre} (${r.datos.id})` : 'Sin coincidencias.',
      };

    case 'tic': {
      const validados = r.datos.infones.filter((i) => i.estado === 'VALIDADO').length;
      return {
        autor: 'sistema',
        texto: `Procesado con «${r.datos.skill_activa}»: ${validados} de ${r.datos.infones.length} hallazgos validados.`,
      };
    }

    case 'error':
      return { autor: 'sistema', texto: r.mensaje };
  }
}
