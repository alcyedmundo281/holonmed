"""Dos signos declarados, uno incluido en el otro: una sola observación.

PARÁMETRO DE SEGURIDAD. «Descenso del segmento ST» es un caso de «Signos de
isquemia en el electrocardiograma». Antes sólo impedía contarlos dos veces una
instrucción en prosa del prompt (regla 5 de AGENTS.md): con el protocolo real,
un trazado daba 67.95 % en vez de 37.06 %. Aquí se fija la regla de
`core/inclusion.py` y que Bayes, veredicto, promoción y Φ la apliquen igual.

Todo el texto es sintético.
"""

import math
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from holonmed.core.acoplamiento import MedidorDeAcoplamiento
from holonmed.core.bayes import AntigenPresentingCell
from holonmed.core.inclusion import unificar
from holonmed.core.pipeline import _avisar_protocolo
from holonmed.core.promocion import EvaluadorDePromocion
from holonmed.core.skills import Skill
from holonmed.core.veredicto import EvaluadorDeVeredicto
from holonmed.db import Database, GraphRepo, TicRepo
from holonmed.models import EstadoInfon, Infon, Polaridad, ResultadoTic

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import convertir_condicion  # noqa: E402

ESPECIFICO = ("Descenso del segmento ST", "HM:3015")
AMPLIO = ("Signos de isquemia en el electrocardiograma", "HM:3016")


def infon(signo, presente=True, confianza=80.0, **extra):
    termino, codigo = signo
    return Infon(
        texto_origen="trazado sintético",
        termino_propuesto=termino,
        termino=termino,
        codigo=codigo,
        sistema="holonmed",
        polaridad=Polaridad.PRESENTE if presente else Polaridad.AUSENTE,
        estado=EstadoInfon.VALIDADO,
        confianza=confianza,
        **extra,
    )


UN_TRAZADO = [infon(ESPECIFICO), infon(AMPLIO)]


@pytest.fixture
def sca():
    ruta = RAIZ / "skills" / "sindrome_coronario_agudo.md"
    return Skill(ruta.stem, ruta.read_text(encoding="utf-8"))


def signo(
    nombre, codigo, rol="prueba_especifica", incluido=None, lr=None, lr_neg=None, extra=""
):
    lineas = [
        f"  - nombre: {nombre}",
        f'    codigos: {{ holonmed: "{codigo}" }}',
        f"    rol: {rol}",
        "    fuente: sintética",
    ]
    if incluido is not None:
        lineas.append(f"    incluido_en: {incluido}")
    if lr is not None:
        lineas.append(f"    lr: {lr}")
    if lr_neg is not None:
        lineas.append(f"    lr_negativo: {lr_neg}")
    if extra:
        lineas.append(f"    {extra}")
    return "\n".join(lineas)


def protocolo(*signos, bloques=""):
    return Skill(
        "sintetico",
        "---\ntitulo: Protocolo sintético\n"
        "condicion: { nombre: Condición sintética }\n"
        "modelo_bayesiano: { probabilidad_base: 0.1 }\n"
        "signos:\n" + "\n".join(signos) + "\n" + bloques + "---\n",
    )


CONTAR = """balance:
  probable: { apoyos_minimos: 2 }
  fuente: sintética
promocion:
  exige: { prueba_especifica: 2 }
  fuente: sintética
"""


@pytest.fixture
def contado():
    return protocolo(
        signo(*ESPECIFICO, incluido='["HM:3016"]'), signo(*AMPLIO), bloques=CONTAR
    )


def bayes(skill, infones):
    return AntigenPresentingCell().calcular({}, skill.para_bayes(), infones)


def phi(skill, infones):
    return MedidorDeAcoplamiento().medir(skill, infones)


def observadas(acoplamiento):
    return [c.dimension for c in acoplamiento.componentes if c.observado]


def dimensiones(acoplamiento):
    return [c.dimension for c in acoplamiento.componentes if c.esperado]


# --- El caso que lo motivó, con el protocolo real ------------------------


def test_el_protocolo_real_declara_el_par(sca):
    assert sca.errores_inclusion == []
    assert sca.inclusiones == {ESPECIFICO[0].lower(): frozenset({AMPLIO[0].lower()})}


