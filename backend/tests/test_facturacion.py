"""Tests de la cadena de facturación.

Lo que se protege aquí no es la aritmética sino las reglas que impiden que
esto se convierta en una máquina de facturar de más:

* Sin orden no hay cargo. Es estructural, no una instrucción en un prompt.
* Ningún cargo se factura sin que una persona lo confirme.
* Los descuadres se muestran; no se resuelven solos ni se ocultan.

Y una que es clínica antes que económica: una orden sin ejecutar significa
que el paciente puede no haber recibido lo prescrito.
"""

import json

import pytest

from holonmed.db import Database
from holonmed.facturacion import (
    CargoRepo,
    Conciliador,
    Ejecucion,
    EjecucionRepo,
    EstadoCargo,
    EstadoOrden,
    Orden,
    OrdenRepo,
    Tarifario,
    TarifarioRepo,
    TipoDescuadre,
)

VOCABULARIO = {
    "conceptos": [
        {"codigo": "P:0", "termino": "Procedimiento"},
        {"codigo": "P:1", "termino": "Preparación de citostáticos", "padre": "P:0"},
        {
            "codigo": "P:2",
            "termino": "Preparación de nutrición parenteral",
            "padre": "P:0",
        },
        {"codigo": "P:3", "termino": "Administración intravenosa", "padre": "P:0"},
    ]
}

TARIFARIO = {
    "sistema": "prueba",
    "vigente_desde": "2026-01-01",
    "prestaciones": [
        {
            "codigo": "T-001",
            "descripcion": "Preparación de citostáticos",
            "importe": 48.5,
            "equivale_a": ["P:1"],
        },
        {
            "codigo": "T-002",
            "descripcion": "Preparación de nutrición parenteral",
            "importe": 62.0,
            "equivale_a": ["P:2"],
        },
    ],
}


@pytest.fixture
def entorno(tmp_path):
    from holonmed.core.terminology import TerminologyIndex, VocabularyLoader
    from holonmed.db import GraphRepo

    (tmp_path / "vocab.json").write_text(json.dumps(VOCABULARIO), encoding="utf-8")
    (tmp_path / "tarifas.json").write_text(json.dumps(TARIFARIO), encoding="utf-8")

    db = Database(tmp_path / "prueba.db")
    VocabularyLoader(db).cargar_semilla(tmp_path / "vocab.json")
    Tarifario(db).cargar_json(tmp_path / "tarifas.json")

    index = TerminologyIndex(db, GraphRepo(db))
    ordenes, ejecuciones = OrdenRepo(db), EjecucionRepo(db)
    cargos, tarifas = CargoRepo(db), TarifarioRepo(db)
    conciliador = Conciliador(
        ordenes, ejecuciones, cargos, tarifas, sistema_tarifario="prueba"
    )
    return db, index, ordenes, ejecuciones, cargos, conciliador


def _ordenar(ordenes, index, termino, paciente="p1", **kw):
    orden = Orden(paciente_id=paciente, termino=termino, **kw)
    concepto = index.buscar_exacto(termino)
    if concepto:
        orden.concepto_id = concepto.concepto_id
        orden.codigo, orden.sistema = concepto.codigo, concepto.sistema
    orden.id = ordenes.crear(orden)
    return orden


def _ejecutar(ejecuciones, index, termino, paciente="p1", **kw):
    e = Ejecucion(paciente_id=paciente, termino=termino, **kw)
    concepto = index.buscar_exacto(termino)
    if concepto:
        e.codigo, e.sistema = concepto.codigo, concepto.sistema
    e.id = ejecuciones.registrar(e)
    return e


# --- El circuito completo ---------------------------------------------


def test_orden_mas_ejecucion_produce_cargo(entorno):
    _, index, ordenes, ejecuciones, _, conciliador = entorno
    _ordenar(ordenes, index, "Preparación de citostáticos")
    _ejecutar(ejecuciones, index, "Preparación de citostáticos", actor="farmacia")

    cuenta = conciliador.facturar("p1")
    assert len(cuenta.cargos) == 1
    assert cuenta.cargos[0].codigo_tarifario == "T-001"
    assert cuenta.cargos[0].importe == 48.5
    assert not cuenta.descuadres


