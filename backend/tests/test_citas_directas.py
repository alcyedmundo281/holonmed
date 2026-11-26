"""`POST /api/citas`: lo que no se entiende se rechaza y no se escribe.

La ruta pasaba la fecha por un intérprete de lenguaje libre, que leía una fecha
ISO con el día y el mes cambiados, completaba lo que faltaba con el reloj y,
cuando no entendía nada, guardaba el texto como si fuera una cita. Todo el texto
es sintético.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from holonmed.api.app import crear_app
from holonmed.api.deps import AppContext, get_context
from holonmed.config import Settings

# Día 3 a propósito: con el mes, admite dos lecturas para quien las invierta.
ANIO = datetime.now().year + 1
MOTIVO = "revisión de tensión"
ESPERADA = f"{ANIO}-12-03T10:00:00"


@pytest.fixture
def entorno(tmp_path):
    ajustes = Settings(
        db_path=tmp_path / "h.db", docs_dir=tmp_path / "docs", autocargar_semilla=False
    )
    contexto = AppContext(ajustes)
    contexto.pacientes.crear({"id": "p1", "nombre": "Paciente Sintético"})

    app = crear_app(ajustes)
    app.dependency_overrides[get_context] = lambda: contexto
    with TestClient(app) as cliente:
        yield cliente, contexto
    contexto.database.cerrar()


def _pedir(cliente, **cambios):
    cuerpo = {"paciente_id": "p1", "fecha": f"{ANIO}-12-03 10:00", "motivo": MOTIVO}
    cuerpo.update(cambios)
    return cliente.post(
        "/api/citas", json={k: v for k, v in cuerpo.items() if v is not None}
    )


def _filas(ctx, tabla):
    consulta = f"SELECT * FROM {tabla}"
    return [dict(f) for f in ctx.database.conexion().execute(consulta)]


@pytest.mark.parametrize(
    "texto",
    [
        f"{ANIO}-12-03 10:00",
        f"03/12/{ANIO} 10:00",
        f"el 3 de diciembre de {ANIO} a las 10:00",
    ],
)
def test_agenda_el_dia_y_la_hora_que_dice_el_texto(entorno, texto):
    cliente, ctx = entorno

    respuesta = _pedir(cliente, fecha=texto)

    assert respuesta.status_code == 201
    assert respuesta.json()["fecha"] == ESPERADA
    assert respuesta.json()["estado"] == "agendada"
    (cita,) = _filas(ctx, "cita")
    assert cita["fecha"] == ESPERADA
    assert cita["interpretada"] == 1
    assert cita["motivo"] == MOTIVO
    # Por esta ruta nadie aprueba nada: no se inventa quién.
    assert cita["confirmada_por"] is None


def test_manana_con_hora_usa_la_hora_dicha_y_no_la_del_reloj(entorno):
    cliente, _ = entorno
    antes = datetime.now().date()

    respuesta = _pedir(cliente, fecha="mañana a las 09:30")

    fecha = datetime.fromisoformat(respuesta.json()["fecha"])
    posibles = {d + timedelta(days=1) for d in (antes, datetime.now().date())}
    assert fecha.date() in posibles
    assert (fecha.hour, fecha.minute, fecha.second) == (9, 30, 0)


@pytest.mark.parametrize(
    "texto",
    [
        "10",
        "mañana",
        "el 3 de diciembre",
        "el próximo martes",
        f"{ANIO}-12-03",
        f"31/02/{ANIO} 10:00",
        "1/01/2020 10:00",
        "texto sintético sin fecha",
        "",
    ],
)
def test_una_fecha_que_no_se_entiende_es_422_y_no_escribe(entorno, texto):
    cliente, ctx = entorno
    antes = ctx.database.conexion().total_changes

    respuesta = _pedir(cliente, fecha=texto)

    assert respuesta.status_code == 422
    assert ctx.database.conexion().total_changes == antes


def test_el_rechazo_dice_como_escribir_la_fecha(entorno):
    cliente, _ = entorno

    detalle = _pedir(cliente, fecha="el próximo martes").json()["detail"]

    assert "«el próximo martes»" in detalle
    assert "dd/mm/aaaa a las hh:mm" in detalle


@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_el_motivo_no_se_completa(entorno, motivo):
    """Antes, una cita sin motivo quedaba escrita como «Control»."""
    cliente, ctx = entorno

    assert _pedir(cliente, motivo=motivo).status_code == 422
    assert _filas(ctx, "cita") == []


def test_sin_ficha_no_se_agenda_ni_se_crea_el_paciente(entorno):
    """La cita daba de alta una ficha cuyo nombre era el identificador."""
    cliente, ctx = entorno

    respuesta = _pedir(cliente, paciente_id="sin-ficha")

    assert respuesta.status_code == 404
    assert _filas(ctx, "cita") == []
    assert [p["id"] for p in _filas(ctx, "paciente")] == ["p1"]


def test_una_escritura_que_falla_no_responde_creada(entorno, monkeypatch):
    cliente, ctx = entorno
    monkeypatch.setattr(ctx.citas, "crear", lambda _: None)

    respuesta = _pedir(cliente)

    assert respuesta.status_code == 500
    assert "No se registró nada" in respuesta.json()["detail"]