@pytest.mark.parametrize("trazado", [UN_TRAZADO, UN_TRAZADO[::-1]])
def test_bayes_no_multiplica_dos_veces_el_mismo_trazado(sca, trazado):
    ambos = bayes(sca, trazado)

    assert ambos.probabilidad_porcentaje == 37.06
    assert (
        ambos.probabilidad_porcentaje
        == bayes(sca, [infon(ESPECIFICO)]).probabilidad_porcentaje
    )
    assert len(ambos.evidencia_utilizada) == 1
    assert any("una sola observación" in linea for linea in ambos.traza_logica)


def test_phi_ve_una_sola_observacion(sca):
    ambos = phi(sca, UN_TRAZADO)
    solo = phi(sca, [infon(ESPECIFICO)])

    assert observadas(ambos) == [ESPECIFICO[0]]
    assert AMPLIO[0] not in dimensiones(ambos)
    assert (ambos.phi, ambos.cobertura, ambos.anclaje) == (
        solo.phi,
        solo.cobertura,
        solo.anclaje,
    )
    assert ambos.phi_categorico == solo.phi_categorico
    assert AMPLIO[0] not in ambos.indagacion
    assert ambos.resto_no_simbolizado == []


def test_phi_lee_el_mismo_vector_que_bayes(sca):
    for trazado in (UN_TRAZADO, [infon(ESPECIFICO, False), infon(AMPLIO)]):
        inferencia = bayes(sca, trazado)
        p, p0 = (
            inferencia.probabilidad_porcentaje / 100,
            inferencia.probabilidad_previa / 100,
        )
        delta = math.log(p / (1 - p)) - math.log(p0 / (1 - p0))
        vector = sum(
            c.observado
            for c in phi(sca, trazado).componentes
            if c.rol != "no_contemplado"
        )
        assert vector == pytest.approx(delta, abs=1e-3)


def test_sin_mirar_el_par_es_una_sola_dimension_la_amplia(sca):
    lectura = phi(sca, [])

    assert AMPLIO[0] in dimensiones(lectura)
    assert ESPECIFICO[0] not in dimensiones(lectura)


# --- La tabla ------------------------------------------------------------


@pytest.fixture
def con_lr():
    return protocolo(
        signo(*ESPECIFICO, incluido='["HM:3016"]', lr=5.0, lr_neg=0.5),
        signo(*AMPLIO, lr=3.0, lr_neg=0.2),
    )


@pytest.mark.parametrize(
    "estrecho, amplio, cuenta, lr",
    [
        (True, True, [ESPECIFICO[0]], 5.0),
        (False, True, [AMPLIO[0]], 3.0),
        (False, False, [AMPLIO[0]], 0.2),
        (True, False, [], 1.0),
        (True, None, [ESPECIFICO[0]], 5.0),
        (False, None, [ESPECIFICO[0]], 0.5),
        (None, True, [AMPLIO[0]], 3.0),
        (None, False, [AMPLIO[0]], 0.2),
    ],
)
def test_que_cuenta_en_cada_combinacion(con_lr, estrecho, amplio, cuenta, lr):
    infones = [
        infon(s, presente)
        for s, presente in ((ESPECIFICO, estrecho), (AMPLIO, amplio))
        if presente is not None
    ]
    odds = (0.1 / 0.9) * lr

    inferencia = bayes(con_lr, infones)

    assert inferencia.probabilidad_porcentaje == round(100 * odds / (1 + odds), 2)
    assert observadas(phi(con_lr, infones)) == cuenta


def test_la_especifica_manda_aunque_su_cociente_sea_el_menor():
    skill = protocolo(
        signo(*ESPECIFICO, incluido='["HM:3016"]', lr=2.0), signo(*AMPLIO, lr=9.0)
    )

    assert "LR 2.0" in bayes(skill, UN_TRAZADO).evidencia_utilizada[0]


def test_la_contradiccion_se_informa_y_no_se_resuelve_por_fecha(con_lr, contado):
    ahora = datetime.now(UTC).isoformat()
    antes = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    for fechas in ((ahora, antes), (antes, ahora)):
        infones = [
            infon(ESPECIFICO, True, timestamp=fechas[0]),
            infon(AMPLIO, False, timestamp=fechas[1]),
        ]
        for traza in (
            bayes(con_lr, infones).traza_logica,
            phi(con_lr, infones).traza,
            EvaluadorDeVeredicto().evaluar(contado, infones).traza,
            EvaluadorDePromocion().evaluar(contado, infones).traza,
        ):
            assert any("contradicción" in linea for linea in traza)
        assert bayes(con_lr, infones).evidencia_utilizada == []
        # El par queda como una sola dimensión sin medir.
        assert dimensiones(phi(con_lr, infones)) == [AMPLIO[0]]