def test_sin_orden_no_hay_cargo(entorno):
    """La propiedad antifraude es estructural: un cargo referencia siempre
    una orden, así que una ejecución huérfana no puede facturarse."""
    _, index, _, ejecuciones, _, conciliador = entorno
    _ejecutar(ejecuciones, index, "Preparación de citostáticos", actor="farmacia")

    cuenta = conciliador.facturar("p1")
    assert cuenta.cargos == []
    assert len(cuenta.descuadres) == 1
    assert cuenta.descuadres[0].tipo is TipoDescuadre.EJECUCION_SIN_ORDEN


def test_una_orden_sin_ejecutar_es_un_incidente_clinico(entorno):
    """No es que falte facturar: es que el paciente puede no haber
    recibido lo que se le prescribió."""
    _, index, ordenes, _, _, conciliador = entorno
    _ordenar(ordenes, index, "Preparación de nutrición parenteral")

    cuenta = conciliador.facturar("p1")
    assert cuenta.cargos == []
    descuadre = cuenta.descuadres[0]
    assert descuadre.tipo is TipoDescuadre.ORDEN_SIN_EJECUTAR
    assert descuadre.es_incidente_de_seguridad
    assert "puede no haberlo recibido" in descuadre.detalle


def test_todo_cargo_nace_propuesto(entorno):
    """Cobrarle a un paciente por algo que dedujo un modelo sin que nadie
    lo revisara sería indefendible."""
    _, index, ordenes, ejecuciones, _, conciliador = entorno
    _ordenar(ordenes, index, "Preparación de citostáticos")
    _ejecutar(ejecuciones, index, "Preparación de citostáticos")

    cuenta = conciliador.facturar("p1")
    assert all(c.estado is EstadoCargo.PROPUESTO for c in cuenta.cargos)
    assert cuenta.total_confirmado == 0.0
    assert cuenta.total_propuesto == 48.5


def test_confirmar_es_lo_que_hace_facturable_un_cargo(entorno):
    _, index, ordenes, ejecuciones, cargos, conciliador = entorno
    _ordenar(ordenes, index, "Preparación de citostáticos")
    _ejecutar(ejecuciones, index, "Preparación de citostáticos")
    cuenta = conciliador.facturar("p1")

    cargos.confirmar(cuenta.cargos[0].id)
    actualizada = conciliador.cuenta("p1")
    assert actualizada.total_confirmado == 48.5
    assert actualizada.total_propuesto == 0.0


def test_la_orden_pasa_a_cumplida_al_conciliar(entorno):
    _, index, ordenes, ejecuciones, _, conciliador = entorno
    orden = _ordenar(ordenes, index, "Preparación de citostáticos")
    assert orden.estado is EstadoOrden.PENDIENTE

    _ejecutar(ejecuciones, index, "Preparación de citostáticos")
    conciliador.conciliar("p1")
    assert ordenes.listar("p1")[0].estado is EstadoOrden.CUMPLIDA


def test_una_orden_anulada_no_reclama_ejecucion(entorno):
    _, index, ordenes, _, _, conciliador = entorno
    orden = _ordenar(ordenes, index, "Preparación de citostáticos")
    ordenes.marcar(orden.id, EstadoOrden.ANULADA)
    assert conciliador.conciliar("p1").descuadres == []


# --- Emparejamiento ----------------------------------------------------


def test_una_ejecucion_anterior_a_la_orden_no_la_cumple(entorno):
    """Tratarla como si la cumpliera ocultaría justo el caso a detectar:
    algo administrado antes de que nadie lo autorizara."""
    _, index, ordenes, ejecuciones, _, conciliador = entorno
    _ordenar(
        ordenes, index, "Preparación de citostáticos", timestamp="2026-08-12T10:00:00Z"
    )
    _ejecutar(
        ejecuciones,
        index,
        "Preparación de citostáticos",
        timestamp="2026-08-12T09:00:00Z",
    )

    resultado = conciliador.conciliar("p1")
    assert resultado.parejas == []
    assert {d.tipo for d in resultado.descuadres} == {
        TipoDescuadre.ORDEN_SIN_EJECUTAR,
        TipoDescuadre.EJECUCION_SIN_ORDEN,
    }


def test_una_ejecucion_no_cubre_dos_ordenes(entorno):
    """Dos preparaciones ordenadas y una ejecutada dejan una pendiente."""
    _, index, ordenes, ejecuciones, _, conciliador = entorno
    _ordenar(ordenes, index, "Preparación de citostáticos")
    _ordenar(ordenes, index, "Preparación de citostáticos")
    _ejecutar(ejecuciones, index, "Preparación de citostáticos")

    resultado = conciliador.conciliar("p1")
    assert len(resultado.parejas) == 1
    assert len(resultado.descuadres) == 1


