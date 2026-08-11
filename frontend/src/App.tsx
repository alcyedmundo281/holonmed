import { Activity, UserCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { ChatPanel } from './components/ChatPanel';
import { InferencePanel } from './components/InferencePanel';
import { InfonCard } from './components/InfonCard';
import { SystemStatus } from './components/SystemStatus';
import { TicComposer } from './components/TicComposer';
import { api } from './lib/api';
import type { EstadoSistema, Paciente, ResultadoTic, Skill } from './lib/types';

const PACIENTE_INICIAL: Paciente = { _key: 'demo', nombre: 'Paciente Demo' };

export default function App() {
  const [estado, setEstado] = useState<EstadoSistema | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [paciente, setPaciente] = useState<Paciente>(PACIENTE_INICIAL);
  const [tic, setTic] = useState<ResultadoTic | null>(null);

  useEffect(() => {
    // El fallo de cualquiera de estas llamadas no debe dejar la app en
    // blanco: el aviso de estado ya explica qué falta.
    api.estado().then(setEstado).catch(() => setEstado(null));
    api.skills().then(setSkills).catch(() => setSkills([]));
    api
      .pacientes()
      .then((lista) => {
        setPacientes(lista);
        if (lista.length > 0) setPaciente(lista[0]);
      })
      .catch(() => setPacientes([]));
  }, []);

  const validados = tic?.infones.filter((i) => i.estado === 'VALIDADO').length ?? 0;
  const alertas = tic?.infones.filter((i) => i.estado === 'ALERTA').length ?? 0;
  const descartados = tic?.infones.filter((i) => i.estado === 'RUIDO').length ?? 0;

  return (
    <div className="flex flex-col h-screen bg-slate-100">
      <SystemStatus estado={estado} />

      <div className="flex flex-1 min-h-0">
        {/* Columna izquierda: acciones */}
        <aside className="w-[340px] shrink-0 border-r border-slate-700 bg-slate-800 flex flex-col">
          <header className="p-4 border-b border-slate-700 flex items-center gap-2">
            <Activity size={18} className="text-emerald-400" aria-hidden />
            <span className="font-bold text-slate-100">HolonMed</span>
            <span className="text-[10px] text-slate-400 ml-auto font-mono">v0.1.0</span>
          </header>
          <ChatPanel pacienteId={paciente._key} />
        </aside>

        {/* Columna principal: cristalización */}
        <main className="flex-1 flex flex-col min-w-0">
          <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <div className="bg-indigo-100 p-2 rounded-full text-indigo-600 shrink-0">
                <UserCircle size={22} aria-hidden />
              </div>
              <div className="min-w-0">
                {pacientes.length > 0 ? (
                  <select
                    value={paciente._key}
                    onChange={(e) => {
                      const elegido = pacientes.find((p) => p._key === e.target.value);
                      if (elegido) {
                        setPaciente(elegido);
                        setTic(null); // no arrastrar resultados entre pacientes
                      }
                    }}
                    aria-label="Paciente activo"
                    className="font-semibold text-slate-800 bg-transparent border-0 p-0
                               focus:outline-none focus:ring-2 focus:ring-indigo-400 rounded cursor-pointer"
                  >
                    {pacientes.map((p) => (
                      <option key={p._key} value={p._key}>
                        {p.nombre}
                      </option>
                    ))}
                  </select>
                ) : (
                  <h1 className="font-semibold text-slate-800 truncate">{paciente.nombre}</h1>
                )}
                <p className="text-[11px] text-slate-500 font-mono">
                  {paciente._key}
                  {paciente.edad ? ` · ${paciente.edad} años` : ''}
                </p>
              </div>
            </div>

            {tic && (
              <div className="flex items-center gap-3 text-xs shrink-0">
                <Contador n={validados} etiqueta="validados" color="text-emerald-600" />
                <Contador n={alertas} etiqueta="en alerta" color="text-amber-600" />
                <Contador n={descartados} etiqueta="descartados" color="text-rose-500" />
              </div>
            )}
          </header>

          <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0">
            <TicComposer
              pacienteId={paciente._key}
              skills={skills}
              onResultado={setTic}
            />

            {tic && (
              <>
                <div className="flex items-baseline gap-2 text-xs text-slate-500">
                  <span>
                    Protocolo aplicado:{' '}
                    <code className="text-slate-700">{tic.skill_activa}</code>
                  </span>
                  {tic.tic_id && <span className="font-mono">· tic {tic.tic_id}</span>}
                  {!tic.tic_id && <span className="text-amber-600">· no persistido</span>}
                </div>

                {tic.resumen && (
                  <p className="text-sm text-slate-700 bg-white border border-slate-200 rounded-lg p-3">
                    {tic.resumen}
                  </p>
                )}

                {tic.inferencia && <InferencePanel inferencia={tic.inferencia} />}

                {tic.infones.length > 0 ? (
                  <section>
                    <h3 className="text-sm font-semibold text-slate-700 mb-2">
                      Infones extraídos ({tic.infones.length})
                    </h3>
                    {tic.infones.map((infon, i) => (
                      <InfonCard key={`${infon.termino_snomed}-${i}`} infon={infon} />
                    ))}
                  </section>
                ) : (
                  <p className="text-sm text-slate-500 bg-white border border-slate-200 rounded-lg p-4">
                    No se extrajo ningún hallazgo de este texto.
                  </p>
                )}
              </>
            )}
          </div>

          <footer className="border-t border-slate-200 bg-white px-6 py-2 shrink-0">
            <p className="text-[11px] text-slate-400">
              Herramienta de apoyo a la decisión clínica. No es un dispositivo
              médico y no sustituye el juicio de un profesional sanitario.
            </p>
          </footer>
        </main>
      </div>
    </div>
  );
}

function Contador({ n, etiqueta, color }: { n: number; etiqueta: string; color: string }) {
  return (
    <span className={n > 0 ? color : 'text-slate-300'}>
      <span className="font-bold tabular-nums">{n}</span>{' '}
      <span className="text-slate-500">{etiqueta}</span>
    </span>
  );
}