def test_un_signo_sin_cociente_tambien_descarta_al_que_lo_incluye():
    """Bayes juzga el par antes de mirar quién trae LR."""
    skill = protocolo(signo(*ESPECIFICO, incluido='["HM:3016"]'), signo(*AMPLIO, lr=3.0))

    assert bayes(skill, UN_TRAZADO).evidencia_utilizada == []


TERCERO = ("Descenso del segmento ST en cara inferior", "HM:9001")
HERMANO = ("Onda T invertida", "HM:9002")


def test_la_inclusion_es_transitiva():
    skill = protocolo(
        signo(*TERCERO, incluido='["HM:3015"]', lr=7.0),
        signo(*ESPECIFICO, incluido='["HM:3016"]', lr=5.0),
        signo(*AMPLIO, lr=3.0),
    )

    evidencia = bayes(skill, [infon(TERCERO), infon(AMPLIO)]).evidencia_utilizada

    assert len(evidencia) == 1 and "LR 7.0" in evidencia[0]


def test_dos_especificos_del_mismo_amplio_se_cuentan_los_dos():
    skill = protocolo(
        signo(*ESPECIFICO, incluido='["HM:3016"]', lr=5.0),
        signo(*HERMANO, incluido='["HM:3016"]', lr=2.0),
        signo(*AMPLIO, lr=3.0),
    )
    infones = [infon(ESPECIFICO), infon(HERMANO), infon(AMPLIO)]

    assert observadas(phi(skill, infones)) == [ESPECIFICO[0], HERMANO[0]]
    assert len(bayes(skill, infones).evidencia_utilizada) == 2


def test_dos_signos_sin_declaracion_no_se_unifican_por_el_nombre():
    skill = protocolo(signo(*ESPECIFICO, lr=5.0), signo(*AMPLIO, lr=3.0))

    assert len(bayes(skill, UN_TRAZADO).evidencia_utilizada) == 2


def test_unificar_sin_inclusiones_no_toca_nada():
    elegidos = {"a": infon(ESPECIFICO), "b": infon(AMPLIO)}

    assert unificar(elegidos, {}).cuentan == elegidos


# --- Veredicto y promoción -----------------------------------------------


def test_el_veredicto_cuenta_un_apoyo(contado):
    veredicto = EvaluadorDeVeredicto().evaluar(contado, UN_TRAZADO)

    assert veredicto.apoyos == [ESPECIFICO[0]]
    assert veredicto.nivel is None


@pytest.mark.parametrize(
    "infones, satisfecho",
    [
        ([infon(ESPECIFICO), infon(AMPLIO)], True),
        ([infon(ESPECIFICO)], True),
        ([infon(ESPECIFICO), infon(AMPLIO, False)], False),
        ([infon(ESPECIFICO, False), infon(AMPLIO, False)], False),
    ],
)
def test_un_nucleo_que_exige_el_amplio_lo_satisface_el_estrecho(infones, satisfecho):
    skill = protocolo(
        signo(*ESPECIFICO, incluido='["HM:3016"]'),
        signo(*AMPLIO),
        bloques=f"nucleo: {{ requiere: ['{AMPLIO[0]}'] }}\n" + CONTAR,
    )

    traza = EvaluadorDeVeredicto().evaluar(skill, infones).traza

    assert any("Núcleo no documentado" in t for t in traza) is not satisfecho


def test_la_promocion_no_completa_la_tupla_con_un_trazado(contado):
    veredicto = EvaluadorDePromocion().evaluar(contado, UN_TRAZADO)

    assert veredicto.cumplido["prueba_especifica"] == 1
    assert not veredicto.promueve


