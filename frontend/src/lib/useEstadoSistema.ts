import { useEffect, useState } from 'react';
import { api } from './api';
import type { EstadoSistema } from './types';

const INTERVALO_MS = 10_000;
// Mayor que el plazo con que el backend consulta al servidor de modelos (5 s).
const PLAZO_MS = 8_000;

export type SaludDelSistema =
  | { fase: 'comprobando' }
  | { fase: 'sin_servidor' }
  | { fase: 'respondio'; estado: EstadoSistema };

/**
 * Consulta `/health` cada pocos segundos, sin recargar la página.
 *
 * Un fallo o una respuesta que no llega a tiempo borra lo anterior: un
 * «conectado» viejo es justo lo que no puede quedarse en pantalla. La
 * siguiente consulta se programa al terminar la actual, así no se solapan.
 */
export function useEstadoSistema(): SaludDelSistema {
  const [salud, setSalud] = useState<SaludDelSistema>({ fase: 'comprobando' });

  useEffect(() => {
    let vivo = true;
    let enCurso = false;
    let temporizador: number | undefined;

    async function comprobar() {
      if (enCurso) return;
      enCurso = true;
      window.clearTimeout(temporizador);
      let siguiente: SaludDelSistema;
      try {
        const estado = await api.estado(AbortSignal.timeout(PLAZO_MS));
        siguiente = { fase: 'respondio', estado };
      } catch {
        siguiente = { fase: 'sin_servidor' };
      }
      enCurso = false;
      if (!vivo) return;
      setSalud(siguiente);
      temporizador = window.setTimeout(comprobar, INTERVALO_MS);
    }

    // El navegador frena los temporizadores de una pestaña oculta: al volver
    // a ella se comprueba en el acto.
    function alVolver() {
      if (document.visibilityState === 'visible') void comprobar();
    }

    void comprobar();
    document.addEventListener('visibilitychange', alVolver);
    return () => {
      vivo = false;
      window.clearTimeout(temporizador);
      document.removeEventListener('visibilitychange', alVolver);
    };
  }, []);

  return salud;
}
