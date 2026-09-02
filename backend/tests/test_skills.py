"""Tests del parseo de protocolos y la extracción de skill-hints."""

from pathlib import Path

import pytest

from holonmed.core.skills import Skill, SkillManager

SKILL_YAML = """---
titulo: Condición de prueba
descripcion: Protocolo sintético para los tests
version: "1.0.0"

condicion:
  nombre: Condición de prueba
  codigos: { snomed: "111111" }

ambito_grafo: [HM:0730]

modelo_bayesiano:
  probabilidad_base: 0.05
  factores_riesgo:
    tabaquismo: 2.0

signos:
  - nombre: Dolor epigástrico
    codigos: { holonmed: "HM:0202", snomed: "79922009" }
    lr: 2.1
    fuente: Estudio de prueba
  - nombre: Vómitos
    codigos: { snomed: "422400008" }
    lr: 1.6
    fuente: Estudio de prueba

laboratorio:
  - parametro: Calcio
    corte_inferior: 8.5
    termino_si_bajo: Hipocalcemia
    codigos: { holonmed: "HM:0721", snomed: "5291005" }
---

# PROTOCOLO DE PRUEBA

INSTRUCCIONES: extrae hallazgos.
"""

# Formato anterior al frontmatter, que debe seguir funcionando.
SKILL_ANTIGUO = """# SKILL: PRUEBA ANTIGUA

{
    "name": "Condición antigua",
    "snomed_id": "111111",
    "modelo_bayesiano": {
        "probabilidad_base": 0.05,
        "factores_riesgo_a_priori": {"tabaquismo": 2.0}
    },
    "criterios_laboratorio": {
        "reglas": [
            {"parametro": "Calcio", "corte_inferior": 8.5,
             "termino_si_bajo": "Hipocalcemia", "snomed_id": "5291005"}
        ]
    },
    "signDetected": [
        {"name": "Dolor epigástrico", "snomed_id": "79922009", "bayes_lr": 2.1},
        {"name": "Vómitos", "code": {"codeValue": "422400008"}, "bayes_lr": 1.6}
    ]
}

INSTRUCCIONES: extrae hallazgos.
"""


# --- Frontmatter ------------------------------------------------------


def test_la_descripcion_sale_del_frontmatter():
    assert Skill("p", SKILL_YAML).descripcion == "Protocolo sintético para los tests"


def test_el_frontmatter_no_entra_en_el_prompt():
    """El modelo recibe la prosa; el YAML es para el código.

    Colarlo en el prompt gastaría contexto en sintaxis que el modelo no
    tiene que interpretar, y le daría los códigos que precisamente debe
    deducir el validador.
    """
    contenido = Skill("p", SKILL_YAML).contenido
    assert "PROTOCOLO DE PRUEBA" in contenido
    assert "ambito_grafo" not in contenido
    assert "modelo_bayesiano" not in contenido


def test_se_parsean_signos_y_laboratorio():
    skill = Skill("p", SKILL_YAML)
    assert len(skill.signos) == 2
    assert len(skill.laboratorio) == 1
    assert skill.signos[0].lr == 2.1
    assert skill.laboratorio[0].corte_inferior == 8.5


def test_el_ambito_de_grafo_queda_disponible():
    assert Skill("p", SKILL_YAML).ambito_grafo == ["HM:0730"]


def test_los_hints_salen_de_signos_y_de_laboratorio():
    hints = Skill("p", SKILL_YAML).hints()
    assert hints["dolor epigástrico"] == "HM:0202"  # prioriza holonmed
    assert hints["vómitos"] == "422400008"  # sólo hay snomed
    assert hints["hipocalcemia"] == "HM:0721"  # derivado del laboratorio


def test_las_claves_de_los_hints_se_normalizan_a_minusculas():
    assert all(k == k.lower() for k in Skill("p", SKILL_YAML).hints())


def test_el_vocabulario_preferido_no_tiene_duplicados():
    vocabulario = Skill("p", SKILL_YAML).vocabulario_preferido()
    assert len(vocabulario) == len(set(vocabulario))
    assert "Dolor epigástrico" in vocabulario


def test_la_estructura_para_bayes_conserva_los_lr():
    bayes = Skill("p", SKILL_YAML).para_bayes()
    assert bayes["modelo_bayesiano"]["probabilidad_base"] == 0.05
    assert {s["name"]: s["bayes_lr"] for s in bayes["signDetected"]} == {
        "Dolor epigástrico": 2.1,
        "Vómitos": 1.6,
    }


