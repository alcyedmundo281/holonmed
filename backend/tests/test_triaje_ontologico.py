"""Pruebas del triaje clínico determinista basado en criterios ontológicos de consenso.

Verifica que el triaje:
1. Consulta medsemiotics-db y las skills para cargar criterios diagnósticos de consenso.
2. Agrupa deterministamente la lista de problemas del paciente sin depender de LLM ("inteligencia").
3. Asocia la procedencia y el PMID correspondiente a cada agrupación y criterio.
4. Distingue criterios cumplidos, parciales y sospechas iniciales.
"""

from pathlib import Path
from typing import Any

import pytest

from holonmed.core.pipeline import CrystallizationPipeline
from holonmed.core.skills import SkillManager
from holonmed.core.triaje import TriajeOntologico
from holonmed.core.validator import OntologyValidator
from holonmed.core.verifier import ClinicalVerifier
from holonmed.models import (
    EstadoInfon,
    HolonPaciente,
    Infon,
    Polaridad,
    ResultadoTic,
)


@pytest.fixture
def skills_manager(tmp_path: Path) -> SkillManager:
    return SkillManager()


@pytest.fixture
def triaje(skills_manager: SkillManager) -> TriajeOntologico:
    return TriajeOntologico(skills_manager=skills_manager)


def test_carga_construcciones_con_pmid(triaje: TriajeOntologico) -> None:
    """Verifica que las construcciones ontológicas se cargan con sus PMID."""
    construcciones = triaje.cargar_construcciones()
    assert len(construcciones) > 0

    # Pancreatitis debe tener PMID 23100216 (Atlanta 2012)
    pancreatitis = next(
        (c for c in construcciones if "pancreatitis" in c.termino.lower()), None
    )
    assert pancreatitis is not None
    assert pancreatitis.pmid == "23100216"
    assert "Atlanta" in pancreatitis.consenso_nombre

    # Parkinson debe tener PMID 26474316 (MDS 2015)
    parkinson = next(
        (c for c in construcciones if "parkinson" in c.termino.lower()), None
    )
    assert parkinson is not None
    assert parkinson.pmid == "26474316"
    assert len(parkinson.items) > 0


def test_agrupar_pancreatitis_criterios_atlanta(triaje: TriajeOntologico) -> None:
    """Pancreatitis aguda: 2 de 3 criterios de Atlanta cumplidos deterministamente."""
    problemas = [
        Infon(
            texto_origen="dolor epigástrico en cinturón",
            termino_propuesto="dolor epigástrico",
            termino="Dolor epigástrico",
            codigo="HM:0202",
            polaridad=Polaridad.PRESENTE,
            estado=EstadoInfon.VALIDADO,
        ),
        Infon(
            texto_origen="lipasa 890",
            termino_propuesto="hiperlipasemia",
            termino="Hiperlipasemia (>3x)",
            codigo="HM:0732",
            polaridad=Polaridad.PRESENTE,
            estado=EstadoInfon.VALIDADO,
        ),
        Infon(
            texto_origen="vómitos de repetición",
            termino_propuesto="vómitos",
            termino="Vómitos",
            codigo="HM:0302",
            polaridad=Polaridad.PRESENTE,
            estado=EstadoInfon.VALIDADO,
        ),
    ]

    agrupaciones = triaje.agrupar_problemas(problemas)
    assert len(agrupaciones) > 0

    primera = agrupaciones[0]
    assert "pancreatitis" in primera.condicion_nombre.lower()
    assert primera.pmid == "23100216"
    assert "Atlanta" in primera.consenso_nombre
    assert primera.cumplido is True
    assert primera.estado == "CUMPLIDO"

    # Problemas agrupados bajo la construcción
    terminos_agrupados = [p.termino for p in primera.problemas_agrupados]
    assert "Dolor epigástrico" in terminos_agrupados
    assert "Hiperlipasemia (>3x)" in terminos_agrupados

    # Verifica que el criterio de imagen queda como pendiente
    assert any("imagen" in p.lower() for p in primera.criterios_pendientes)


