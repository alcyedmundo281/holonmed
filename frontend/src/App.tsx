import {
  Activity,
  ClipboardList,
  History,
  MessageSquare,
  Network,
  Stethoscope,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { ChatPanel } from './components/ChatPanel';
import { ConceptGraph } from './components/ConceptGraph';
import { EvidenceText } from './components/EvidenceText';
import { HistoryTimeline } from './components/HistoryTimeline';
import { InferencePanel } from './components/InferencePanel';
import { InfonCard } from './components/InfonCard';
import { PatientList } from './components/PatientList';
import { ProblemList } from './components/ProblemList';
import { SystemStatus } from './components/SystemStatus';
import { TicComposer } from './components/TicComposer';
import { api } from './lib/api';
import type {
  EntradaHistorial,
  EstadoSistema,
  Grafo,
  Paciente,
  Problema,
  ResultadoTic,
  Skill,
} from './lib/types';

type Vista = 'consulta' | 'problemas' | 'historia' | 'grafo';

const PESTANAS: { id: Vista; etiqueta: string; Icono: typeof Stethoscope }[] = [
  { id: 'consulta', etiqueta: 'Consulta', Icono: Stethoscope },
  { id: 'problemas', etiqueta: 'Problemas', Icono: ClipboardList },
  { id: 'historia', etiqueta: 'Historia', Icono: History },
  { id: 'grafo', etiqueta: 'Grafo', Icono: Network },
];

export default function App() {
  const [estado, setEstado] = useState<EstadoSistema | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [paciente, setPaciente] = useState<Paciente | null>(null);

  const [vista, setVista] = useState<Vista>('consulta');
  const [tic, setTic] = useState<ResultadoTic | null>(null);
  const [seleccionado, setSeleccionado] = useState<number | null>(null);

  const [problemas, setProblemas] = useState<Problema[]>([]);
  const [historial, setHistorial] = useState<EntradaHistorial[]>([]);
  const [grafo, setGrafo] = useState<Grafo>({ nodos: [], aristas: [] });
  const [chatAbierto, setChatAbierto] = useState(false);

  const cargarPacientes = useCallback(async () => {
    try {
      const lista = await api.pacientes();
      setPacientes(lista);
      setPaciente((actual) => actual ?? lista[0] ?? null);
    } catch {
      setPacientes([]);
    }
  }, []);

  useEffect(() => {
    // Ninguna de estas llamadas debe poder dejar la app en blanco: el
    // aviso de estado ya explica qué falta si algo no responde.
    api.estado().then(setEstado).catch(() => setEstado(null));
    api.skills().then(setSkills).catch(() => setSkills([]));
    void cargarPacientes();
  }, [cargarPacientes]);

  // Los datos derivados del paciente se recargan al cambiar de paciente o
  // al terminar un tic, que son los dos momentos en que pueden variar.
  const refrescarPaciente = useCallback(async (id: string) => {
    const [p, h, g] = await Promise.allSettled([
      api.problemas(id),
      api.historial(id),
      api.grafoPaciente(id),
    ]);
    setProblemas(p.status === 'fulfilled' ? p.value : []);
    setHistorial(h.status === 'fulfilled' ? h.value : []);
    setGrafo(g.status === 'fulfilled' ? g.value : { nodos: [], aristas: [] });
  }, []);

  useEffect(() => {
    if (paciente) void refrescarPaciente(paciente.id);
  }, [paciente, refrescarPaciente]);

  function seleccionarPaciente(p: Paciente) {
    setPaciente(p);
    setTic(null); // no arrastrar resultados de un paciente a otro
    setSeleccionado(null);
    setVista('consulta');
  }

  function alTerminarTic(resultado: ResultadoTic) {
    setTic(resultado);
    setSeleccionado(null);
    if (paciente) void refrescarPaciente(paciente.id);
    void cargarPacientes();
  }

  const validados = tic?.infones.filter((i) => i.estado === 'VALIDADO').length ?? 0;
  const alertas = tic?.infones.filter((i) => i.estado === 'ALERTA').length ?? 0;
  const descartados = tic?.infones.filter((i) => i.estado === 'RUIDO').length ?? 0;

  return (
    <div className="flex flex-col h-screen bg-slate-100">
      <SystemStatus estado={estado} />

      <div className="flex flex-1 min-h-0">
        <aside className="w-[260px] shrink-0 border-r border-slate-700 bg-slate-800 flex flex-col">
          <header className="px-3 py-3 border-b border-slate-700 flex items-center gap-2">
            <Activity size={17} className="text-emerald-400" aria-hidden />
            <span className="font-bold text-slate-100 text-sm">HolonMed</span>
            <span className="text-[10px] text-slate-500 ml-auto font-mono">v0.2.0</span>
          </header>

          <PatientList
            pacientes={pacientes}
            activo={paciente?.id ?? null}
            onSeleccionar={seleccionarPaciente}
            onCreado={cargarPacientes}
          />

          <button
            type="button"
            onClick={() => setChatAbierto((v) => !v)}
            className="border-t border-slate-700 px-3 py-2 text-xs text-slate-300
                       hover:bg-slate-700/50 flex items-center gap-2 shrink-0"
            aria-expanded={chatAbierto}
          >
            <MessageSquare size={13} aria-hidden />
            Asistente
            <span className="ml-auto text-slate-500">{chatAbierto ? '▾' : '▸'}</span>
          </button>

          {chatAbierto && paciente && (
            <div className="h-[300px] border-t border-slate-700 shrink-0">
              <ChatPanel pacienteId={paciente.id} />
            </div>
          )}
        </aside>

        <main className="flex-1 flex flex-col min-w-0">
          <header className="bg-white border-b border-slate-200 px-6 pt-3 shrink-0">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h1 className="font-semibold text-slate-800 text-lg truncate">
                  {paciente?.nombre ?? 'Sin paciente seleccionado'}
                </h1>
                <p className="text-xs text-slate-500 flex flex-wrap gap-x-3">
                  {paciente && (
                    <>
                      <span className="font-mono">{paciente.id}</span>
                      {paciente.edad != null && <span>{paciente.edad} años</span>}
                      {paciente.sexo && <span>{paciente.sexo}</span>}
                      {paciente.antecedentes && (
                        <span className="italic truncate max-w-lg">
                          {paciente.antecedentes}
                        </span>
                      )}
                    </>
                  )}
                </p>
              </div>

              {tic && vista === 'consulta' && (
                <div className="flex items-center gap-3 text-xs shrink-0 pt-1">
                  <Contador n={validados} etiqueta="validados" color="text-emerald-600" />
                  <Contador n={alertas} etiqueta="en alerta" color="text-amber-600" />
                  <Contador n={descartados} etiqueta="descartados" color="text-rose-500" />
                </div>
              )}
            </div>

            <nav className="flex gap-1 mt-3" aria-label="Vistas del paciente">
              {PESTANAS.map(({ id, etiqueta, Icono }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setVista(id)}
                  aria-current={vista === id}
                  className={`px-3 py-1.5 text-sm rounded-t-md border-b-2 flex items-center gap-1.5
                    ${
                      vista === id
                        ? 'border-indigo-600 text-indigo-700 font-medium'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                    }`}
                >
                  <Icono size={14} aria-hidden />
                  {etiqueta}
                  {id === 'problemas' && problemas.length > 0 && (
                    <span className="text-[10px] bg-slate-200 text-slate-600 rounded-full px-1.5">
                      {problemas.length}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </header>

          <div className="flex-1 overflow-y-auto p-6 min-h-0">
            {!paciente ? (
              <p className="text-sm text-slate-500 text-center mt-12">
                Crea o selecciona un paciente para empezar.
              </p>
            ) : vista === 'consulta' ? (
              <div className="space-y-4">
                <TicComposer
                  pacienteId={paciente.id}
                  skills={skills}
                  onResultado={alTerminarTic}
                />

                {tic && (
                  <>
                    <div className="flex flex-wrap items-baseline gap-2 text-xs text-slate-500">
                      <span>
                        Protocolo: <code className="text-slate-700">{tic.skill_activa}</code>
                      </span>
                      {tic.tic_id ? (
                        <span className="font-mono">· tic {tic.tic_id}</span>
                      ) : (
                        <span className="text-amber-600">· no persistido</span>
                      )}
                    </div>

                    <section className="bg-white border border-slate-200 rounded-lg p-4">
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                        Narrativa y evidencia
                      </h3>
                      <EvidenceText
                        texto={tic.texto_original}
                        infones={tic.infones}
                        seleccionado={seleccionado}
                        onSeleccionar={setSeleccionado}
                      />
                      {tic.resumen && (
                        <p className="text-sm text-slate-600 italic mt-3 pt-3 border-t border-slate-100">
                          {tic.resumen}
                        </p>
                      )}
                    </section>

                    {tic.inferencia && <InferencePanel inferencia={tic.inferencia} />}

                    {tic.infones.length > 0 ? (
                      <section>
                        <h3 className="text-sm font-semibold text-slate-700 mb-2">
                          Infones extraídos ({tic.infones.length})
                        </h3>
                        {tic.infones.map((infon, i) => (
                          <InfonCard
                            key={`${infon.termino}-${i}`}
                            infon={infon}
                            resaltado={seleccionado === i}
                            onSeleccionar={() =>
                              setSeleccionado(seleccionado === i ? null : i)
                            }
                          />
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
            ) : vista === 'problemas' ? (
              <ProblemList problemas={problemas} />
            ) : vista === 'historia' ? (
              <HistoryTimeline historial={historial} />
            ) : (
              <ConceptGraph grafo={grafo} />
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
