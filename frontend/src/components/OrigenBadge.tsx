import { Beaker, FlaskConical, HeartPulse, Pill, Scan, Stethoscope, User, Cpu } from 'lucide-react';
import type { OrigenTic } from '../lib/types';

/**
 * Distintivo del actor que produjo un registro.
 *
 * En un entorno clínico real la información no llega de un solo sitio: la
 * consulta dicta, el laboratorio informa, la farmacia dispensa. Todos
 * alimentan la misma historia, y saber de cuál viene cada dato cambia
 * cuánto se le concede al leerlo.
 *
 * El paciente es uno más, y se distingue a propósito: es quien más
 * variables conoce sobre su propio cuadro, y lo que trae no se lee igual
 * que lo que mide un analizador.
 */
const ESTILOS: Record<OrigenTic, { etiqueta: string; clase: string; Icono: typeof Stethoscope }> = {
  consulta: {
    etiqueta: 'Consulta',
    clase: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    Icono: Stethoscope,
  },
  laboratorio: {
    etiqueta: 'Laboratorio',
    clase: 'bg-sky-50 text-sky-700 border-sky-200',
    Icono: FlaskConical,
  },
  farmacia: {
    etiqueta: 'Farmacia',
    clase: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    Icono: Pill,
  },
  enfermeria: {
    etiqueta: 'Enfermería',
    clase: 'bg-rose-50 text-rose-700 border-rose-200',
    Icono: HeartPulse,
  },
  imagen: {
    etiqueta: 'Imagen',
    clase: 'bg-violet-50 text-violet-700 border-violet-200',
    Icono: Scan,
  },
  paciente: {
    etiqueta: 'Paciente',
    clase: 'bg-amber-50 text-amber-700 border-amber-200',
    Icono: User,
  },
  holonmed: {
    etiqueta: 'HolonMed',
    clase: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    Icono: Cpu,
  },
  otro: {
    etiqueta: 'Otro',
    clase: 'bg-slate-50 text-slate-600 border-slate-200',
    Icono: Beaker,
  },
};

export function OrigenBadge({
  origen,
  actor,
  compacto = false,
}: {
  origen: OrigenTic;
  actor?: string | null;
  compacto?: boolean;
}) {
  const estilo = ESTILOS[origen] ?? ESTILOS.otro;
  const { Icono } = estilo;

  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded border ${estilo.clase}`}
      title={actor ? `${estilo.etiqueta} · ${actor}` : estilo.etiqueta}
    >
      <Icono size={11} aria-hidden />
      {!compacto && estilo.etiqueta}
      {!compacto && actor && <span className="opacity-70">· {actor}</span>}
    </span>
  );
}

export const ORIGENES: OrigenTic[] = [
  'consulta',
  'laboratorio',
  'farmacia',
  'enfermeria',
  'imagen',
];

export function etiquetaOrigen(origen: OrigenTic): string {
  return (ESTILOS[origen] ?? ESTILOS.otro).etiqueta;
}
