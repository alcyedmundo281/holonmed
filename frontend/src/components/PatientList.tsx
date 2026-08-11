import { Plus, Search, UserPlus, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { api } from '../lib/api';
import type { Paciente } from '../lib/types';

interface Props {
  pacientes: Paciente[];
  activo: string | null;
  onSeleccionar: (paciente: Paciente) => void;
  onCreado: () => void;
}

/**
 * Lista de pacientes con búsqueda y alta rápida.
 *
 * El filtro es local porque la lista cabe en memoria en una consulta
 * individual: filtrar sin ida y vuelta al servidor hace que teclear se
 * sienta instantáneo, que es la diferencia entre usarlo y no usarlo.
 */
export function PatientList({ pacientes, activo, onSeleccionar, onCreado }: Props) {
  const [filtro, setFiltro] = useState('');
  const [creando, setCreando] = useState(false);

  const visibles = useMemo(() => {
    const q = filtro.trim().toLowerCase();
    if (!q) return pacientes;
    return pacientes.filter((p) => p.nombre.toLowerCase().includes(q));
  }, [pacientes, filtro]);

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="p-2 border-b border-slate-700 flex gap-1.5">
        <div className="relative flex-1">
          <Search
            size={13}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-500"
            aria-hidden
          />
          <input
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
            placeholder="Buscar paciente…"
            aria-label="Buscar paciente"
            className="w-full text-xs bg-slate-700 text-slate-100 placeholder-slate-400
                       rounded pl-7 pr-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>
        <button
          type="button"
          onClick={() => setCreando(true)}
          title="Nuevo paciente"
          aria-label="Nuevo paciente"
          className="px-2 rounded bg-slate-700 text-slate-300 hover:bg-slate-600"
        >
          <Plus size={14} aria-hidden />
        </button>
      </div>

      <ul className="flex-1 overflow-y-auto min-h-0">
        {visibles.length === 0 && (
          <li className="p-4 text-xs text-slate-500 text-center">
            {pacientes.length === 0 ? 'Aún no hay pacientes.' : 'Sin coincidencias.'}
          </li>
        )}

        {visibles.map((p) => (
          <li key={p.id}>
            <button
              type="button"
              onClick={() => onSeleccionar(p)}
              aria-current={p.id === activo}
              className={`w-full text-left px-3 py-2 border-l-2 transition-colors ${
                p.id === activo
                  ? 'border-l-indigo-400 bg-slate-700/60'
                  : 'border-l-transparent hover:bg-slate-700/30'
              }`}
            >
              <div className="text-sm text-slate-100 truncate">{p.nombre}</div>
              <div className="text-[11px] text-slate-400 flex gap-2">
                {p.edad != null && <span>{p.edad} a</span>}
                {p.sexo && <span>{p.sexo[0].toUpperCase()}</span>}
                {p.tics ? <span>{p.tics} consultas</span> : <span>sin consultas</span>}
              </div>
            </button>
          </li>
        ))}
      </ul>

      {creando && (
        <NuevoPaciente
          onCerrar={() => setCreando(false)}
          onCreado={() => {
            setCreando(false);
            onCreado();
          }}
        />
      )}
    </div>
  );
}

function NuevoPaciente({
  onCerrar,
  onCreado,
}: {
  onCerrar: () => void;
  onCreado: () => void;
}) {
  const [nombre, setNombre] = useState('');
  const [edad, setEdad] = useState('');
  const [sexo, setSexo] = useState('');
  const [antecedentes, setAntecedentes] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  async function guardar() {
    if (!nombre.trim() || guardando) return;
    setGuardando(true);
    setError(null);
    try {
      await api.crearPaciente({
        nombre: nombre.trim(),
        edad: edad ? Number(edad) : null,
        sexo: sexo || null,
        antecedentes: antecedentes.trim(),
      });
      onCreado();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error creando el paciente');
      setGuardando(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Nuevo paciente"
      onKeyDown={(e) => e.key === 'Escape' && onCerrar()}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-slate-800 flex items-center gap-2">
            <UserPlus size={17} className="text-indigo-600" aria-hidden />
            Nuevo paciente
          </h2>
          <button type="button" onClick={onCerrar} aria-label="Cerrar">
            <X size={16} className="text-slate-400 hover:text-slate-600" aria-hidden />
          </button>
        </div>

        <div className="space-y-3">
          <Campo etiqueta="Nombre">
            <input
              autoFocus
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && guardar()}
              className={entrada}
            />
          </Campo>

          <div className="grid grid-cols-2 gap-3">
            <Campo etiqueta="Edad">
              <input
                type="number"
                min={0}
                max={130}
                value={edad}
                onChange={(e) => setEdad(e.target.value)}
                className={entrada}
              />
            </Campo>
            <Campo etiqueta="Sexo">
              <select
                value={sexo}
                onChange={(e) => setSexo(e.target.value)}
                className={entrada}
              >
                <option value="">—</option>
                <option value="femenino">Femenino</option>
                <option value="masculino">Masculino</option>
                <option value="otro">Otro</option>
              </select>
            </Campo>
          </div>

          <Campo etiqueta="Antecedentes">
            <textarea
              rows={3}
              value={antecedentes}
              onChange={(e) => setAntecedentes(e.target.value)}
              placeholder="Alimentan la probabilidad a priori del motor bayesiano"
              className={`${entrada} resize-y`}
            />
          </Campo>
        </div>

        {error && (
          <p role="alert" className="text-xs text-rose-700 mt-3">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 mt-5">
          <button
            type="button"
            onClick={onCerrar}
            className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded-md"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={guardar}
            disabled={!nombre.trim() || guardando}
            className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-md
                       hover:bg-indigo-700 disabled:bg-slate-300"
          >
            {guardando ? 'Guardando…' : 'Crear'}
          </button>
        </div>
      </div>
    </div>
  );
}

const entrada =
  'w-full text-sm border border-slate-300 rounded-md px-2.5 py-1.5 ' +
  'focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent';

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600 block mb-1">{etiqueta}</span>
      {children}
    </label>
  );
}
