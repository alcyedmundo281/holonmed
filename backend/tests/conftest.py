import os
import sys
from pathlib import Path

import pytest

# Permite ejecutar pytest sin instalar el paquete.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """Con `HOLONMED_EXIGIR_INDICE=1`, saltarse por falta de índice es un fallo.

    En una máquina sin `medsemiotics-db` el salto es lo correcto. En CI, que lo
    clona, significa que el clon se perdió o se desincronizó, y un `skip` deja
    la build en verde. Se reconoce por la razón del salto: toda razón que
    dependa del índice tiene que nombrar `medsemiotics-db`.
    """
    informe = yield
    if (
        os.environ.get("HOLONMED_EXIGIR_INDICE") == "1"
        and informe.skipped
        and isinstance(informe.longrepr, tuple)
        and "medsemiotics-db" in informe.longrepr[2]
    ):
        informe.outcome = "failed"
        informe.longrepr = (
            f"HOLONMED_EXIGIR_INDICE=1 y la prueba iba a saltarse. {informe.longrepr[2]}"
        )
    return informe
