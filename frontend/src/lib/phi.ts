/**
 * Cómo se lee un acoplamiento, en un solo sitio.
 *
 * El backend tiene dos derivados —`phi_legible` y `duda`— declarados como
 * propiedades de Python, así que **no viajan en el JSON**. La interfaz
 * tiene que reproducir la regla, y ésa es exactamente la clase de cosa que
 * se copia mal en cuatro componentes y acaba diciendo cosas distintas en
 * cada panel.
 *
 * La regla, y por qué: `phi` es la lectura ponderada, y para un protocolo
 * que declara categorías y no cocientes vale 0 porque no hay vector que
 * proyectar. Ese 0 no significa «ortogonal»: significa «aquí no se mide
 * así». Leerlo tal cual haría que la mayoría del índice —MDS, Atlanta,
 * Duke, ACR/EULAR declaran categorías— apareciera siempre en duda. Es un
 * fallo que el backend ya cometió dos veces, y no hace falta cometerlo una
 * tercera aquí.
 */
import type { Acoplamiento, VeredictoSemiotico } from './types';

/** Coincide con `UMBRAL_ACOPLAMIENTO` del backend. */
export const UMBRAL_ACOPLAMIENTO = 0.2;
export const UMBRAL_ARMONIA = 0.6;

/**
 * El Φ que este protocolo permite leer de verdad: la lectura ponderada, o
 * la categórica cuando la ponderada no existe.
 *
 * El discriminante es `cobertura === null`, el mismo que usan el backend y
 * la competencia abductiva: vale null exactamente cuando el protocolo no
 * declara ni un likelihood ratio.
 */
export function phiLegible(a: Acoplamiento): number {
  return a.cobertura === null && a.phi_categorico !== null ? a.phi_categorico : a.phi;
}

/** Si la lectura ponderada existe. Si no, la que manda es la categórica. */
export function esPonderada(a: Acoplamiento): boolean {
  return a.cobertura !== null;
}

/**
 * Los tres factores de la lectura que corresponda.
 *
 * Se devuelven tal cual, con sus `null`. Un `null` NO es un 0: dice que
 * ese factor no está definido —sin ninguna dimensión medida no hay ángulo
 * entre h y e, de modo que la dirección no vale 0, no existe— y pintarlo
 * como una barra al 0 % afirmaría algo sobre el caso.
 */
export function factores(a: Acoplamiento): {
  direccion: number | null;
  cobertura: number | null;
  explicacion: number | null;
  lectura: 'ponderada' | 'categórica';
} {
  return esPonderada(a)
    ? {
        direccion: a.direccion,
        cobertura: a.cobertura,
        explicacion: a.explicacion,
        lectura: 'ponderada',
      }
    : {
        direccion: a.direccion_categorica,
        cobertura: a.cobertura_categorica,
        explicacion: a.explicacion_categorica,
        lectura: 'categórica',
      };
}

/** Un número que puede no existir. Nunca «0» donde no hay medida. */
export function cifra(valor: number | null, decimales = 4): string {
  return valor === null ? 'n/d' : valor.toFixed(decimales);
}

/** Un factor como porcentaje, con la misma regla. */
export function porcentaje(valor: number | null): string {
  return valor === null ? 'n/d' : `${(valor * 100).toFixed(0)} %`;
}

export const TONO_VEREDICTO: Record<
  VeredictoSemiotico,
  { texto: string; fondo: string; borde: string; barra: string; leyenda: string }
> = {
  ARMONIA: {
    texto: 'text-emerald-700',
    fondo: 'bg-emerald-50',
    borde: 'border-emerald-200',
    barra: 'bg-emerald-500',
    leyenda: 'La hipótesis es operable: armoniza con el paciente entero.',
  },
  ACOPLAMIENTO_PARCIAL: {
    texto: 'text-sky-700',
    fondo: 'bg-sky-50',
    borde: 'border-sky-200',
    barra: 'bg-sky-500',
    leyenda: 'Encaja con lo que hay, y queda por mirar.',
  },
  INERCIA: {
    texto: 'text-slate-600',
    fondo: 'bg-slate-50',
    borde: 'border-slate-200',
    barra: 'bg-slate-400',
    leyenda: 'Ortogonal: la hipótesis no toca este caso. No es contradicción.',
  },
  FRICCION: {
    texto: 'text-amber-700',
    fondo: 'bg-amber-50',
    borde: 'border-amber-200',
    barra: 'bg-amber-500',
    leyenda: 'El contexto empieza a disentir de la hipótesis.',
  },
  DESARMONIA: {
    texto: 'text-rose-700',
    fondo: 'bg-rose-50',
    borde: 'border-rose-200',
    barra: 'bg-rose-500',
    leyenda: 'El contexto contradice la hipótesis.',
  },
};