def test_un_frontmatter_roto_no_revienta(caplog):
    """Debe fallar de forma ruidosa, no silenciosa: un protocolo sin
    códigos ni cortes seguiría cargándose y usándose."""
    roto = "---\ntitulo: [sin cerrar\n---\n\n# Cuerpo\n"
    skill = Skill("roto", roto)
    assert skill.hints() == {}
    assert "Cuerpo" in skill.contenido
    assert any("Frontmatter inválido" in r.message for r in caplog.records)


# --- Compatibilidad con el formato antiguo ----------------------------


def test_el_formato_antiguo_sigue_funcionando():
    skill = Skill("antiguo", SKILL_ANTIGUO)
    hints = skill.hints()
    assert hints["dolor epigástrico"] == "79922009"
    assert hints["vómitos"] == "422400008"  # forma anidada code.codeValue
    assert hints["hipocalcemia"] == "5291005"
    assert skill.para_bayes()["modelo_bayesiano"]["probabilidad_base"] == 0.05


def test_se_tolera_la_basura_de_copiar_y_pegar():
    """Espacios no separables y escapes de Markdown en el formato antiguo."""
    sucio = SKILL_ANTIGUO.replace(" ", "\xa0", 5).replace('"name"', '\\"name\\"', 1)
    assert Skill("sucio", sucio).hints()


def test_un_skill_sin_estructura_no_revienta():
    skill = Skill("plano", "# Sólo texto\nSin nada estructurado.")
    assert skill.hints() == {}
    assert skill.signos == []
    assert not skill.bayes.declarado


# --- Los protocolos del repositorio -----------------------------------


DIRECTORIO_SKILLS = Path(__file__).resolve().parents[1] / "skills"


def _skills_del_repo():
    return sorted(DIRECTORIO_SKILLS.glob("*.md"))


def test_hay_protocolos_en_el_repositorio():
    assert _skills_del_repo()


@pytest.mark.parametrize("ruta", _skills_del_repo(), ids=lambda p: p.stem)
def test_los_protocolos_del_repositorio_son_validos(ruta):
    """Cada protocolo distribuido debe parsear y pasar su propia revisión.

    Sin índice terminológico, así que no comprueba que los códigos
    existan; para eso está `holonmed skills --validar`, que necesita el
    vocabulario cargado.
    """
    skill = Skill(ruta.stem, ruta.read_text(encoding="utf-8"))
    assert skill.descripcion
    assert skill.problemas() == []


@pytest.mark.parametrize("ruta", _skills_del_repo(), ids=lambda p: p.stem)
def test_los_protocolos_clinicos_aportan_hints(ruta):
    skill = Skill(ruta.stem, ruta.read_text(encoding="utf-8"))
    if skill.tipo in ("operativo", "documento"):
        pytest.skip(f"un protocolo '{skill.tipo}' no extrae hallazgos")
    assert skill.hints(), f"{ruta.name} no aporta hints"


def test_todo_lr_declarado_cita_su_fuente():
    """Un likelihood ratio sin procedencia es un número inventado con
    formato científico, y mueve la probabilidad que ve un clínico."""
    for ruta in _skills_del_repo():
        skill = Skill(ruta.stem, ruta.read_text(encoding="utf-8"))
        for signo in skill.signos:
            if signo.lr is not None and signo.lr != 1.0:
                assert signo.fuente, f"{ruta.name}: '{signo.nombre}' sin fuente"


# --- Carga segura -----------------------------------------------------


class TestCargaSegura:
    def _gestor(self, tmp_path):
        from holonmed.config import Settings

        (tmp_path / "valida.md").write_text(SKILL_YAML, encoding="utf-8")
        return SkillManager(Settings(skills_dir=tmp_path))

    def test_carga_una_skill_existente(self, tmp_path):
        assert self._gestor(tmp_path).cargar("valida") is not None

    def test_acepta_el_nombre_con_extension(self, tmp_path):
        assert self._gestor(tmp_path).cargar("valida.md") is not None

    def test_rechaza_el_recorrido_de_directorios(self, tmp_path):
        """El nombre puede venir de un LLM: no debe escapar del directorio."""
        gestor = self._gestor(tmp_path)
        for malicioso in (
            "../../../etc/passwd",
            "..\\..\\windows\\win.ini",
            "/etc/hosts",
        ):
            assert gestor.cargar(malicioso) is None

    def test_siempre_hay_una_skill_por_defecto(self, tmp_path):
        assert self._gestor(tmp_path).cargar_o_defecto("inexistente") is not None

    def test_se_localizan_protocolos_por_ambito_de_grafo(self, tmp_path):
        """Permite preguntar qué protocolos aplican a un paciente a partir
        de los conceptos que ya tiene, sin depender del texto de hoy."""
        gestor = self._gestor(tmp_path)
        assert [s.nombre for s in gestor.para_concepto({"HM:0730"})] == ["valida"]
        assert gestor.para_concepto({"HM:9999"}) == []