def test_un_registro_repetido_no_deja_volver_al_par(contado):
    """Dos lecturas opuestas del estrecho: el par se juzga y se cuenta con una."""
    antes = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    infones = [infon(ESPECIFICO, False, timestamp=antes), *UN_TRAZADO]

    assert EvaluadorDeVeredicto().evaluar(contado, infones).apoyos == [ESPECIFICO[0]]
    assert EvaluadorDePromocion().evaluar(contado, infones).cumplido == {
        "prueba_especifica": 1
    }


SENSIBLE = ("Prueba sensible sintética", "HM:9003")


@pytest.mark.parametrize(
    "medido, pedidas",
    [
        ([], [AMPLIO[0]]),
        ([infon(AMPLIO, False)], []),
        ([infon(ESPECIFICO, False)], []),
    ],
)
def test_no_se_pide_dos_veces_la_misma_observacion(medido, pedidas):
    skill = protocolo(
        signo(*SENSIBLE, rol="prueba_sensible"),
        signo(*ESPECIFICO, incluido='["HM:3016"]'),
        signo(*AMPLIO),
        bloques="promocion:\n"
        "  exige: { prueba_sensible: 1, prueba_especifica: 1 }\n"
        "  fuente: sintética\n",
    )

    veredicto = EvaluadorDePromocion().evaluar(skill, [infon(SENSIBLE), *medido])

    assert [p.termino for p in veredicto.propuestas] == pedidas


# --- Declaraciones que no se pueden cumplir: fallo cerrado ----------------


def _par(**estrecho):
    return protocolo(
        signo(*ESPECIFICO, lr=5.0, **estrecho), signo(*AMPLIO, lr=3.0), bloques=CONTAR
    )


MAL_DECLARADOS = {
    "no es lista": _par(incluido="HM:3016"),
    "lista vacía": _par(incluido="[]"),
    "nula": _par(incluido="null"),
    "no son textos": _par(incluido="[3016]"),
    "código ausente": _par(incluido='["HM:9999"]'),
    "por nombre": _par(incluido=f'["{AMPLIO[0]}"]'),
    "a sí mismo": _par(incluido='["HM:3015"]'),
    "errata en la clave": _par(extra='incluida_en: ["HM:3016"]'),
    "otro rol": _par(rol="apoyo", incluido='["HM:3016"]'),
    "otro efecto": _par(incluido='["HM:3016"]', extra="efecto: bandera_roja"),
    "otro disparador": _par(incluido='["HM:3016"]', extra="dispara_si: ausente"),
    "graduado": _par(
        incluido='["HM:3016"]', extra="tramos: [{ umbral: sintético, lr: 2.0 }]"
    ),
    "exclusiones": protocolo(
        signo(*ESPECIFICO, incluido='["HM:3016"]', extra="efecto: excluye"),
        signo(*AMPLIO, extra="efecto: excluye"),
    ),
    "banderas rojas": protocolo(
        signo(*ESPECIFICO, incluido='["HM:3016"]', extra="efecto: bandera_roja"),
        signo(*AMPLIO, extra="efecto: bandera_roja"),
    ),
    "código ambiguo": protocolo(
        signo(*ESPECIFICO, incluido='["HM:3016"]'),
        signo(*AMPLIO),
        signo("Otro con el mismo código", "HM:3016"),
    ),
    "ciclo": protocolo(
        signo(*ESPECIFICO, incluido='["HM:3016"]'),
        signo(*AMPLIO, incluido='["HM:3015"]'),
    ),
}


@pytest.mark.parametrize("caso", MAL_DECLARADOS)
def test_una_declaracion_invalida_detiene_a_los_cuatro(caso):
    skill = MAL_DECLARADOS[caso]

    assert skill.errores_inclusion
    assert skill.inclusiones == {}
    assert set(skill.errores_inclusion) <= set(skill.problemas())
    assert bayes(skill, UN_TRAZADO) is None
    assert phi(skill, UN_TRAZADO) is None
    assert EvaluadorDeVeredicto().evaluar(skill, UN_TRAZADO) is None
    assert EvaluadorDePromocion().evaluar(skill, UN_TRAZADO) is None


