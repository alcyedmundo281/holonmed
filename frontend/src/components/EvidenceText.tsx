import { useMemo } from 'react';
import type { EstadoInfon, Infon } from '../lib/types';

interface Props {
  texto: string;
  infones: Infon[];
  seleccionado: number | null;
  onSeleccionar: (indice: number | null) => void;
}

const FONDO: Record<EstadoInfon, string> = {
  VALIDADO: 'bg-emerald-100 hover:bg-emerald-200 decoration-emerald-500',
  ALERTA: 'bg-amber-100 hover:bg-amber-200 decoration-amber-500',
  RUIDO: 'bg-rose-50 hover:bg-rose-100 decoration-rose-400',
};

interface Tramo {
  inicio: number;
  fin: number;
  indice: number;
}

/**
 * La narrativa original con la evidencia de cada hallazgo resaltada.
 *
 * Es lo que convierte una lista de códigos en algo revisable: el clínico ve
 * *de dónde* salió cada infón sin tener que releer la nota buscándolo. Al
 * pulsar un fragmento se selecciona su hallazgo, y viceversa.
 *
 * Los fragmentos que el modelo cita pero que no aparecen literalmente en el
 * texto simplemente no se resaltan. Eso también es información: significa
 * que la cita es una paráfrasis y merece más desconfianza.
 */
export function EvidenceText({ texto, infones, seleccionado, onSeleccionar }: Props) {
  const tramos = useMemo(() => localizar(texto, infones), [texto, infones]);

  if (tramos.length === 0) {
    return <p className="whitespace-pre-wrap text-sm text-slate-700 leading-relaxed">{texto}</p>;
  }

  const piezas: React.ReactNode[] = [];
  let cursor = 0;

  tramos.forEach((tramo, i) => {
    if (tramo.inicio > cursor) {
      piezas.push(<span key={`t${i}`}>{texto.slice(cursor, tramo.inicio)}</span>);
    }
    const infon = infones[tramo.indice];
    const activo = seleccionado === tramo.indice;
    piezas.push(
      <mark
        key={`m${i}`}
        onClick={() => onSeleccionar(activo ? null : tramo.indice)}
        title={`${infon.termino} — ${infon.estado.toLowerCase()}`}
        className={`cursor-pointer rounded px-0.5 underline decoration-2 underline-offset-2
                    transition-colors ${FONDO[infon.estado]} ${
                      activo ? 'ring-2 ring-indigo-500 ring-offset-1' : ''
                    }`}
      >
        {texto.slice(tramo.inicio, tramo.fin)}
      </mark>,
    );
    cursor = tramo.fin;
  });

  if (cursor < texto.length) {
    piezas.push(<span key="final">{texto.slice(cursor)}</span>);
  }

  return (
    <p className="whitespace-pre-wrap text-sm text-slate-700 leading-relaxed">{piezas}</p>
  );
}

/**
 * Localiza la cita de cada infón dentro del texto original.
 *
 * Se busca sin distinguir mayúsculas ni acentos, porque el modelo
 * reescribe las citas con frecuencia. Los solapamientos se descartan: dos
 * marcas anidadas romperían el renderizado y confundirían más de lo que
 * aportan.
 */
function localizar(texto: string, infones: Infon[]): Tramo[] {
  const plano = normalizar(texto);
  const encontrados: Tramo[] = [];

  infones.forEach((infon, indice) => {
    const cita = infon.texto_origen?.trim();
    if (!cita || cita.length < 3) return;

    let inicio = plano.indexOf(normalizar(cita));
    // Si la cita completa no está, se intenta con su fragmento más largo:
    // suele bastar para anclar la frase correcta.
    if (inicio === -1) {
      const fragmento = cita
        .split(/[,;.]/)
        .map((s) => s.trim())
        .sort((a, b) => b.length - a.length)[0];
      if (!fragmento || fragmento.length < 4) return;
      inicio = plano.indexOf(normalizar(fragmento));
      if (inicio === -1) return;
      encontrados.push({ inicio, fin: inicio + fragmento.length, indice });
      return;
    }
    encontrados.push({ inicio, fin: inicio + cita.length, indice });
  });

  encontrados.sort((a, b) => a.inicio - b.inicio || b.fin - a.fin);

  const sinSolapes: Tramo[] = [];
  let ultimoFin = -1;
  for (const tramo of encontrados) {
    if (tramo.inicio >= ultimoFin) {
      sinSolapes.push(tramo);
      ultimoFin = tramo.fin;
    }
  }
  return sinSolapes;
}

/** Mismas reglas que `normalizar` en el backend, para que casen igual. */
function normalizar(texto: string): string {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}