# --- Proyección al prompt ---------------------------------------------


@pytest.mark.parametrize("formato", ["minimo", "prosa", "etiquetas"])
def test_todos_los_formatos_conservan_la_prosa(formato):
    assert "PROTOCOLO DE PRUEBA" in Skill("p", SKILL_YAML).para_prompt(formato)


def test_el_formato_minimo_no_expone_los_cortes():
    """Documenta el fallo que motivó la comparación: sin cortes en el
    prompt, el auditor se los inventa."""
    texto = Skill("p", SKILL_YAML).para_prompt("minimo")
    assert "8.5" not in texto


@pytest.mark.parametrize("formato", ["prosa", "etiquetas"])
def test_los_formatos_con_contexto_exponen_los_cortes(formato):
    texto = Skill("p", SKILL_YAML).para_prompt(formato)
    assert "8.5" in texto
    assert "Hipocalcemia" in texto


def test_el_formato_etiquetas_esta_bien_formado():
    texto = Skill("p", SKILL_YAML).para_prompt("etiquetas")
    for etiqueta in ("valores_de_referencia", "terminos_reconocidos"):
        assert texto.count(f"<{etiqueta}>") == texto.count(f"</{etiqueta}>") == 1


def test_el_protocolo_de_pancreatitis_expone_sus_cortes():
    """Regresión del fallo real: el auditor escribió que el límite de la
    lipasa era «aprox. 250-300» cuando el protocolo declara 60."""
    ruta = DIRECTORIO_SKILLS / "acute_pancreatitis.md"
    skill = Skill("acute_pancreatitis", ruta.read_text(encoding="utf-8"))
    texto = skill.para_prompt("prosa")
    for corte in ("110", "60", "44", "8.5"):
        assert corte in texto, f"el corte {corte} no llega al modelo"


# --- Los conceptos que el protocolo acuña ----------------------------
#
# Un hint colgado degrada un hallazgo. Un `produce` colgado hace que el
# clasificador emita el DIAGNÓSTICO sin linaje ni mapeo CIE-10, en
# silencio y con todos los criterios satisfechos. Hasta ahora nadie lo
# comprobaba.


class IndiceFalso:
    """Índice mínimo: sabe qué códigos y qué términos existen."""

    def __init__(self, codigos: set[str], terminos: set[str]):
        self._codigos = codigos
        self._terminos = {t.lower() for t in terminos}

    def buscar_codigo(self, codigo, sistema=None):
        return object() if codigo in self._codigos else None

    def buscar_exacto(self, texto):
        return object() if texto.lower() in self._terminos else None


PROTOCOLO_QUE_ACUNA = """---
titulo: Protocolo que acuña un término
condicion:
  nombre: Pancreatitis aguda
  codigos: { snomed: "197456007" }
signos:
  - nombre: Hiperlipasemia
    codigos: { holonmed: "HM:0732" }
    lr: 26.6
    fuente: JAMA
clasificacion:
  nombre: Criterios de Atlanta
  requiere: 1
  criterios:
    - nombre: Enzimas elevadas
      satisface_si: ["HM:0732"]
  produce:
    termino: Pancreatitis aguda
    codigos: { holonmed: "HM:1002" }
---

Cuerpo.
"""


def _skill_que_acuna():
    return Skill("acuna", PROTOCOLO_QUE_ACUNA)


def test_el_termino_acunado_desaparecido_se_denuncia():
    """El fallo silencioso que motivó esta comprobación."""
    index = IndiceFalso({"HM:0732"}, {"Hiperlipasemia"})
    fallos = _skill_que_acuna().problemas(index)

    assert any("acuña 'Pancreatitis aguda'" in f for f in fallos)
    assert any("sin linaje ni CIE-10" in f for f in fallos)


