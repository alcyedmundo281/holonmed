"""Tests de la lista de problemas y de la evolución SOAP.

Lo que se comprueba por encima de todo es lo que la nota NO puede hacer:
convertir una negación en problema, declarar como S u O lo que nadie declaró,
escribir un análisis o un plan, y colar lo que no está validado.

Todas las narrativas son sintéticas.
"""

import pytest

from holonmed.core.nota_soap import (
    SIN_DATO,
    SIN_PLAN,
    SIN_VALORACION,
    construir_nota,
    declarar_procedencia,
)
from holonmed.db.store import Database, EpisodioRepo, GraphRepo, TicRepo
from holonmed.models import (
    EstadoInfon,
    Infon,
    NotaEvolucion,
    Polaridad,
    ProblemaEvolucion,
    ResultadoTic,
)

NARRATIVA = (
    "Paciente sintético de 45 años.\n"
    "S: Refiere dolor epigástrico desde ayer, con náuseas.\n"
    "O: Afebril. Sin ictericia. Lipasa 900 U/L."
)


def _infon(termino, cita, **extra):
    extra.setdefault("estado", EstadoInfon.VALIDADO)
    return Infon(texto_origen=cita, termino_propuesto=termino, termino=termino, **extra)


def _tic(infones, texto=NARRATIVA, **extra):
    return ResultadoTic(
        paciente_id="sintetico",
        texto_original=texto,
        skill_activa="general_triage",
        infones=infones,
        **extra,
    )


def _caso():
    return _tic(
        [
            _infon("Dolor epigástrico", "dolor epigástrico desde ayer"),
            _infon("Ictericia", "Sin ictericia", polaridad=Polaridad.AUSENTE),
            _infon("Hiperlipasemia", "Lipasa 900 U/L"),
            _infon("Fiebre", "fiebre", estado=EstadoInfon.RUIDO),
        ],
        resumen="Texto libre del modelo que no debe entrar",
    )


@pytest.fixture
def tics(tmp_path):
    db = Database(tmp_path / "soap.db")
    return TicRepo(db, GraphRepo(db))


@pytest.mark.parametrize(
    ("cita", "esperada"),
    [
        ("dolor epigástrico desde ayer", "subjetivo"),
        ("Lipasa 900 U/L.", "objetivo"),
        ("sin ICTERICIA", "objetivo"),
        # Antes de la primera marca nadie declaró nada.
        ("45 años", "sin_declarar"),
        # Una cita que no está literal no se reubica por parecido.
        ("dolor abdominal", "sin_declarar"),
        ("", "sin_declarar"),
    ],
)
def test_s_y_o_salen_de_lo_que_la_narrativa_declara(cita, esperada):
    assert declarar_procedencia(NARRATIVA, cita) == esperada


@pytest.mark.parametrize(
    "narrativa",
    [
        # «Refiere» no es una declaración.
        "Refiere náuseas.",
        # Una letra a mitad de frase no abre sección.
        "Grupo sanguíneo O: náuseas",
        # Otro encabezado cierra la sección abierta.
        "O: afebril\nPlan: vigilar náuseas",
        "S: dolor. P: vigilar náuseas",
        # Y una línea en blanco también.
        "O: afebril\n\nnáuseas",
        # En dos secciones a la vez no se elige.
        "S: náuseas. O: náuseas.",
    ],
)
def test_ante_la_duda_la_cita_queda_sin_declarar(narrativa):
    assert declarar_procedencia(narrativa, "náuseas") == "sin_declarar"


def test_el_defecto_de_un_infon_no_asevera_que_sea_objetivo():
    assert _infon("Náuseas", "náuseas").procedencia == "sin_declarar"


def test_la_nota_va_por_problema_y_deja_a_y_p_al_profesional():
    nota = construir_nota(_caso())

    dolor, lipasa = nota.problemas
    assert dolor.subjetivo == ["dolor epigástrico desde ayer"]
    assert dolor.objetivo == []
    assert lipasa.objetivo == ["Lipasa 900 U/L"]
    assert nota.texto.count(f"A: {SIN_VALORACION}") == 2
    assert nota.texto.count(f"P: {SIN_PLAN}") == 2
    assert f"O: {SIN_DATO}" in nota.texto
    assert "borrador sin firma" in nota.texto
    assert "Texto libre del modelo" not in nota.texto


def test_la_nota_no_tiene_donde_guardar_un_analisis_ni_un_plan():
    """Si alguien añade el campo, la regla deja de ser estructural."""
    campos = set(ProblemaEvolucion.model_fields) | set(NotaEvolucion.model_fields)

    assert not campos & {"analisis", "apreciacion", "plan", "a", "p", "siguiente"}


def test_lo_negado_no_es_problema_y_lo_no_validado_queda_fuera():
    nota = construir_nota(_caso())

    assert [p.termino for p in nota.problemas] == [
        "Dolor epigástrico",
        "Hiperlipasemia",
    ]
    assert [(n.termino, n.procedencia) for n in nota.negativos] == [
        ("Ictericia", "objetivo")
    ]
    assert [(f.termino, f.estado) for f in nota.fuera_de_la_nota] == [("Fiebre", "RUIDO")]
    assert "Ictericia: ausente · «Sin ictericia»" in nota.texto


