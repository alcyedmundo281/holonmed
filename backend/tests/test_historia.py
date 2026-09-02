"""La historia del holon: que lea las cinco tablas y que no calle nada.

Sobre una base real y no sobre dobles: el valor de esta pieza está en el SQL
y en los nombres de las columnas, que es justo donde falló la primera versión
—sondeaba `documento` buscando una columna `timestamp` que no existe y
devolvía cero recetas sin decirlo—.
"""

import json

import pytest

from holonmed.core.historia import HistoriaRepo
from holonmed.core.terminology import VocabularyLoader
from holonmed.db import Database, GraphRepo

VOCABULARIO = {
    "conceptos": [
        {"codigo": "T:0", "termino": "Hallazgo clínico"},
        {"codigo": "T:AB", "termino": "Trastorno abdominal", "padre": "T:0"},
        {"codigo": "T:AP", "termino": "Apendicitis aguda", "padre": "T:AB"},
        {"codigo": "T:NE", "termino": "Trastorno neurológico", "padre": "T:0"},
        {"codigo": "T:BR", "termino": "Bradicinesia", "padre": "T:NE"},
    ]
}


@pytest.fixture
def base(tmp_path):
    ruta = tmp_path / "vocab.json"
    ruta.write_text(json.dumps(VOCABULARIO), encoding="utf-8")
    db = Database(tmp_path / "historia.db")
    VocabularyLoader(db).cargar_semilla(ruta)

    cx = db.conexion()
    cx.execute(
        "INSERT INTO paciente (id, nombre, creado) VALUES "
        "('P1', 'Prueba', '2024-01-01T00:00:00')"
    )

    def concepto(codigo):
        fila = cx.execute(
            "SELECT id FROM concepto WHERE codigo = ? LIMIT 1", (codigo,)
        ).fetchone()
        return fila["id"] if fila else None

    cx.execute(
        "INSERT INTO tic (id, paciente_id, timestamp, origen, actor, skill, "
        "texto_original, resumen) VALUES "
        "(1, 'P1', '2024-03-01T09:00:00', 'consulta', 'Dr. A', 'abdomen', 't', 'dolor')"
    )
    cx.execute(
        "INSERT INTO orden (paciente_id, tic_id, timestamp, termino, codigo, "
        "sistema, concepto_id, prescriptor, detalle, estado) VALUES "
        "('P1', 1, '2024-03-01T09:30:00', 'Apendicectomía', 'T:AP', 'holonmed', "
        f"{concepto('T:AP')}, 'Dr. A', '{{\"via\": \"laparoscopica\"}}', 'pendiente')"
    )
    cx.execute(
        "INSERT INTO ejecucion (paciente_id, tic_id, timestamp, termino, codigo, "
        "sistema, actor, origen, campos_faltantes) VALUES "
        "('P1', 1, '2024-03-01T12:00:00', 'Apendicectomía', 'T:AP', 'holonmed', "
        "'Dr. B', 'quirofano', '[\"hora_fin\"]')"
    )
    cx.execute(
        "INSERT INTO orden (paciente_id, tic_id, timestamp, termino, codigo, "
        "sistema, concepto_id, prescriptor, estado) VALUES "
        "('P1', 1, '2024-03-02T08:00:00', 'Levodopa', 'T:BR', 'holonmed', "
        f"{concepto('T:BR')}, 'Dr. C', 'pendiente')"
    )
    cx.execute(
        "INSERT INTO documento (tic_id, paciente_id, tipo, archivo, creado) "
        "VALUES (1, 'P1', 'receta', 'r.pdf', '2024-03-02T08:05:00')"
    )
    cx.execute(
        "INSERT INTO infon (tic_id, paciente_id, concepto_id, timestamp, "
        "texto_origen, termino_propuesto, termino, polaridad, codigo, sistema, "
        "estado, confianza) VALUES "
        f"(1, 'P1', {concepto('T:BR')}, '2024-03-03T10:00:00', 'lento', "
        "'Bradicinesia', 'Bradicinesia', 'presente', 'T:BR', 'holonmed', "
        "'VALIDADO', 90)"
    )
    cx.commit()
    return db


@pytest.fixture
def repo(base):
    return HistoriaRepo(base, GraphRepo(base))


# --- Que las cinco tablas lleguen ────────────────────────────────────────────


def test_la_historia_lee_las_cinco_tablas(repo):
    h = repo.del_holon("P1")
    clases = {a.clase for a in h.acciones}
    assert clases == {"consulta", "orden", "ejecucion", "documento", "hallazgo"}


def test_las_recetas_no_desaparecen(repo):
    """El fallo de la primera versión: la columna de `documento` se llama
    `creado`, no `timestamp`, y el sondeo devolvía cero sin decirlo."""
    h = repo.del_holon("P1")
    assert [a.termino for a in h.acciones if a.clase == "documento"] == ["receta"]


