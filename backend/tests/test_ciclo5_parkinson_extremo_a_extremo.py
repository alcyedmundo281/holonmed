"""El bucle completo: una arista del índice llega a un veredicto contado.

Hasta este ciclo había dos extremos construidos y nada en medio. El conversor
mandaba los signos de alarma a la prosa del cuerpo, que lee el modelo y no lee
`veredicto.py`, así que una bandera curada en el índice no llegaba a contarse.

Estas pruebas no usan fixtures escritas a mano: convierten desde el índice real
y evalúan el resultado. Si el índice no está disponible se saltan, porque una
prueba que finge tener la fuente no prueba nada.

TRES ESTADOS, NO DOS
--------------------
Una prueba de aceptación tiene precondiciones, y confundirlas con su objeto
produce el mismo defecto que este repositorio persigue: un fallo que no nombra
su causa. Aquí se separan:

  · no hay clon                       -> SALTA, diciendo qué ruta se miró
  · hay clon pero le falta lo que la  -> SALTA, diciendo QUÉ falta y cuántas
    prueba necesita                      condiciones tiene el clon
  · está todo y el bucle no cierra    -> FALLA

Sólo el tercero es un defecto del código. Los dos primeros son un clon
desactualizado, y decir «assert set() == {'Anemia', ...}» en ese caso manda a
buscar el fallo donde no está. El salto sólo vale si dice la verdad completa:
un `skip` genérico sería el defecto de la lista blanca del `tipo` otra vez.
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

# La misma convención que `test_convertir_condicion.py`: relativa al repo, no
# a la máquina de nadie. Una ruta absoluta del portátil del autor hace que
# estas pruebas se salten en CI y en cualquier otro sitio, y son justamente
# las que demuestran que el bucle se cierra. La razón del salto lleva la ruta
# dentro para que el salto diga la verdad.
sys.path.insert(0, str(RAIZ / "scripts"))
convertir_condicion = pytest.importorskip("convertir_condicion")

INDICE = convertir_condicion.INDICE_POR_DEFECTO

pytestmark = pytest.mark.skipif(
    not (INDICE / "condiciones").is_dir(),
    reason=f"no hay un clon de medsemiotics-db en {INDICE}",
)


def _condiciones_del_clon() -> list[str]:
    indice = convertir_condicion.cargar_indice(INDICE)
    return sorted(indice.condiciones)


def exige_condicion(identificador: str) -> None:
    """Precondición: el clon declara esta condición. Si no, salta y lo dice.

    No es un `skipif` sobre «la versión del índice» —el índice no publica una—
    sino sobre lo concreto que hace falta, que es lo que alguien puede ir a
    arreglar.
    """
    condiciones = _condiciones_del_clon()
    if identificador not in condiciones:
        pytest.skip(
            f"tu clon de medsemiotics-db no declara {identificador}: tiene "
            f"{len(condiciones)} condiciones, de {condiciones[0]} a "
            f"{condiciones[-1]}. Actualízalo antes de leer esto como un fallo."
        )


def exige_arista(identificador: str, concepto: str, clave: str) -> None:
    """Precondición: la arista declara la clave que la prueba va a comprobar.

    El caso real: `HM:6002` existe en clones antiguos pero sus signos de alarma
    figuran sin `sostiene`, así que el conversor no puede emitirlos como
    bandera — y la prueba fallaba acusando al conversor de algo que decidió el
    índice.
    """
    indice = convertir_condicion.cargar_indice(INDICE)
    condicion = indice.condiciones.get(identificador) or {}
    aristas = (condicion.get("signos") or []) + (
        condicion.get("signos_de_alarma") or []
    )
    for arista in aristas:
        if str(arista.get("concepto")) == concepto and arista.get(clave):
            return
    pytest.skip(
        f"en tu clon, la arista {concepto} de {identificador} no declara "
        f"«{clave}»: el conversor no puede emitirla, y eso lo decide el índice, "
        f"no este repositorio. Actualiza el clon."
    )


def convertir(identificador: str) -> Skill:
    """Convierte de verdad, invocando el script como lo haría una persona."""
    exige_condicion(identificador)
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
    exige_arista("HM:6002", "HM:0711", "sostiene")
    skill = convertir("HM:6002")

    banderas = [s for s in skill.signos if s.efecto == "bandera_roja"]
    assert {s.nombre for s in banderas} == {"Anemia", "Pérdida de peso"}

    veredicto = EvaluadorDeVeredicto().evaluar(skill, [infon("Anemia")])
    assert veredicto is not None
    assert "Anemia" in veredicto.banderas_rojas


def test_la_prosa_de_alarma_se_conserva():
    """Dos consumidores, no uno migrando al otro: el modelo también las lee."""
    skill = convertir("HM:6002")   # la prosa no depende de `sostiene`
    assert "## Signos de alarma" in skill.cuerpo
    assert "Anemia" in skill.cuerpo
