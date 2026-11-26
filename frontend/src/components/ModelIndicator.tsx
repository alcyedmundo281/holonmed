import { CircleAlert, CircleCheck, CircleHelp, CircleX } from 'lucide-react';
import type { SaludDelSistema } from '../lib/useEstadoSistema';

interface Vista {
  Icono: typeof CircleCheck;
  color: string;
  titulo: string;
  detalle: string;
}

function describir(salud: SaludDelSistema): Vista {
  const sinComprobar = (detalle: string): Vista => ({
    Icono: CircleHelp,
    color: 'text-slate-400',
    titulo: 'Modelo sin comprobar',
    detalle,
  });

  if (salud.fase === 'comprobando') return sinComprobar('Comprobando…');
  if (salud.fase === 'sin_servidor') return sinComprobar('HolonMed no responde');

  const { llm } = salud.estado;
  const configurados = [...new Set([llm.configurados?.clinico, llm.configurados?.router])]
    .filter(Boolean)
    .join(', ');

  switch (llm.estado) {
    case 'conectado':
      return {
        Icono: CircleCheck,
        color: 'text-emerald-400',
        titulo: 'Modelo conectado',
        detalle: configurados,
      };
    case 'falta_modelo':
      return {
        Icono: CircleAlert,
        color: 'text-amber-400',
        titulo: 'Falta el modelo',
        detalle: llm.faltantes.join(', '),
      };
    case 'sin_conexion':
      return {
        Icono: CircleX,
        color: 'text-rose-400',
        titulo: 'Modelo sin conexión',
        detalle: llm.host,
      };
    // Incluye un backend antiguo que no manda `estado`: ante la duda, no es verde.
    default:
      return sinComprobar('El servidor de modelos no dio una lista legible');
  }
}

/**
 * Símbolo permanente de la conexión con el modelo local.
 *
 * El veredicto lo da el backend en `/health`; aquí sólo se pinta. Cada estado
 * tiene icono y texto propios, para que no dependa sólo del color.
 */
export function ModelIndicator({ salud }: { salud: SaludDelSistema }) {
  const { Icono, color, titulo, detalle } = describir(salud);
  const explicacion =
    salud.fase === 'respondio' && salud.estado.llm.estado === 'conectado'
      ? `El servidor de ${salud.estado.llm.host} responde y ofrece: ${detalle}`
      : `${titulo}: ${detalle}`;

  return (
    <div
      role="status"
      title={explicacion}
      className="px-3 py-2 border-b border-slate-700 flex items-center gap-2 shrink-0"
    >
      <Icono size={15} className={`shrink-0 ${color}`} aria-hidden />
      <div className="min-w-0 leading-tight">
        <p className={`text-xs font-medium ${color}`}>{titulo}</p>
        <p className="text-[10px] text-slate-500 truncate">{detalle}</p>
      </div>
    </div>
  );
}
