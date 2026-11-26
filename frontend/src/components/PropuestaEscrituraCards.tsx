import { api } from '../lib/api';
import type { PropuestaCita, PropuestaPaciente, PropuestaTic } from '../lib/types';
import { ConfirmarConNombre } from './ConfirmarConNombre';

const MARCO = 'mt-2 pt-2 border-t border-slate-300/40 text-xs space-y-1.5';

function Dato({ nombre, children }: { nombre: string; children: string }) {
  return (
    <p className="break-words">
      <span className="font-medium">{nombre}:</span> {children}
    </p>
  );
}

function Registrado({ texto, por }: { texto: string; por: string }) {
  return (
    <p className="text-[11px] text-amber-700">
      {texto} Confirmó: {por}.
    </p>
  );
}

export function PropuestaCitaCard({ propuesta }: { propuesta: PropuestaCita }) {
  const cuando = new Date(propuesta.fecha).toLocaleString('es', {
    dateStyle: 'full',
    timeStyle: 'short',
  });
  return (
    <div className={MARCO}>
      <Dato nombre="Paciente">{propuesta.paciente_nombre}</Dato>
      <Dato nombre="Petición">{propuesta.texto_original}</Dato>
      <Dato nombre="Fecha escrita">{propuesta.fecha_texto}</Dato>
      <Dato nombre="Se agendará">{cuando}</Dato>
      <Dato nombre="Motivo">{propuesta.motivo}</Dato>
      <ConfirmarConNombre
        confirmar={(nombre) =>
          api.confirmarCita(propuesta.propuesta_id, propuesta.paciente_id, nombre)
        }
        registrado={(r) => <Registrado texto="Cita agendada." por={r.confirmado_por} />}
      />
    </div>
  );
}

export function PropuestaPacienteCard({ propuesta }: { propuesta: PropuestaPaciente }) {
  return (
    <div className={MARCO}>
      <Dato nombre="Petición">{propuesta.texto_original}</Dato>
      <Dato nombre="Nombre">{propuesta.nombre}</Dato>
      <p>Se dará de alta sólo con el nombre, sin ningún otro dato.</p>
      <ConfirmarConNombre
        confirmar={(nombre) => api.confirmarAlta(propuesta.propuesta_id, nombre)}
        registrado={(r) => (
          <Registrado texto={`Alta registrada (${r.id}).`} por={r.confirmado_por} />
        )}
      />
    </div>
  );
}

export function PropuestaTicCard({ propuesta }: { propuesta: PropuestaTic }) {
  const { tic } = propuesta;
  return (
    <div className={MARCO}>
      <Dato nombre="Paciente">{propuesta.paciente_nombre}</Dato>
      <Dato nombre="Narrativa">{tic.texto_original}</Dato>
      <Dato nombre="Protocolo">{tic.skill_activa}</Dato>
      {tic.resumen && <Dato nombre="Resumen del modelo, sin validar">{tic.resumen}</Dato>}
      {tic.infones.length === 0 ? (
        <p>No se extrajo ningún hallazgo.</p>
      ) : (
        <ul className="list-disc pl-4">
          {tic.infones.map((infon, i) => (
            <li key={i} className="break-words">
              <span className="font-medium">{infon.termino}</span> ({infon.polaridad},{' '}
              {infon.estado})
            </li>
          ))}
        </ul>
      )}
      {tic.evolucion && (
        <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words font-sans">
          {tic.evolucion.texto}
        </pre>
      )}
      {tic.veredicto_declarado?.veto && (
        <Dato nombre="Hipótesis retirada">{tic.veredicto_declarado.veto.motivo}</Dato>
      )}
      {tic.inferencia && !tic.veredicto_declarado?.veto && (
        <Dato nombre="Inferencia">
          {`${tic.inferencia.diagnostico}: ${tic.inferencia.probabilidad_porcentaje} %`}
        </Dato>
      )}
      <details>
        <summary className="cursor-pointer">Todo lo que se guardará</summary>
        <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words text-[10px]">
          {JSON.stringify(tic, null, 2)}
        </pre>
      </details>
      <p>Confirmar guarda el procesamiento; no ratifica los hallazgos.</p>
      <ConfirmarConNombre
        confirmar={(nombre) =>
          api.confirmarTic(propuesta.propuesta_id, propuesta.paciente_id, nombre)
        }
        registrado={(r) => (
          <Registrado texto={`Guardado como tic ${r.tic_id}.`} por={r.confirmado_por} />
        )}
      />
    </div>
  );
}