def test_la_condicion_desaparecida_se_denuncia():
    """Es el caso de HM:6007: la condición vive fuera de `conceptos/`."""
    index = IndiceFalso({"HM:0732", "HM:1002"}, {"Hiperlipasemia", "Pancreatitis aguda"})
    sin_condicion = IndiceFalso({"HM:0732"}, {"Hiperlipasemia"})

    assert not any("la condición" in f for f in _skill_que_acuna().problemas(index))
    assert any("la condición" in f for f in _skill_que_acuna().problemas(sin_condicion))


def test_basta_una_asa_para_dar_por_anclado_el_concepto():
    """Anclar por cualquier código o por el término, no por el preferente.

    La pancreatitis del repositorio declara sólo su código SNOMED y corre
    sin SNOMED cargado. Exigir el código preferente la marcaría como rota
    nada más instalar, y un validador que falla de fábrica no se lee.
    """
    solo_por_termino = IndiceFalso({"HM:0732"}, {"Hiperlipasemia", "Pancreatitis aguda"})
    solo_por_codigo = IndiceFalso({"HM:0732", "197456007", "HM:1002"}, {"Hiperlipasemia"})

    assert _skill_que_acuna().problemas(solo_por_termino) == []
    assert _skill_que_acuna().problemas(solo_por_codigo) == []


def test_sin_indice_no_se_comprueban_los_acunados():
    """Sin vocabulario cargado no se inventan fallos, igual que con los hints."""
    assert _skill_que_acuna().problemas() == []


@pytest.mark.parametrize("ruta", _skills_del_repo(), ids=lambda p: p.stem)
def test_los_protocolos_del_repositorio_anclan_lo_que_acunan(ruta, tmp_path):
    """Con el vocabulario semilla real, ningún protocolo acuña al vacío.

    Éste es el test que habría detectado la colisión de `HM:6007` sin que
    nadie tuviera que mirar dos ramas a mano.
    """
    from holonmed.core.terminology import TerminologyIndex, VocabularyLoader
    from holonmed.db import Database, GraphRepo

    semilla = Path(__file__).resolve().parents[1] / "data" / "vocabulario_semilla.json"
    db = Database(str(tmp_path / "vocabulario.db"))
    VocabularyLoader(db).cargar_semilla(semilla)
    index = TerminologyIndex(db, GraphRepo(db))

    skill = Skill(ruta.stem, ruta.read_text(encoding="utf-8"))
    assert skill._problemas_acunados(index) == []


# --- Un `tipo` desconocido no puede desactivar comprobaciones ----------
#
# El salto de `test_los_protocolos_clinicos_aportan_hints` enruta hacia una
# rama sobre la que no se afirma nada, y su condición fue durante un tiempo
# `tipo != "clinico"`: una negación abierta sobre el único campo taxonómico
# del parseador sin lista blanca. Cualquier cadena que no fuera exactamente
# "clinico" —un acento, una mayúscula, la clave sin valor— eximía al
# protocolo de declarar signos Y saltaba la comprobación de hints, con la
# build en verde.
#
# Verde no significa comprobado si nadie miró qué camino se recorrió.

PLANTILLA_TIPO = """---
titulo: Protocolo de prueba
condicion:
  nombre: Apendicitis
tipo: '{tipo}'
---

PROTOCOLO
"""


@pytest.mark.parametrize(
    "declarado", ["clínico", "Clinico", "documeto", "", "None", "clinic"]
)
def test_un_tipo_desconocido_cae_al_valor_mas_estricto(declarado):
    """Lo desconocido se normaliza a `clinico`, que es el que más exige.

    La dirección es lo que importa: caía al más permisivo por accidente —al
    no coincidir con ninguna rama, escapaba de todas—. `problemas()` sólo
    corre bajo `skills --validar`, así que la normalización es la única
    defensa que actúa también en producción.
    """
    skill = Skill("x", PLANTILLA_TIPO.format(tipo=declarado))

    assert skill.tipo == "clinico"
    assert skill.tipo_declarado == declarado
    assert any("no declara signos" in f for f in skill.problemas())


@pytest.mark.parametrize("declarado", ["clínico", "documeto", ""])
def test_un_tipo_desconocido_se_denuncia(declarado):
    """Normalizar en silencio arreglaría el efecto y ocultaría la errata."""
    skill = Skill("x", PLANTILLA_TIPO.format(tipo=declarado))
    assert any("desconocido" in f for f in skill.problemas())


@pytest.mark.parametrize("valido", ["clinico", "operativo", "documento"])
def test_los_tipos_validos_se_respetan(valido):
    skill = Skill("x", PLANTILLA_TIPO.format(tipo=valido))
    assert skill.tipo == valido
    assert not any("desconocido" in f for f in skill.problemas())