def test_lo_rechazado_por_una_persona_no_entra():
    nota = construir_nota(_tic([_infon("Náuseas", "náuseas", acto="rechazado")]))

    assert nota.problemas == []
    assert nota.fuera_de_la_nota[0].estado == "RECHAZADO"
    assert "Sin problemas" in nota.texto


def test_lo_derivado_se_dice_derivado_y_no_ocupa_s_ni_o():
    infon = _infon(
        "Trastorno sintético",
        "Lipasa 900 U/L",
        criterio="Criterio de prueba",
        derivado_de=["Hiperlipasemia"],
    )

    problema = construir_nota(_tic([infon])).problemas[0]

    assert problema.derivado == ["Trastorno sintético (criterio: Criterio de prueba)"]
    assert problema.objetivo == []


def test_la_lista_de_problemas_excluye_lo_negado_y_lo_rechazado(tics):
    """El caso reproducido: «Sin ictericia» creaba el problema «Ictericia»."""
    resultado = _caso()
    resultado.infones.append(_infon("Náuseas", "náuseas", acto="rechazado"))
    assert tics.guardar(resultado)

    lista = tics.lista_problemas("sintetico")

    assert [(p["numero"], p["termino"]) for p in lista] == [
        (1, "Dolor epigástrico"),
        (2, "Hiperlipasemia"),
    ]


def test_el_numero_de_un_problema_no_cambia_cuando_reaparece(tics):
    tics.guardar(
        _tic([_infon("Dolor epigástrico", "dolor")], timestamp="2026-01-01T08:00:00")
    )
    segundo = _tic(
        [
            _infon("Náuseas", "náuseas", timestamp="2026-01-02T08:00:00"),
            _infon("Dolor epigástrico", "dolor", timestamp="2026-01-02T08:00:00"),
        ]
    )
    segundo.infones[0].procedencia = "objetivo"
    tics.guardar(segundo)

    nota = construir_nota(segundo, tics.lista_problemas("sintetico"))

    assert [(p.numero, p.termino) for p in nota.problemas][-1] == (2, "Náuseas")
    # Una procedencia puesta sin que la narrativa la declare no se respeta.
    assert nota.problemas[-1].objetivo == []


def test_sin_guardar_no_se_inventa_un_numero():
    nota = construir_nota(_caso())

    assert [p.numero for p in nota.problemas] == [None, None]
    assert "(sin número) Dolor epigástrico" in nota.texto


def test_el_resumen_vivo_es_soap_y_no_convierte_la_negacion_en_problema(tics):
    tics.guardar(_caso())

    fila = (
        tics._db.conexion()
        .execute("SELECT resumen_vivo FROM paciente WHERE id = 'sintetico'")
        .fetchone()
    )
    texto = fila["resumen_vivo"]

    assert "#1 Dolor epigástrico\n  S: «dolor epigástrico desde ayer»" in texto
    assert "#2 Hiperlipasemia" in texto
    assert "#3" not in texto
    assert (
        "Ausencias documentadas (no son problemas): Ictericia («Sin ictericia»)" in texto
    )
    assert f"P: {SIN_PLAN}" in texto
    assert "Texto libre del modelo" not in texto


def test_lo_rechazado_no_marca_un_problema_como_ausente(tics):
    tics.guardar(_tic([_infon("Náuseas", "náuseas")]))
    tics.guardar(
        _tic(
            [
                _infon(
                    "Náuseas",
                    "sin náuseas",
                    polaridad=Polaridad.AUSENTE,
                    acto="rechazado",
                )
            ]
        )
    )

    assert tics.lista_problemas("sintetico")[0]["consta_ausente"] is None


def test_con_texto_dirigido_al_sistema_la_nota_no_tiene_problemas():
    """El pipeline deja todo en ALERTA: a la vista y fuera de la nota."""
    nota = construir_nota(_tic([_infon("Náuseas", "náuseas", estado=EstadoInfon.ALERTA)]))

    assert nota.problemas == []
    assert [f.estado for f in nota.fuera_de_la_nota] == ["ALERTA"]


def test_un_registro_antiguo_no_se_lee_como_objetivo(tmp_path):
    """Lo guardado antes quedó «objetivo» por defecto, sin que nadie lo dijera."""
    db = Database(tmp_path / "antiguo.db")
    episodios = EpisodioRepo(db)
    repo = TicRepo(db, GraphRepo(db))
    db.conexion().execute(
        "INSERT INTO paciente (id, nombre, antecedentes, creado) "
        "VALUES ('sintetico', 'sintetico', '', '2026-01-01')"
    )
    episodio = episodios.abrir("sintetico", "motivo sintético", "comprehensiva")
    base = _tic(
        [_infon("Náuseas", "náuseas")],
        texto="Refiere náuseas.",
        episodio_id=episodio,
        tipo="base",
    )
    assert repo.guardar(base)
    db.conexion().execute("UPDATE infon SET procedencia = 'objetivo'")

    infones = episodios.infones_del_episodio(episodio)

    assert [i.procedencia for i in infones] == ["sin_declarar"]
