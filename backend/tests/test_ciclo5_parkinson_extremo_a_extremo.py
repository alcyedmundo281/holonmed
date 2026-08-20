"""El bucle completo: una arista del índice llega a un veredicto contado.

Hasta este ciclo había dos extremos construidos y nada en medio. El conversor
mandaba los signos de alarma a la prosa del cuerpo, que lee el modelo y no lee
`veredicto.py`, así que una bandera curada en el índice no llegaba a contarse.

Estas pruebas no usan fixtures escritas a mano: convierten desde el índice real
y evalúan el resultado. Si el índice no está disponible se saltan, porque una
prueba que finge tener la fuente no prueba nada.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from holonmed.core.skills import Skill
from holonmed.core.veredicto import EvaluadorDeVeredicto
from holonmed.models import EstadoInfon, Infon, Polaridad

RAIZ = Path(__file__).resolve().parents[1]
CONVERSOR = RAIZ / "scripts" / "convertir_condicion.py"
INDICE = Path("C:/Users/alcye/OneDrive - Outlook/OneDrive/Documents/medsemiotics-db")

pytestmark = pytest.mark.skipif(
    not (INDICE / "condiciones").is_dir(),
    reason="hace falta un clon de medsemiotics-db",
)


def convertir(identificador: str) -> Skill:
    """Convierte de verdad, invocando el script como lo haría una persona."""
    r = subprocess.run(
        [sys.executable, str(CONVERSOR), identificador, "--indice", str(INDICE)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(RAIZ),
    )
    assert r.returncode == 0, r.stderr
    return Skill(identificador, r.stdout)


def infon(termino: str, polaridad: Polaridad = Polaridad.PRESENTE) -> Infon:
    """Un hallazgo VALIDADO. El estado por defecto es RUIDO a propósito: sólo la
    evidencia que pasó la auditoría satisface un criterio o veta un
    diagnóstico, y una fixture que lo olvidara probaría otra cosa."""
    return Infon(
        texto_origen=termino, termino_propuesto=termino,
        termino=termino, polaridad=polaridad,
        estado=EstadoInfon.VALIDADO,
    )


# ── el caso de aceptación ────────────────────────────────────────────────────

def test_parkinson_alcanza_establecida_desde_el_indice():
    """Bradicinesia y rigidez documentadas, dos apoyos, ninguna bandera."""
    skill = convertir("HM:6015")

    assert skill.nucleo.declarado, "el núcleo no llegó a la skill"
    assert skill.balance.declarado, "el balance no llegó a la skill"

    veredicto = EvaluadorDeVeredicto().evaluar(
        skill, [infon("Bradicinesia"), infon("Rigidez parkinsoniana")]
    )

    assert veredicto is not None
    assert veredicto.nivel == "establecida", veredicto.traza
    assert len(veredicto.apoyos) == 2
    assert veredicto.banderas_rojas == []
    # La cita viaja con el veredicto: es lo que permite discrepar de un paso.
    assert "Postuma" in veredicto.fuente


def test_parkinson_sin_nucleo_no_alcanza_ningun_nivel():
    """Sin bradicinesia el criterio no se aplica, por muchos apoyos que haya."""
    skill = convertir("HM:6015")
    veredicto = EvaluadorDeVeredicto().evaluar(
        skill, [infon("Rigidez parkinsoniana"), infon("Temblor de reposo")]
    )
    assert veredicto is not None
    assert veredicto.nivel != "establecida"
    assert any("úcleo" in t for t in veredicto.traza), veredicto.traza


# ── el ruteo de las banderas ─────────────────────────────────────────────────

def test_la_bandera_del_indice_llega_al_bloque_estructurado_y_se_cuenta():
    """Las dos mitades: emitida y contada. La primera sola no prueba nada."""
    skill = convertir("HM:6002")

    banderas = [s for s in skill.signos if s.efecto == "bandera_roja"]
    assert {s.nombre for s in banderas} == {"Anemia", "Pérdida de peso"}

    veredicto = EvaluadorDeVeredicto().evaluar(skill, [infon("Anemia")])
    assert veredicto is not None
    assert "Anemia" in veredicto.banderas_rojas


def test_la_prosa_de_alarma_se_conserva():
    """Dos consumidores, no uno migrando al otro: el modelo también las lee."""
    skill = convertir("HM:6002")
    assert "## Signos de alarma" in skill.cuerpo
    assert "Anemia" in skill.cuerpo
