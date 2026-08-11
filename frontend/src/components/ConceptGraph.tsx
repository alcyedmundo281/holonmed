import { useMemo, useState } from 'react';
import type { Grafo, NodoGrafo } from '../lib/types';

/**
 * El subgrafo clínico del paciente, en SVG puro.
 *
 * Deliberadamente no se usa una simulación de fuerzas. El grafo tiene
 * jerarquía real — hallazgos abajo, agrupaciones arriba — y una disposición
 * por niveles la hace legible de un vistazo, mientras que un layout de
 * fuerzas la escondería tras un ovillo que además se mueve. Menos de 500
 * líneas de dependencia y determinista entre recargas.
 */
export function ConceptGraph({ grafo }: { grafo: Grafo }) {
  const [activo, setActivo] = useState<number | null>(null);

  const disposicion = useMemo(() => calcular(grafo), [grafo]);

  if (grafo.nodos.length === 0) {
    return (
      <p className="text-sm text-slate-500 bg-white border border-slate-200 rounded-lg p-6 text-center">
        Aún no hay conceptos validados para este paciente. El grafo se
        construye a partir de los hallazgos que superan la validación.
      </p>
    );
  }

  const { nodos, ancho, alto } = disposicion;
  const posicion = new Map(nodos.map((n) => [n.id, n]));

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3">
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${ancho} ${alto}`}
          className="w-full"
          style={{ minWidth: Math.min(ancho, 900), height: alto }}
          role="img"
          aria-label="Grafo de conceptos del paciente"
        >
          <g stroke="#cbd5e1" strokeWidth={1.5} fill="none">
            {grafo.aristas.map((a, i) => {
              const o = posicion.get(a.origen);
              const d = posicion.get(a.destino);
              if (!o || !d) return null;
              const resaltada = activo === a.origen || activo === a.destino;
              return (
                <path
                  key={i}
                  d={`M ${o.x} ${o.y} C ${o.x} ${(o.y + d.y) / 2}, ${d.x} ${(o.y + d.y) / 2}, ${d.x} ${d.y}`}
                  stroke={resaltada ? '#6366f1' : '#cbd5e1'}
                  strokeWidth={resaltada ? 2.5 : 1.5}
                />
              );
            })}
          </g>

          {nodos.map((n) => {
            const esHallazgo = n.tipo === 'hallazgo';
            const r = esHallazgo ? 6 + Math.min(6, n.peso) : 5;
            const resaltado = activo === n.id;
            return (
              <g
                key={n.id}
                transform={`translate(${n.x} ${n.y})`}
                onMouseEnter={() => setActivo(n.id)}
                onMouseLeave={() => setActivo(null)}
                className="cursor-pointer"
              >
                <circle
                  r={r}
                  fill={esHallazgo ? '#10b981' : '#94a3b8'}
                  stroke={resaltado ? '#4338ca' : 'white'}
                  strokeWidth={resaltado ? 3 : 2}
                />
                <text
                  y={esHallazgo ? r + 14 : -r - 8}
                  textAnchor="middle"
                  className="pointer-events-none"
                  fontSize={11}
                  fill={esHallazgo ? '#0f172a' : '#64748b'}
                  fontWeight={esHallazgo ? 500 : 400}
                >
                  {recortar(n.termino, 26)}
                </text>
                {esHallazgo && n.peso > 1 && (
                  <text
                    textAnchor="middle"
                    y={3.5}
                    fontSize={9}
                    fill="white"
                    fontWeight={700}
                    className="pointer-events-none"
                  >
                    {n.peso}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="flex gap-4 mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-500">
        <Leyenda color="#10b981" texto="Hallazgo validado (el tamaño indica repeticiones)" />
        <Leyenda color="#94a3b8" texto="Concepto que los agrupa" />
      </div>
    </div>
  );
}

function Leyenda({ color, texto }: { color: string; texto: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <svg width={10} height={10} aria-hidden>
        <circle cx={5} cy={5} r={4} fill={color} />
      </svg>
      {texto}
    </span>
  );
}

interface NodoPosicionado extends NodoGrafo {
  x: number;
  y: number;
}

/**
 * Disposición por niveles: cuanto más general es un concepto, más arriba.
 *
 * El nivel se deduce de las aristas — un nodo está por encima de todo lo
 * que apunta hacia él — recorriendo el grafo desde las hojas.
 */
function calcular(grafo: Grafo): { nodos: NodoPosicionado[]; ancho: number; alto: number } {
  const nivel = new Map<number, number>();
  grafo.nodos.forEach((n) => nivel.set(n.id, n.tipo === 'hallazgo' ? 0 : 1));

  // Se propaga hacia arriba hasta que se estabiliza. El grafo es pequeño
  // (decenas de nodos) y acíclico, así que unas pocas pasadas bastan.
  for (let paso = 0; paso < 6; paso++) {
    let cambio = false;
    for (const a of grafo.aristas) {
      const abajo = nivel.get(a.origen) ?? 0;
      const arriba = nivel.get(a.destino) ?? 1;
      if (arriba <= abajo) {
        nivel.set(a.destino, abajo + 1);
        cambio = true;
      }
    }
    if (!cambio) break;
  }

  const porNivel = new Map<number, NodoGrafo[]>();
  for (const n of grafo.nodos) {
    const l = nivel.get(n.id) ?? 0;
    if (!porNivel.has(l)) porNivel.set(l, []);
    porNivel.get(l)!.push(n);
  }

  const niveles = [...porNivel.keys()].sort((a, b) => b - a); // general arriba
  const masAncho = Math.max(...[...porNivel.values()].map((v) => v.length), 1);
  const ancho = Math.max(640, masAncho * 150);
  const separacionY = 110;
  const alto = niveles.length * separacionY + 60;

  const nodos: NodoPosicionado[] = [];
  niveles.forEach((l, fila) => {
    const enFila = porNivel.get(l)!;
    // Ordenar por término mantiene la posición estable entre recargas: un
    // grafo que salta cada vez que se abre es difícil de leer.
    enFila.sort((a, b) => a.termino.localeCompare(b.termino));
    const paso = ancho / (enFila.length + 1);
    enFila.forEach((n, i) => {
      nodos.push({ ...n, x: paso * (i + 1), y: 40 + fila * separacionY });
    });
  });

  return { nodos, ancho, alto };
}

function recortar(texto: string, max: number): string {
  return texto.length <= max ? texto : `${texto.slice(0, max - 1)}…`;
}