def test_la_historia_va_de_lo_mas_reciente_a_lo_mas_antiguo(repo):
    momentos = [a.momento for a in repo.del_holon("P1").acciones]
    assert momentos == sorted(momentos, reverse=True)


def test_el_detalle_json_se_lee_en_prosa(repo):
    orden = next(
        a
        for a in repo.del_holon("P1").acciones
        if a.termino == "Apendicectomía" and a.clase == "orden"
    )
    assert "laparoscopica" in orden.detalle


# --- La orden y la ejecución no se funden ───────────────────────────────────


def test_una_orden_sin_ejecucion_se_distingue_de_una_cumplida(repo):
    """Una orden es una regla de acción declarada; una ejecución es el acto.

    Fundirlas en «lo que pasó» borraría justo el sitio donde una creencia se
    enunció y no se sostuvo en la conducta.
    """
    pendientes = repo.del_holon("P1").ordenes_sin_ejecutar()
    assert [a.termino for a in pendientes] == ["Levodopa"]


def test_una_ejecucion_incompleta_lo_dice(repo):
    ejec = next(a for a in repo.del_holon("P1").acciones if a.clase == "ejecucion")
    assert "hora_fin" in ejec.estado


# --- El territorio, y lo que no puede colocarse ─────────────────────────────


def test_el_ambito_recorta_por_territorio(repo):
    h = repo.del_holon("P1", ambito=["T:AB"])
    assert {a.termino for a in h.acciones} == {"Apendicectomía"}
    assert h.fuera_de_territorio > 0


def test_el_ambito_usa_el_cierre_transitivo(repo):
    """`T:NE` no es el concepto de la acción: es su ancestro."""
    h = repo.del_holon("P1", ambito=["T:NE"])
    assert "Levodopa" in {a.termino for a in h.acciones}
    assert "Bradicinesia" in {a.termino for a in h.acciones}


def test_lo_que_no_se_puede_ubicar_no_se_declara_irrelevante(repo):
    """El modo de fallo que este módulo se niega a cometer en silencio.

    Una acción sin `concepto_id` —un tic, una receta— no se puede situar en
    ningún territorio. Devolverla como «fuera» convertiría «no sé dónde va»
    en «no aplica», que es una afirmación que nadie ha comprobado.
    """
    h = repo.del_holon("P1", ambito=["T:AB"])

    sin_ubicar = {a.clase for a in h.sin_ubicar}
    assert "consulta" in sin_ubicar and "documento" in sin_ubicar
    assert all(not a.ubicable for a in h.sin_ubicar)
    # y se dice en voz alta, que es la otra mitad
    assert "SIN CONCEPTO" in h.resumen()
    assert "NO se han descartado" in h.para_llm()


def test_un_ambito_roto_no_es_un_territorio_vacio(repo):
    """Recortar con un ámbito que no resuelve dejaría la historia a cero y
    parecería un paciente sin historia."""
    h = repo.del_holon("P1", ambito=["T:NO_EXISTE"])
    assert h.total > 0
    assert any("no resuelve" in t for t in h.traza)


# --- La ventana temporal ────────────────────────────────────────────────────


def test_la_ventana_temporal_recorta_por_los_dos_lados(repo):
    h = repo.del_holon("P1", desde="2024-03-02T00:00:00", hasta="2024-03-02T23:59:59")
    assert {a.termino for a in h.acciones} == {"Levodopa", "receta"}


def test_una_historia_recortada_por_limite_lo_dice(repo):
    h = repo.del_holon("P1", limite=2)
    assert h.total == 2
    assert h.truncada
    assert "recortada" in h.resumen()


# --- El texto para el modelo ────────────────────────────────────────────────


def test_el_texto_para_el_modelo_lleva_el_resumen_y_los_pendientes(repo):
    texto = repo.del_holon("P1").para_llm()
    assert "HISTORIA DE ACCIONES" in texto
    assert "ÓRDENES SIN EJECUCIÓN" in texto
    assert "Levodopa" in texto


def test_un_paciente_sin_acciones_no_finge_tenerlas(repo):
    h = repo.del_holon("P_INEXISTENTE")
    assert h.total == 0
    assert "sin acciones" in h.resumen()


def test_el_territorio_no_depende_del_cierre_materializado(base, repo):
    """`ancestro` se rellena sólo dentro de `TicRepo.guardar`, y sólo para los
    infones VALIDADOS de ese tic.

    Un concepto que llegó por `orden` o por `ejecucion` y que nunca fue infón
    no tiene fila ahí. Un filtro apoyado en esa tabla diría «ninguna acción en
    este territorio» cuando la verdad es «no he mirado». Esta prueba fija que
    el recorrido no la usa: con `ancestro` VACÍA, el territorio sigue saliendo.
    """
    cx = base.conexion()
    assert cx.execute("SELECT COUNT(*) c FROM ancestro").fetchone()["c"] == 0

    h = repo.del_holon("P1", ambito=["T:AB"])
    assert {a.termino for a in h.acciones} == {"Apendicectomía"}