def test_agrupar_parkinson_criterios_mds_nucleo(triaje: TriajeOntologico) -> None:
    """Parkinson: núcleo motor de MDS 2015 (bradicinesia + temblor de reposo)."""
    problemas = [
        {"termino": "Bradicinesia", "codigo": "HM:3061", "polaridad": "presente"},
        {"termino": "Temblor de reposo", "codigo": "HM:3062", "polaridad": "presente"},
    ]

    agrupaciones = triaje.agrupar_problemas(problemas)
    parkinson = next(
        (a for a in agrupaciones if "parkinson" in a.condicion_nombre.lower()), None
    )
    assert parkinson is not None
    assert parkinson.pmid == "26474316"
    assert parkinson.cumplido is True
    assert parkinson.estado == "CUMPLIDO"

    terminos_agrupados = [p.termino for p in parkinson.problemas_agrupados]
    assert "Bradicinesia" in terminos_agrupados
    assert "Temblor de reposo" in terminos_agrupados


def test_agrupar_faringitis_centor_con_pmid(triaje: TriajeOntologico) -> None:
    """Faringitis estreptocócica: criterios Centor/McIsaac con PMID 11147989/6763125."""
    problemas = [
        {"termino": "Odinofagia", "codigo": "HM:0211"},
        {"termino": "Exudado amigdalino", "codigo": "HM:3026"},
        {"termino": "Adenopatía cervical anterior dolorosa", "codigo": "HM:3029"},
    ]

    agrupaciones = triaje.agrupar_problemas(problemas)
    faringitis = next(
        (a for a in agrupaciones if "faringitis" in a.condicion_nombre.lower()), None
    )
    assert faringitis is not None
    assert faringitis.pmid in ("11147989", "6763125", "9475915")
    assert len(faringitis.problemas_agrupados) >= 2


def test_agrupar_sindrome_coronario_agudo(triaje: TriajeOntologico) -> None:
    """SCA: dolor torácico + descenso ST con PMID 26547467 (Fanaroff 2015)."""
    problemas = [
        {"termino": "Dolor torácico", "codigo": "HM:0206"},
        {"termino": "Descenso del segmento ST", "codigo": "HM:3015"},
    ]

    agrupaciones = triaje.agrupar_problemas(problemas)
    sca = next(
        (a for a in agrupaciones if "coronario" in a.condicion_nombre.lower()), None
    )
    assert sca is not None
    assert sca.pmid == "26547467"

    # Descenso ST debe estar catalogado como prueba_especifica
    st_prob = next(
        (p for p in sca.problemas_agrupados if "st" in p.termino.lower()), None
    )
    assert st_prob is not None
    assert st_prob.rol == "prueba_especifica"
    assert st_prob.lr_positivo == 5.3


@pytest.mark.asyncio
async def test_triaje_skill_manager_determinista_sin_llm(
    skills_manager: SkillManager,
) -> None:
    """SkillManager.triaje selecciona el protocolo sin llamar a ningún LLM."""
    problemas = [
        {"termino": "Dolor epigástrico", "codigo": "HM:0202"},
        {"termino": "Hiperlipasemia (>3x)", "codigo": "HM:0732"},
    ]

    protocolo = await skills_manager.triaje(
        texto_clinico="dolor epigástrico y lipasa muy alta",
        llm=None,  # No hay LLM disponible
        problemas=problemas,
    )
    assert protocolo == "acute_pancreatitis"


@pytest.mark.asyncio
async def test_triaje_texto_determinista_sin_llm(
    skills_manager: SkillManager,
) -> None:
    """SkillManager.triaje identifica el protocolo desde texto usando los criterios ontológicos."""
    texto = "Varón de 45 años con dolor epigástrico en cinturón e hiperlipasemia >3x"
    protocolo = await skills_manager.triaje(
        texto_clinico=texto,
        llm=None,
    )
    assert protocolo == "acute_pancreatitis"


class IndexEco:
    def __init__(self, codigo: str = "HM:0202"):
        self.codigo = codigo

    def disponible(self) -> bool:
        return True

    def buscar_exacto(self, texto: str) -> Any:
        from holonmed.core.terminology import Candidato

        return Candidato(1, self.codigo, "holonmed", texto, 100.0)

    def buscar_candidatos(self, texto: str, limite: int = 15) -> list[Any]:
        from holonmed.core.terminology import Candidato

        return [Candidato(1, self.codigo, "holonmed", texto, 95.0)]

    def metadatos(self, concepto_id: int) -> tuple[str, str]:
        return "R50.9", "Signo clínico"

    def cobertura_de_grafo(self, concepto_ids: Any) -> set[str]:
        return {"HM:0201", "HM:0730", "HM:0202"}


