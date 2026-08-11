"""Tests del parseo de skills y la extracción de skill-hints."""

from holonmed.core.skills import Skill, SkillManager

SKILL_DEMO = """# SKILL: PRUEBA

BASE DE CONOCIMIENTO:

{
    "@context": "https://schema.org",
    "@type": "MedicalCondition",
    "name": "Condición de prueba",
    "snomed_id": "111111",
    "modelo_bayesiano": {
        "probabilidad_base": 0.05,
        "factores_riesgo_a_priori": {"tabaquismo": 2.0}
    },
    "criterios_laboratorio": {
        "reglas": [
            {
                "parametro": "Calcio",
                "corte_inferior": 8.5,
                "termino_si_bajo": "Hipocalcemia",
                "snomed_id": "5291005"
            }
        ]
    },
    "signDetected": [
        {"name": "Dolor epigástrico", "snomed_id": "79922009", "bayes_lr": 2.1},
        {"name": "Vómitos", "code": {"codeValue": "422400008"}, "bayes_lr": 1.6}
    ]
}

INSTRUCCIONES: extrae hallazgos.
"""


def test_la_descripcion_sale_de_la_primera_linea():
    assert Skill("prueba", SKILL_DEMO).descripcion == "SKILL: PRUEBA"


def test_se_parsea_el_bloque_json_embebido():
    skill = Skill("prueba", SKILL_DEMO)
    assert skill.json_principal["name"] == "Condición de prueba"
    assert skill.json_principal["modelo_bayesiano"]["probabilidad_base"] == 0.05


def test_los_hints_salen_de_signos_y_de_laboratorio():
    hints = Skill("prueba", SKILL_DEMO).hints_snomed()
    assert hints["dolor epigástrico"] == "79922009"
    assert hints["vómitos"] == "422400008"  # forma anidada code.codeValue
    assert hints["hipocalcemia"] == "5291005"  # derivado de criterios_laboratorio


def test_las_claves_de_los_hints_se_normalizan_a_minusculas():
    assert all(k == k.lower() for k in Skill("p", SKILL_DEMO).hints_snomed())


def test_el_vocabulario_preferido_no_tiene_duplicados():
    vocabulario = Skill("prueba", SKILL_DEMO).vocabulario_preferido()
    assert len(vocabulario) == len(set(vocabulario))
    assert "Dolor epigástrico" in vocabulario


def test_un_skill_sin_json_no_revienta():
    skill = Skill("plano", "# Sólo texto\nSin JSON aquí.")
    assert skill.hints_snomed() == {}
    assert skill.json_principal == {}


def test_se_tolera_la_basura_de_copiar_y_pegar():
    """Espacios no separables y escapes de Markdown no deben romper el parseo."""
    sucio = SKILL_DEMO.replace(" ", "\xa0", 5).replace('"name"', '\\"name\\"', 1)
    assert Skill("sucio", sucio).hints_snomed()


def test_los_skills_del_repositorio_son_validos(tmp_path):
    """Los protocolos que se distribuyen deben parsear sin errores."""
    from pathlib import Path

    directorio = Path(__file__).resolve().parents[1] / "skills"
    archivos = list(directorio.glob("*.md"))
    assert archivos, "No hay skills en el repositorio"

    for ruta in archivos:
        skill = Skill(ruta.stem, ruta.read_text(encoding="utf-8"))
        assert skill.descripcion
        if ruta.stem != "receta":  # la receta no declara terminología
            assert skill.hints_snomed(), f"{ruta.name} no aporta hints SNOMED"


class TestCargaSegura:
    def _gestor(self, tmp_path):
        from holonmed.config import Settings

        (tmp_path / "valida.md").write_text(SKILL_DEMO, encoding="utf-8")
        return SkillManager(Settings(skills_dir=tmp_path))

    def test_carga_una_skill_existente(self, tmp_path):
        assert self._gestor(tmp_path).cargar("valida") is not None

    def test_acepta_el_nombre_con_extension(self, tmp_path):
        assert self._gestor(tmp_path).cargar("valida.md") is not None

    def test_rechaza_el_recorrido_de_directorios(self, tmp_path):
        """El nombre puede venir de un LLM: no debe poder escapar del directorio."""
        gestor = self._gestor(tmp_path)
        for malicioso in ("../../../etc/passwd", "..\\..\\windows\\win.ini", "/etc/hosts"):
            assert gestor.cargar(malicioso) is None

    def test_siempre_hay_una_skill_por_defecto(self, tmp_path):
        assert self._gestor(tmp_path).cargar_o_defecto("inexistente") is not None