def test_conciliar_es_idempotente(entorno):
    """Reejecutarlo no debe duplicar cargos."""
    _, index, ordenes, ejecuciones, _, conciliador = entorno
    _ordenar(ordenes, index, "Preparación de citostáticos")
    _ejecutar(ejecuciones, index, "Preparación de citostáticos")

    conciliador.facturar("p1")
    cuenta = conciliador.facturar("p1")
    assert len(cuenta.cargos) == 1


# --- Tarifario ---------------------------------------------------------


def test_sin_codigo_tarifario_no_se_inventa_precio(entorno):
    """Un hueco de catálogo no es motivo para facturar algo aproximado."""
    _, index, ordenes, ejecuciones, _, conciliador = entorno
    _ordenar(ordenes, index, "Administración intravenosa")  # sin tarifa
    _ejecutar(ejecuciones, index, "Administración intravenosa")

    cuenta = conciliador.facturar("p1")
    assert cuenta.cargos == []
    assert cuenta.descuadres == []  # la orden sí se cumplió


def test_se_usa_la_tarifa_vigente_en_la_fecha_de_ejecucion(entorno):
    """Una cuenta de hace un año debe reconstruirse con los precios de
    entonces, no con los de hoy."""
    db, index, ordenes, ejecuciones, _, conciliador = entorno
    TarifarioRepo(db).cargar(
        "prueba",
        [{"codigo": "T-001", "descripcion": "Preparación", "importe": 99.0}],
        vigente_desde="2026-06-01",
    )

    _ordenar(
        ordenes, index, "Preparación de citostáticos", timestamp="2026-02-01T10:00:00Z"
    )
    _ejecutar(
        ejecuciones,
        index,
        "Preparación de citostáticos",
        timestamp="2026-02-01T11:00:00Z",
    )

    cuenta = conciliador.facturar("p1")
    assert cuenta.cargos[0].importe_unitario == 48.5  # el precio de enero


def test_un_tarifario_es_otro_vocabulario(entorno):
    """Inyectar un catálogo externo no necesita mecanismo nuevo: se apoya
    en la misma tabla `mapeo` que resuelve CIE-10."""
    db, _, _, _, _, _ = entorno
    repo = TarifarioRepo(db)
    assert repo.sistemas() == {"prueba": 2}
    concepto = (
        db.conexion().execute("SELECT id FROM concepto WHERE codigo = 'P:1'").fetchone()
    )
    assert repo.codigo_para(concepto["id"], "prueba") == "T-001"


# --- El alta -----------------------------------------------------------


def test_la_cuenta_no_es_cerrable_con_cosas_pendientes(entorno):
    _, index, ordenes, ejecuciones, cargos, conciliador = entorno
    _ordenar(ordenes, index, "Preparación de citostáticos")
    _ejecutar(ejecuciones, index, "Preparación de citostáticos")
    _ordenar(ordenes, index, "Preparación de nutrición parenteral")  # sin ejecutar

    cuenta = conciliador.facturar("p1")
    assert not cuenta.cerrable  # hay un cargo propuesto y un descuadre

    cargos.confirmar(cuenta.cargos[0].id)
    assert not conciliador.cuenta("p1").cerrable  # sigue el descuadre

    _ejecutar(ejecuciones, index, "Preparación de nutrición parenteral")
    conciliador.facturar("p1")
    final = conciliador.cuenta("p1")
    for c in final.propuestos:
        cargos.confirmar(c.id)
    assert conciliador.cuenta("p1").cerrable


def test_la_cuenta_esta_al_dia_sin_recalcular(entorno):
    """El problema de las seis horas al alta no es de velocidad: es que la
    cuenta se calculaba en bloque al final."""
    _, index, ordenes, ejecuciones, _, conciliador = entorno
    _ordenar(ordenes, index, "Preparación de citostáticos")
    _ejecutar(ejecuciones, index, "Preparación de citostáticos")
    conciliador.facturar("p1")

    # Consultar no recalcula nada: sólo proyecta lo ya acumulado.
    assert conciliador.cuenta("p1").total_propuesto == 48.5