@pytest.mark.asyncio
async def test_pipeline_etapa1_registra_agrupaciones(tmp_path: Path) -> None:
    """El pipeline registra agrupaciones_triage con criterios de consenso y PMID."""
    index = IndexEco()

    class LLMStub:
        backend = "stub"

        async def consultar(self, prompt: str, **kwargs: Any) -> str:
            return '{"resumen": "Dolor y enzimas", "infones": [{"texto_origen": "dolor epigastrico", "termino_clinico": "Dolor epigástrico", "presente": true}]}'

        async def generar_json(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
            if "ROL: ANALISTA CLÍNICO" in prompt:
                return {
                    "resumen": "Dolor y enzimas",
                    "infones": [
                        {
                            "texto_origen": "dolor epigástrico",
                            "termino_clinico": "Dolor epigástrico",
                            "presente": True,
                        }
                    ],
                }
            return {
                "es_valido": True,
                "razon": "confirmado por texto",
                "confianza": 95,
                "ausencia_confirmada": False,
            }

    llm = LLMStub()
    skills = SkillManager()
    validador = OntologyValidator(index, llm)  # type: ignore[arg-type]
    verificador = ClinicalVerifier(llm)  # type: ignore[arg-type]
    pipeline = CrystallizationPipeline(
        llm=llm,  # type: ignore[arg-type]
        skills=skills,
        validador=validador,
        verificador=verificador,
    )

    holon = HolonPaciente(
        paciente_id="test-p1",
        linea_tiempo=[
            Infon(
                texto_origen="dolor epigástrico en cinturón",
                termino_propuesto="dolor epigástrico",
                termino="Dolor epigástrico",
                codigo="HM:0202",
                polaridad=Polaridad.PRESENTE,
                estado=EstadoInfon.VALIDADO,
            ),
            Infon(
                texto_origen="lipasa elevada",
                termino_propuesto="hiperlipasemia",
                termino="Hiperlipasemia (>3x)",
                codigo="HM:0732",
                polaridad=Polaridad.PRESENTE,
                estado=EstadoInfon.VALIDADO,
            ),
        ],
    )

    resultado = await pipeline.ejecutar(
        texto="dolor epigástrico y lipasa >3x",
        holon=holon,
    )

    assert resultado.skill_activa == "acute_pancreatitis"
    assert len(resultado.agrupaciones_triage) > 0
    primera = resultado.agrupaciones_triage[0]
    assert primera.pmid == "23100216"
    assert primera.cumplido is True


def test_api_triage_endpoints(tmp_path: Path) -> None:
    """Verifica los endpoints /api/pacientes/{id}/triage y /api/triage/agrupar."""
    from fastapi.testclient import TestClient

    from holonmed.api.app import crear_app
    from holonmed.api.deps import AppContext, get_context
    from holonmed.config import Settings

    ajustes = Settings(db_path=tmp_path / "test_api.db", autocargar_semilla=False)
    contexto = AppContext(ajustes)

    # Registrar paciente e infón validado para p1
    tic_res = Infon(
        texto_origen="dolor epigástrico intenso",
        termino_propuesto="dolor epigástrico",
        termino="Dolor epigástrico",
        codigo="HM:0202",
        polaridad=Polaridad.PRESENTE,
        estado=EstadoInfon.VALIDADO,
    )
    resultado_tic = ResultadoTic(
        paciente_id="p1",
        texto_original="dolor epigástrico intenso",
        skill_activa="general_triage",
        infones=[tic_res],
    )
    contexto.tics.guardar(resultado_tic)

    app = crear_app(ajustes)
    app.dependency_overrides[get_context] = lambda: contexto

    with TestClient(app) as cliente:
        # GET /api/pacientes/p1/triage
        res_get = cliente.get("/api/pacientes/p1/triage")
        assert res_get.status_code == 200
        datos_get = res_get.json()
        assert len(datos_get) > 0
        assert any("pancreatitis" in d["condicion_nombre"].lower() for d in datos_get)

        # POST /api/triage/agrupar
        res_post = cliente.post(
            "/api/triage/agrupar",
            json=[
                {"termino": "Bradicinesia", "codigo": "HM:3061"},
                {"termino": "Temblor de reposo", "codigo": "HM:3062"},
            ],
        )
        assert res_post.status_code == 200
        datos_post = res_post.json()
        assert len(datos_post) > 0
        primero_post = datos_post[0]
        assert "parkinson" in primero_post["condicion_nombre"].lower()
        assert primero_post["pmid"] == "26474316"
        assert primero_post["cumplido"] is True

    contexto.database.cerrar()
