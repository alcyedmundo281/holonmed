import { AlertTriangle, CheckCircle2, ChevronDown, XCircle } from 'lucide-react';
import { useState } from 'react';
import type { EstadoInfon, Infon } from '../lib/types';

// El color codifica el veredicto. Un hallazgo descartado se muestra igual
// de visible que uno validado: ocultar lo que el sistema rechazó impediría
// detectar cuándo rechaza de más.
const ESTILOS: Record<EstadoInfon, { borde: string; fondo: string; texto: string; Icono: typeof CheckCircle2 }> = {
  VALIDADO: {
    borde: 'border-l-emerald-500',
    fondo: 'bg-emerald-50',
    texto: 'text-emerald-900',
    Icono: CheckCircle2,
  },
  ALERTA: {
    borde: 'border-l-amber-500',
    fondo: 'bg-amber-50',
    texto: 'text-amber-900',
    Icono: AlertTriangle,
  },
  RUIDO: {
    borde: 'border-l-rose-400',
    fondo: 'bg-rose-50/60',
    texto: 'text-rose-900',
    Icono: XCircle,
  },
};

const LEYENDA: Record<EstadoInfon, string> = {
  VALIDADO: 'Concepto confirmado en el vocabulario y sostenido por la evidencia del texto.',
  ALERTA: 'El concepto existe, pero la auditoría no pudo confirmarlo. Revísalo.',
  RUIDO: 'Descartado: no se ancló a un concepto fiable. No entra en la historia.',
};

interface Props {
  infon: Infon;
  resaltado?: boolean;
  onSeleccionar?: () => void;
}

export function InfonCard({ infon, resaltado = false, onSeleccionar }: Props) {
  const [abierto, setAbierto] = useState(false);
  const estilo = ESTILOS[infon.estado];
  const { Icono } = estilo;

  return (
    <div
      className={`border-l-4 ${estilo.borde} ${estilo.fondo} rounded-r-md mb-2 shadow-sm
                  ${resaltado ? 'ring-2 ring-indigo-500' : ''}`}
    >
      <button
        type="button"
        onClick={() => {
          setAbierto(!abierto);
          onSeleccionar?.();
        }}
        className="w-full text-left p-3 flex items-start gap-3"
        aria-expanded={abierto}
      >
        <Icono size={18} className={`${estilo.texto} shrink-0 mt-0.5`} aria-hidden />

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between gap-2">
            <h4 className={`font-semibold ${estilo.texto} truncate`}>
              {/* La polaridad va delante del término y no en una etiqueta
                  al final: invierte el sentido del dato —una ausencia
                  documentada resta peso de evidencia en vez de sumarlo— y
                  leerla después del nombre llega tarde. */}
              {infon.polaridad === 'ausente' && (
                <span className="font-normal text-slate-500">no · </span>
              )}
              {infon.termino}
            </h4>
            <span className="text-xs font-mono text-slate-500 shrink-0">
              {infon.confianza.toFixed(0)}%
            </span>
          </div>

          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {infon.polaridad === 'ausente' && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 border border-slate-300">
                ausencia documentada
              </span>
            )}
            {/* Un infón derivado no es evidencia nueva: es la hipótesis
                misma, acuñada por el clasificador. Φ lo excluye de su
                vector para que el diagnóstico no figure como evidencia
                contra sí mismo, y aquí se marca por la misma razón. */}
            {infon.derivado_de.length > 0 && (
              <span
                className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800 border border-indigo-200"
                title={`Derivado de: ${infon.derivado_de.join(', ')}`}
              >
                derivado
              </span>
            )}
            {infon.codigo && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 border border-sky-200 font-mono">
                {infon.sistema}:{infon.codigo}
              </span>
            )}
            {infon.cie10_code && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-violet-100 text-violet-800 border border-violet-200 font-mono">
                CIE-10 {infon.cie10_code}
              </span>
            )}
            {infon.linaje_clinico && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                {infon.linaje_clinico}
              </span>
            )}
          </div>
        </div>

        <ChevronDown
          size={16}
          className={`text-slate-400 shrink-0 transition-transform ${abierto ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>

      {abierto && (
        <div className="px-3 pb-3 pt-0 ml-9 text-xs space-y-2 text-slate-700">
          <p className="italic text-slate-600 border-l-2 border-slate-300 pl-2">
            «{infon.texto_origen}»
          </p>

          {infon.termino_propuesto !== infon.termino && (
            <p>
              <span className="text-slate-500">El modelo propuso:</span>{' '}
              <span className="font-mono">{infon.termino_propuesto}</span>
              {infon.estado !== 'RUIDO' && ' → normalizado'}
            </p>
          )}

          <div className="grid grid-cols-2 gap-2">
            <Barra etiqueta="Ontología" valor={infon.score_ontologico} />
            <Barra etiqueta="Auditoría lógica" valor={infon.score_logico} />
          </div>

          <p className="text-slate-600 leading-relaxed">{infon.razon_auditoria}</p>

          {infon.derivado_de.length > 0 && (
            <p className="text-slate-600">
              <span className="text-slate-500">Derivado de:</span>{' '}
              {infon.derivado_de.join(', ')}
              {infon.criterio && (
                <>
                  {' · criterio '}
                  <code>{infon.criterio}</code>
                </>
              )}
            </p>
          )}

          <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-200">
            {LEYENDA[infon.estado]} · protocolo <code>{infon.origen_skill}</code>
          </p>
        </div>
      )}
    </div>
  );
}

function Barra({ etiqueta, valor }: { etiqueta: string; valor: number }) {
  return (
    <div>
      <div className="flex justify-between text-[11px] text-slate-500 mb-0.5">
        <span>{etiqueta}</span>
        <span className="font-mono">{valor.toFixed(0)}</span>
      </div>
      <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-slate-500 rounded-full"
          style={{ width: `${Math.min(100, Math.max(0, valor))}%` }}
        />
      </div>
    </div>
  );
}