def test_el_tic_dice_por_que_no_calculo_y_lo_persiste(tmp_path):
    resultado = ResultadoTic(
        paciente_id="p1", texto_original="texto sintético", skill_activa="sintetico"
    )
    skill = MAL_DECLARADOS["código ausente"]
    _avisar_protocolo(resultado, skill)
    _avisar_protocolo(resultado, skill)

    assert resultado.aviso_protocolo.count("mal declarada") == 1
    assert "HM:9999" in resultado.aviso_protocolo

    base = Database(tmp_path / "t.db")
    tics = TicRepo(base, GraphRepo(base))
    guardado = tics.tic_completo(tics.guardar(resultado))
    assert guardado["aviso_protocolo"] == resultado.aviso_protocolo
    base.cerrar()


def test_los_protocolos_del_repositorio_declaran_bien():
    for ruta in (RAIZ / "skills").glob("*.md"):
        skill = Skill(ruta.stem, ruta.read_text(encoding="utf-8"))
        assert skill.errores_inclusion == [], ruta.name


# --- El conversor --------------------------------------------------------


def _indice(conceptos):
    return convertir_condicion.Indice(
        ruta=Path("/no/existe"),
        conceptos=conceptos,
        condiciones={},
        referencias={},
        archivos={},
        commit="0" * 7,
        limpio=True,
    )


def _convertir_signos(**del_estrecho):
    conceptos = {
        "HM:3015": {"termino": ESPECIFICO[0], **del_estrecho},
        "HM:3016": {"termino": AMPLIO[0], "semantica": "agrupacion"},
    }
    aristas = [
        {"concepto": c, "lr_positivo": {"valor": v}}
        for c, v in (("HM:3015", 5.3), ("HM:3016", 3.6))
    ]
    informe = convertir_condicion.Informe()
    bloque, _ = convertir_condicion.signos(
        {"signos": aristas}, _indice(conceptos), informe
    )
    return bloque.texto(), [texto for _, texto in informe.pendientes]


def test_el_conversor_traslada_la_inclusion_del_indice():
    texto, pendientes = _convertir_signos(incluido_en=["HM:3016", "HM:9999"])

    assert 'incluido_en: ["HM:3016"]' in texto
    assert not any("agrupación" in p for p in pendientes)


def test_el_conversor_no_la_infiere_y_avisa_de_la_agrupacion():
    texto, pendientes = _convertir_signos(padre="HM:3016")

    assert "incluido_en" not in texto
    assert any("agrupación" in p and "HM:3016" in p for p in pendientes)


def test_el_conversor_no_pisa_una_inclusion_que_no_sabe_regenerar(sca):
    anterior = sca.contenido_completo
    sin_ella = anterior.replace('    incluido_en: ["HM:3016"]\n', "")

    assert convertir_condicion.inclusiones_perdidas(anterior, anterior) == []
    assert convertir_condicion.inclusiones_perdidas(anterior, sin_ella) == [
        "HM:3015 en HM:3016"
    ]


@pytest.mark.parametrize("se_pierde", [True, False])
def test_la_conversion_masiva_tampoco_pisa_una_inclusion(
    tmp_path, monkeypatch, sca, se_pierde
):
    """`--sync-all --forzar` escribe por su lado y necesita la misma guarda."""
    anterior = sca.contenido_completo
    nuevo = anterior.replace("version: 1.1.0", "version: 0.1.0-borrador")
    if se_pierde:
        nuevo = nuevo.replace('    incluido_en: ["HM:3016"]\n', "")
    afectado, otro = tmp_path / "a.md", tmp_path / "b.md"
    afectado.write_text(anterior, encoding="utf-8", newline="\n")

    indice = _indice({})
    indice.condiciones = {"a": {"termino": "a"}, "b": {"termino": "b"}}
    for nombre, doble in {
        "DIRECTORIO_BORRADORES": tmp_path,
        "vocabulario_local": lambda: (set(), Path("semilla.json")),
        "condiciones_con_protocolo": set,
        "nombre_por_defecto": lambda identificador, _: identificador,
        "fragmento_vocabulario": lambda *_: [],
        "convertir": lambda *_: convertir_condicion.Borrador(nuevo, []),
    }.items():
        monkeypatch.setattr(convertir_condicion, nombre, doble)

    salida = convertir_condicion.sync_all(indice, forzar=True, ruta_vocab=None)

    assert salida == (1 if se_pierde else 0)
    assert afectado.read_text(encoding="utf-8") == (anterior if se_pierde else nuevo)
    # Retener uno no impide escribir los demás.
    assert otro.read_text(encoding="utf-8") == nuevo
