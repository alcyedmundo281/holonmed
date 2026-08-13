"""Tests de las órdenes propuestas desde el plan.

Lo que se protege aquí es una sola regla, la que sostiene todo lo demás:
**proponer no es autorizar.** El modelo lee el plan y sugiere; hasta que
una persona firma, no existe ninguna orden y por tanto no puede existir
ningún cargo.

Los tests están escritos de forma que romper esa regla los rompa: si
`proponer` empezara a escribir en la base, el primero fallaría.
"""

import json

import pytest

from holonmed.core.terminology import TerminologyIndex, VocabularyLoader
from holonmed.db import Database, GraphRepo
from holonmed.facturacion import OrdenRepo, ProponedorOrdenes

VOCABULARIO = {
    "conceptos": [
        {"codigo": "P:0", "termino": "Procedimiento"},
        {"codigo": "P:1", "termino": "Preparación de citostáticos", "padre": "P:0"},
        {"codigo": "P:4", "termino": "Amilasa sérica", "padre": "P:0"},
    ]
}

PLAN = (
    "Dieta absoluta. Analgesia con morfina 3 mg IV cada 4 horas. "
    "Control de amilasa sérica en 24 h. Ondansetrón si náusea."
)


class LLMFalso:
    """Devuelve la lista de órdenes que se le indique."""

    def __init__(self, ordenes):
        self.ordenes = ordenes
        self.prompts: list[str] = []

    async def generar_json(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return {"ordenes": self.ordenes}


class SkillsVacios:
    def listar(self):
        return []

    def cargar(self, nombre):
        return None


@pytest.fixture
def entorno(tmp_path):
    (tmp_path / "vocab.json").write_text(json.dumps(VOCABULARIO), encoding="utf-8")
    db = Database(tmp_path / "prueba.db")
    VocabularyLoader(db).cargar_semilla(tmp_path / "vocab.json")
    return db, TerminologyIndex(db, GraphRepo(db)), OrdenRepo(db)


def _proponedor(index, ordenes_llm):
    return ProponedorOrdenes(SkillsVacios(), LLMFalso(ordenes_llm), index)


# --- La regla central --------------------------------------------------


@pytest.mark.asyncio
async def test_proponer_no_crea_ninguna_orden(entorno):
    """El botón todavía no se ha pulsado: la base no debe haberse tocado."""
    _, index, repo = entorno
    proponedor = _proponedor(
        index, [{"termino": "Amilasa sérica", "texto_origen": "Control de amilasa"}]
    )

    propuestas = await proponedor.proponer(PLAN)

    assert len(propuestas) == 1
    assert repo.listar("p1") == []


@pytest.mark.asyncio
async def test_autorizar_convierte_la_propuesta_en_orden(entorno):
    """Y sólo entonces existe algo sobre lo que se pueda facturar."""
    _, index, repo = entorno
    proponedor = _proponedor(
        index,
        [
            {
                "termino": "Amilasa sérica",
                "texto_origen": "Control de amilasa sérica en 24 h",
            }
        ],
    )

    propuesta = (await proponedor.proponer(PLAN))[0]
    orden = propuesta.a_orden("p1", prescriptor="dr. x")
    orden.id = repo.crear(orden)

    guardadas = repo.listar("p1")
    assert len(guardadas) == 1
    assert guardadas[0].termino == "Amilasa sérica"
    assert guardadas[0].prescriptor == "dr. x"
    # La cita sobrevive a la firma: es lo que permite auditar la orden
    # contra la nota sin releerla entera.
    assert "amilasa" in guardadas[0].texto_origen.lower()


@pytest.mark.asyncio
async def test_lo_no_autorizado_simplemente_no_existe(entorno):
    """Descartar un borrador no requiere ninguna acción ni deja rastro de
    orden: es la diferencia entre un borrador y un acto médico."""
    _, index, repo = entorno
    proponedor = _proponedor(
        index,
        [
            {"termino": "Amilasa sérica", "texto_origen": "Control de amilasa"},
            {"termino": "Ondansetrón", "texto_origen": "Ondansetrón si náusea"},
        ],
    )

    propuestas = await proponedor.proponer(PLAN)
    firmada = propuestas[0]
    orden = firmada.a_orden("p1")
    orden.id = repo.crear(orden)

    guardadas = repo.listar("p1")
    assert [o.termino for o in guardadas] == ["Amilasa sérica"]


# --- Calidad del borrador ---------------------------------------------


@pytest.mark.asyncio
async def test_la_propuesta_reconocida_trae_su_codigo(entorno):
    """Sin código no encontraría después su tarifa, y el cargo se perdería
    aunque el procedimiento se hubiese hecho."""
    _, index, _ = entorno
    proponedor = _proponedor(index, [{"termino": "preparación de citostáticos"}])

    propuesta = (await proponedor.proponer(PLAN))[0]

    assert propuesta.reconocida
    assert propuesta.codigo == "P:1"
    assert propuesta.termino == "Preparación de citostáticos"


@pytest.mark.asyncio
async def test_una_orden_no_reconocida_se_marca_pero_no_se_descarta(entorno):
    """El vocabulario semilla no cubre la farmacopea entera. Ocultar lo que
    no reconoce haría desaparecer órdenes reales del plan."""
    _, index, _ = entorno
    proponedor = _proponedor(index, [{"termino": "Ondansetrón"}])

    propuesta = (await proponedor.proponer(PLAN))[0]

    assert not propuesta.reconocida
    assert propuesta.termino == "Ondansetrón"


@pytest.mark.asyncio
async def test_una_medicacion_incompleta_señala_lo_que_falta(entorno):
    """Un hueco visible se corrige antes de firmar; uno inventado se firma
    sin mirar y acaba administrándose."""
    _, index, _ = entorno
    proponedor = _proponedor(
        index, [{"termino": "Morfina", "dosis": "3 mg", "via": "IV"}]
    )

    propuesta = (await proponedor.proponer(PLAN))[0]

    assert propuesta.faltantes == ["frecuencia"]


@pytest.mark.asyncio
async def test_no_se_exige_dosis_a_lo_que_no_es_medicacion(entorno):
    """Pedir vía y frecuencia a una interconsulta sería ruido, y el ruido
    enseña a ignorar los avisos que sí importan."""
    _, index, _ = entorno
    proponedor = _proponedor(index, [{"termino": "Interconsulta a cirugía"}])

    propuesta = (await proponedor.proponer(PLAN))[0]

    assert propuesta.faltantes == []


@pytest.mark.asyncio
async def test_los_nulos_del_modelo_no_llegan_al_detalle(entorno):
    """Un modelo rellena los campos que no sabe con `null` o `N/A`; eso no
    es una dosis y no debe mostrarse como si lo fuera."""
    _, index, _ = entorno
    proponedor = _proponedor(
        index,
        [{"termino": "Morfina", "dosis": "3 mg", "via": "null", "frecuencia": "N/A"}],
    )

    propuesta = (await proponedor.proponer(PLAN))[0]

    assert propuesta.detalle == {"dosis": "3 mg"}
    assert set(propuesta.faltantes) == {"via", "frecuencia"}


@pytest.mark.asyncio
async def test_una_categoria_no_es_un_farmaco(entorno):
    """Observado con el modelo local: «Ondansetrón 8 mg» volvió como
    «Medicamento». Una categoría no se puede administrar, así que la
    propuesta se marca en vez de adivinar cuál era."""
    _, index, _ = entorno
    proponedor = _proponedor(index, [{"termino": "Medicamento", "dosis": "8 mg"}])

    propuesta = (await proponedor.proponer(PLAN))[0]

    assert propuesta.generico
    # Y no se corrige sola: adivinar el fármaco es justo lo que no debe hacer.
    assert propuesta.termino == "Medicamento"


@pytest.mark.asyncio
async def test_un_farmaco_concreto_no_se_marca(entorno):
    _, index, _ = entorno
    proponedor = _proponedor(index, [{"termino": "Ondansetrón", "dosis": "8 mg"}])

    assert not (await proponedor.proponer(PLAN))[0].generico


@pytest.mark.asyncio
async def test_sin_llm_no_hay_propuestas_pero_tampoco_error(entorno):
    """El plan se escribe igual sin el modelo. El botón sugiere; no es un
    requisito para prescribir."""
    from holonmed.llm import LLMUnavailable

    class LLMCaido:
        async def generar_json(self, prompt, **kwargs):
            raise LLMUnavailable("apagado")

    _, index, _ = entorno
    proponedor = ProponedorOrdenes(SkillsVacios(), LLMCaido(), index)

    assert await proponedor.proponer(PLAN) == []
