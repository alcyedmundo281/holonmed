import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  PenLine,
  Sparkles,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Orden, OrdenPropuesta } from '../lib/types';

interface Props {
  pacienteId: string;
}

const ETIQUETAS: Record<string, string> = {
  dosis: 'Dosis',
  via: 'Vía',
  frecuencia: 'Frecuencia',
  duracion: 'Duración',
};

/**
 * El plan (P) y sus órdenes.
 *
 * El sistema lee el plan y propone; el médico firma. Esa separación es
 * literal en la interfaz: las propuestas se ven distintas de las órdenes,
 * viven en otra caja, y sólo cruzan al pulsar el botón. Hasta entonces no
 * existen en ninguna base y no pueden generar ningún cargo.
 *
 * Los huecos que el plan no especificaba se muestran como campos vacíos
 * para rellenar, nunca rellenos a ojo: un hueco visible se corrige antes
 * de firmar; uno inventado se firma sin mirar.
 */
export function PlanOrders({ pacienteId }: Props) {
  const [texto, setTexto] = useState('');
  const [propuestas, setPropuestas] = useState<OrdenPropuesta[]>([]);
  const [marcadas, setMarcadas] = useState<Set<number>>(new Set());
  const [ordenes, setOrdenes] = useState<Orden[]>([]);
  const [proponiendo, setProponiendo] = useState(false);
  const [firmando, setFirmando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargarOrdenes = useCallback(async () => {
    try {
      setOrdenes(await api.ordenes(pacienteId));
    } catch {
      setOrdenes([]);
    }
  }, [pacienteId]);

  useEffect(() => {
    setTexto('');
    setPropuestas([]);
    setMarcadas(new Set());
    setAviso(null);
    void cargarOrdenes();
  }, [cargarOrdenes]);

  async function proponer() {
    if (!texto.trim() || proponiendo) return;
    setProponiendo(true);
    setError(null);
    setAviso(null);
    try {
      const { propuestas: nuevas } = await api.proponerOrdenes(pacienteId, texto);
      setPropuestas(nuevas);
      // Todas vienen marcadas: revisar y desmarcar es más rápido que
      // marcar una a una, y ninguna se firma sin pulsar el botón.
      setMarcadas(new Set(nuevas.map((_, i) => i)));
      if (!nuevas.length) setAviso('No se identificó ninguna orden en este plan.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudieron proponer órdenes');
    } finally {
      setProponiendo(false);
    }
  }

  /**
   * Rellenar un hueco no lo borra de `faltantes`: el campo debe seguir
   * visible mientras se escribe en él. Lo que cambia es el aviso, que se
   * calcula al pintar según lo que ya tenga valor.
   */
  function editarCampo(indice: number, campo: string, valor: string) {
    setPropuestas((actuales) =>
      actuales.map((p, i) =>
        i === indice ? { ...p, detalle: { ...p.detalle, [campo]: valor } } : p,
      ),
    );
  }

  /**
   * Cambiar el término invalida el código: era el del término anterior.
   * Se borra en vez de arrastrarlo, aunque eso deje la orden sin tarifar,
   * porque un código que no corresponde al término factura otra cosa.
   */
  function editarTermino(indice: number, valor: string) {
    setPropuestas((actuales) =>
      actuales.map((p, i) =>
        i === indice
          ? {
              ...p,
              termino: valor,
              codigo: null,
              sistema: null,
              concepto_id: null,
              reconocida: false,
              generico: false,
            }
          : p,
      ),
    );
  }

  function alternar(indice: number) {
    setMarcadas((actuales) => {
      const copia = new Set(actuales);
      if (copia.has(indice)) copia.delete(indice);
      else copia.add(indice);
      return copia;
    });
  }

  async function firmar(indices: number[]) {
    if (!indices.length || firmando) return;
    setFirmando(true);
    setError(null);
    try {
      const seleccionadas = indices.map((i) => propuestas[i]);
      const { creadas } = await api.autorizarOrdenes(pacienteId, seleccionadas);
      // Lo firmado sale del borrador; lo que quede sigue siendo borrador.
      const restantes = propuestas.filter((_, i) => !indices.includes(i));
      setPropuestas(restantes);
      setMarcadas(new Set(restantes.map((_, i) => i)));
      setAviso(`${creadas} ${creadas === 1 ? 'orden generada' : 'órdenes generadas'}.`);
      await cargarOrdenes();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudieron generar las órdenes');
    } finally {
      setFirmando(false);
    }
  }

  const nMarcadas = marcadas.size;

  return (
    <div className="space-y-4">
      <section className="border border-slate-200 rounded-lg bg-white p-4 shadow-sm">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Plan
        </h3>
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') void proponer();
          }}
          placeholder="Dieta absoluta. Analgesia con morfina 3 mg IV cada 4 h. Control de amilasa en 24 h…"
          rows={6}
          disabled={proponiendo}
          className="w-full text-sm border border-slate-200 rounded-md p-3 resize-y
                     focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent
                     disabled:bg-slate-50 disabled:text-slate-400"
        />
        <div className="flex items-center gap-3 mt-3">
          <p className="text-xs text-slate-500 flex-1">
            El sistema propone las órdenes que lee en el plan. Ninguna existe
            hasta que la firmas.
          </p>
          <button
            type="button"
            onClick={proponer}
            disabled={proponiendo || !texto.trim()}
            className="text-sm px-4 py-1.5 rounded-md bg-indigo-600 text-white font-medium
                       hover:bg-indigo-700 disabled:bg-slate-300 flex items-center gap-2 shrink-0"
          >
            {proponiendo ? (
              <>
                <Loader2 size={15} className="animate-spin" aria-hidden />
                Leyendo el plan…
              </>
            ) : (
              <>
                <Sparkles size={15} aria-hidden />
                Proponer órdenes
              </>
            )}
          </button>
        </div>
      </section>

      {error && (
        <p
          role="alert"
          className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-md p-2"
        >
          {error}
        </p>
      )}
      {aviso && !error && (
        <p className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-md p-2">
          {aviso}
        </p>
      )}

      {propuestas.length > 0 && (
        <section className="border-2 border-dashed border-amber-300 rounded-lg bg-amber-50/40 p-4">
          <header className="flex items-baseline gap-2 mb-3">
            <h3 className="text-sm font-semibold text-slate-700">
              Órdenes propuestas ({propuestas.length})
            </h3>
            <span className="text-xs text-amber-700">
              borrador · todavía no existe ninguna
            </span>
          </header>

          <ul className="space-y-2">
            {propuestas.map((p, i) => (
              <li
                key={`${p.termino}-${i}`}
                className="bg-white border border-slate-200 rounded-md p-3 flex gap-3"
              >
                <input
                  type="checkbox"
                  checked={marcadas.has(i)}
                  onChange={() => alternar(i)}
                  aria-label={`Incluir ${p.termino}`}
                  className="mt-1 shrink-0 accent-indigo-600"
                />

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                    {/* El término se edita antes de firmar. El modelo a veces
                        devuelve una categoría («Medicamento») donde debería ir
                        el fármaco, y corregirlo aquí es un clic; descubrirlo
                        después de firmar, un incidente. */}
                    <input
                      value={p.termino}
                      onChange={(e) => editarTermino(i, e.target.value)}
                      aria-label={`Término de la orden ${i + 1}`}
                      className={`text-sm font-medium bg-transparent border-b px-0.5 min-w-0
                        focus:outline-none focus:border-indigo-400
                        ${
                          p.generico
                            ? 'text-rose-700 border-rose-300'
                            : 'text-slate-800 border-transparent hover:border-slate-200'
                        }`}
                    />
                    {p.reconocida ? (
                      <code className="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                        {p.codigo}
                      </code>
                    ) : (
                      <span
                        title="No está en el vocabulario: se ordenará igual, pero habrá que tarifarla a mano."
                        className="text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded"
                      >
                        sin código
                      </span>
                    )}
                    {Object.entries(p.detalle)
                      .filter(([, v]) => v.trim())
                      .map(([k, v]) => (
                        <span key={k} className="text-xs text-slate-600">
                          · {v}
                        </span>
                      ))}
                  </div>

                  {p.texto_origen && (
                    <p className="text-xs text-slate-500 italic mt-1 truncate">
                      «{p.texto_origen}»
                    </p>
                  )}

                  {p.faltantes.length > 0 && (
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {p.faltantes.some((c) => !(p.detalle[c] ?? '').trim()) ? (
                        <span className="text-[11px] text-amber-700 flex items-center gap-1">
                          <AlertTriangle size={12} aria-hidden />
                          El plan no lo especifica:
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-500 flex items-center gap-1">
                          <CheckCircle2 size={12} aria-hidden />
                          Completado por ti:
                        </span>
                      )}
                      {p.faltantes.map((campo) => (
                        <input
                          key={campo}
                          value={p.detalle[campo] ?? ''}
                          onChange={(e) => editarCampo(i, campo, e.target.value)}
                          placeholder={ETIQUETAS[campo] ?? campo}
                          aria-label={`${ETIQUETAS[campo] ?? campo} de ${p.termino}`}
                          className="text-xs border border-amber-300 rounded px-2 py-0.5 w-28
                                     focus:outline-none focus:ring-2 focus:ring-amber-400"
                        />
                      ))}
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => void firmar([i])}
                  disabled={firmando}
                  title="Generar esta orden"
                  className="self-start text-xs px-2.5 py-1.5 rounded-md border border-indigo-200
                             text-indigo-700 hover:bg-indigo-50 disabled:opacity-50
                             flex items-center gap-1.5 shrink-0"
                >
                  <PenLine size={13} aria-hidden />
                  Firmar
                </button>
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-3 mt-3">
            <p className="text-xs text-slate-500 flex-1">
              Lo que no firmes se descarta al salir: un borrador no deja rastro.
            </p>
            <button
              type="button"
              onClick={() => void firmar([...marcadas].sort((a, b) => a - b))}
              disabled={firmando || nMarcadas === 0}
              className="text-sm px-4 py-1.5 rounded-md bg-emerald-600 text-white font-medium
                         hover:bg-emerald-700 disabled:bg-slate-300 flex items-center gap-2 shrink-0"
            >
              {firmando ? (
                <Loader2 size={15} className="animate-spin" aria-hidden />
              ) : (
                <ClipboardCheck size={15} aria-hidden />
              )}
              Generar {nMarcadas} {nMarcadas === 1 ? 'orden' : 'órdenes'}
            </button>
          </div>
        </section>
      )}

      <section>
        <h3 className="text-sm font-semibold text-slate-700 mb-2">
          Órdenes activas ({ordenes.length})
        </h3>
        {ordenes.length === 0 ? (
          <p className="text-sm text-slate-500 bg-white border border-slate-200 rounded-lg p-4">
            Este paciente no tiene ninguna orden. Sin orden no puede haber cargo:
            es la primera pieza de la cadena.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {ordenes.map((o) => (
              <li
                key={o.id}
                className="bg-white border border-slate-200 rounded-md px-3 py-2
                           flex flex-wrap items-baseline gap-x-2 gap-y-1"
              >
                <CheckCircle2
                  size={14}
                  className={
                    o.estado === 'cumplida' ? 'text-emerald-600' : 'text-slate-300'
                  }
                  aria-hidden
                />
                <span className="text-sm text-slate-800">{o.termino}</span>
                {Object.entries(o.detalle ?? {})
                  .filter(([, v]) => String(v).trim())
                  .map(([k, v]) => (
                    // Los campos de medicación se leen solos («3 mg», «IV»);
                    // el resto necesita su etiqueta o queda un «· 1» que no
                    // dice nada.
                    <span key={k} className="text-xs text-slate-500">
                      · {k in ETIQUETAS ? '' : `${k}: `}
                      {String(v)}
                    </span>
                  ))}
                <span className="ml-auto text-[11px] text-slate-400 font-mono">
                  {o.estado}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
