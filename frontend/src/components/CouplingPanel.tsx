import { ChevronDown, Compass, HelpCircle } from 'lucide-react';
import { useState } from 'react';
import {
  cifra,
  factores,
  phiLegible,
  porcentaje,
  TONO_VEREDICTO,
} from '../lib/phi';
import type { Acoplamiento } from '../lib/types';

/**
 * El segundo eje: cuánto armoniza la hipótesis con el paciente entero.
 *
 * Se lee JUNTO a la probabilidad y nunca en su lugar. Bayes dice cuánta
 * evidencia hay; Φ dice si esa hipótesis, tomada como regla de acción,
 * encaja con el resto del paciente. Son preguntas distintas y pueden
 * discrepar — y cuando discrepan, la discrepancia es información clínica.
 *
 * Los tres factores se informan y NUNCA se vuelven a aplicar: ya están
 * dentro del coseno. Se muestran para poder leer *por qué* salió ese
 * número, porque el número fundido no distingue «nada la contradice
 * todavía» de «se puso a prueba y aguanta a medias».
 */
export function CouplingPanel({ acoplamiento }: { acoplamiento: Acoplamiento }) {
  const [abierto, setAbierto] = useState(false);
  const phi = phiLegible(acoplamiento);
  const tono = TONO_VEREDICTO[acoplamiento.veredicto];
  const { direccion, cobertura, explicacion, lectura } = factores(acoplamiento);

  // Φ vive en [−1, +1] y la barra en [0, 100]: el centro es el 50 %.
  const posicion = ((phi + 1) / 2) * 100;

  return (
    <section className={`border ${tono.borde} rounded-lg ${tono.fondo} p-4 mb-4 shadow-sm`}>
      <header className="flex items-center gap-2 mb-3">
        <Compass size={16} className="text-indigo-600" aria-hidden />
        <h3 className="font-semibold text-slate-800 text-sm">Acoplamiento semiótico</h3>
        <span className="text-[11px] text-slate-500 ml-auto">
          lectura {lectura}
        </span>
      </header>

      <div className="flex items-baseline justify-between mb-1">
        <span className="font-medium text-slate-900">{acoplamiento.hipotesis}</span>
        <span className={`text-2xl font-bold tabular-nums ${tono.texto}`}>
          Φ {phi.toFixed(4)}
        </span>
      </div>

      {/* La escala va de −1 a +1, así que el cero se marca: sin la marca,
          una barra a media altura se leería como «la mitad de bien». */}
      <div className="relative h-2 bg-slate-200 rounded-full overflow-hidden mb-1">
        <div
          className={`h-full ${tono.barra} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(100, Math.max(0, posicion))}%` }}
        />
        <div className="absolute inset-y-0 left-1/2 w-px bg-slate-400/70" aria-hidden />
      </div>
      <div className="flex justify-between text-[10px] text-slate-400 mb-2" aria-hidden>
        <span>−1</span>
        <span>0</span>
        <span>+1</span>
      </div>

      <p className="text-xs text-slate-600 mb-3">
        <span className={`font-medium ${tono.texto}`}>{acoplamiento.veredicto}</span>
        {' · '}
        {tono.leyenda}
      </p>

      <div className="grid grid-cols-3 gap-2 mb-3">
        {/* La dirección NO es una proporción: es un coseno en [−1, +1], y
            un −1 significa «el registro contradice», no «menos cero por
            ciento». Las otras dos sí son fracciones de una superficie. */}
        <Factor
          etiqueta="dirección"
          valor={direccion}
          signado
          ayuda="De lo que se ha mirado, cuánto concuerda con la hipótesis. Va de −1 (contradice) a +1 (concuerda)."
        />
        <Factor
          etiqueta="cobertura"
          valor={cobertura}
          ayuda="De lo que la hipótesis afirma, cuánto se ha puesto a prueba."
        />
        <Factor
          etiqueta="explicación"
          valor={explicacion}
          ayuda="De lo que el paciente tiene, cuánto cae dentro de la hipótesis."
        />
      </div>

      {acoplamiento.indagacion.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-medium text-slate-700 mb-1 flex items-center gap-1.5">
            <HelpCircle size={12} aria-hidden />
            Hacia dónde indagar
          </h4>
          <ul className="space-y-0.5">
            {acoplamiento.indagacion.map((pregunta, i) => (
              <li
                key={i}
                className="text-xs text-slate-700 pl-3 border-l-2 border-indigo-300"
              >
                {pregunta}
              </li>
            ))}
          </ul>
        </div>
      )}

      {acoplamiento.resto_no_simbolizado.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-medium text-slate-700 mb-1">
            Sin explicar por esta hipótesis ({acoplamiento.resto_no_simbolizado.length})
          </h4>
          <div className="flex flex-wrap gap-1">
            {acoplamiento.resto_no_simbolizado.map((termino) => (
              <span
                key={termino}
                className="text-[11px] px-2 py-0.5 rounded-full bg-white text-slate-600 border border-slate-300"
              >
                {termino}
              </span>
            ))}
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setAbierto(!abierto)}
        aria-expanded={abierto}
        className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
      >
        <ChevronDown
          size={13}
          className={`transition-transform ${abierto ? 'rotate-180' : ''}`}
          aria-hidden
        />
        Traza del cálculo ({acoplamiento.traza.length} pasos)
      </button>

      {abierto && (
        <div className="mt-2 space-y-2 text-[11px]">
          <ul className="space-y-0.5">
            {acoplamiento.traza.map((paso, i) => (
              <li key={i} className="text-slate-600 pl-3 border-l-2 border-slate-300">
                {paso}
              </li>
            ))}
          </ul>

          {acoplamiento.componentes.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="text-slate-500">
                  <tr>
                    <th className="font-medium py-1 pr-2">Dimensión</th>
                    <th className="font-medium py-1 pr-2 text-right">hᵢ</th>
                    <th className="font-medium py-1 pr-2 text-right">eᵢ</th>
                    <th className="font-medium py-1">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {acoplamiento.componentes.map((c, i) => (
                    <tr key={`${c.dimension}-${i}`} className="border-t border-slate-200">
                      <td className="py-1 pr-2 text-slate-700">{c.dimension}</td>
                      <td className="py-1 pr-2 text-right tabular-nums text-slate-600">
                        {c.esperado.toFixed(3)}
                      </td>
                      <td className="py-1 pr-2 text-right tabular-nums text-slate-600">
                        {c.observado.toFixed(3)}
                      </td>
                      <td className="py-1 text-slate-500">{c.detalle}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-slate-500 pt-1 border-t border-slate-200 leading-relaxed">
            α = {acoplamiento.anclaje.toFixed(4)} · cos = {cifra(acoplamiento.coseno)}
            {' · '}
            Los tres factores se publican redondeados a cuatro decimales y el
            producto se calcula sin redondear, así que recomponer la
            multiplicación aquí puede dar un número ligeramente distinto del
            coseno. El que manda es el coseno.
          </p>
        </div>
      )}

      <p className="mt-3 pt-2 border-t border-slate-200/70 text-[11px] text-slate-400 leading-relaxed">
        Φ se lee junto a la probabilidad, nunca en su lugar: Bayes dice cuánta
        evidencia hay y esto dice si la hipótesis armoniza con el paciente
        entero. Cuando discrepan, la discrepancia es información clínica.
      </p>
    </section>
  );
}

/**
 * Un factor con su barra. `null` se pinta como «n/d» y sin barra: un cero
 * afirmaría algo sobre el caso —«lo mirado no concuerda»— donde lo que
 * ocurre es que no hay nada con lo que preguntarlo.
 */
function Factor({
  etiqueta,
  valor,
  ayuda,
  signado = false,
}: {
  etiqueta: string;
  valor: number | null;
  ayuda: string;
  /** El valor vive en [−1, +1] y no en [0, 1]: se pinta desde el centro. */
  signado?: boolean;
}) {
  const negativo = valor !== null && valor < 0;
  // Signada, la barra crece desde el centro hacia el lado que le toca; una
  // proporción crece desde la izquierda. Pintar un −1 como una barra vacía
  // lo confundiría con «no se ha mirado nada», que es lo contrario.
  const ancho =
    valor === null
      ? 0
      : signado
        ? Math.min(50, Math.abs(valor) * 50)
        : Math.min(100, Math.max(0, valor * 100));

  return (
    <div title={ayuda}>
      <div className="flex justify-between items-baseline text-[11px] mb-0.5">
        <span className="text-slate-600">{etiqueta}</span>
        <span
          className={`tabular-nums font-medium ${
            valor === null
              ? 'text-slate-400 italic'
              : negativo
                ? 'text-rose-700'
                : 'text-slate-800'
          }`}
        >
          {valor === null ? 'n/d' : signado ? valor.toFixed(2) : porcentaje(valor)}
        </span>
      </div>
      <div className="relative h-1.5 bg-white rounded-full overflow-hidden border border-slate-200">
        {valor !== null && (
          <div
            className={`absolute inset-y-0 rounded-full ${
              negativo ? 'bg-rose-400' : 'bg-indigo-400'
            }`}
            style={
              signado
                ? negativo
                  ? { right: '50%', width: `${ancho}%` }
                  : { left: '50%', width: `${ancho}%` }
                : { left: 0, width: `${ancho}%` }
            }
          />
        )}
        {signado && (
          <div className="absolute inset-y-0 left-1/2 w-px bg-slate-300" aria-hidden />
        )}
      </div>
    </div>
  );
}
