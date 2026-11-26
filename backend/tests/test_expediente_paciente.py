"""El índice y las cuatro vistas se recuperan de la misma base tras reabrirla."""

from urllib.parse import urljoin

import yaml
from fastapi.testclient import TestClient

from holonmed.api.app import crear_app
from holonmed.config import Settings
from holonmed.models import EstadoInfon, InferenciaBayesiana, Infon, ResultadoTic


def test_expedientes_se_reabren_sin_mezclar_pacientes(tmp_path):
    ajustes = Settings(db_path=tmp_path / "expedientes.db")
    id_con_consulta = "ensayo / ñ?"
    id_vacio = "ensayo-vacio"
    texto = "O: Lipasa 900 U/L."
    lr = "Hiperlipasemia → LR 26.6"

    with TestClient(crear_app(ajustes)) as cliente:
        contexto = cliente.app.state.context
        concepto = contexto.terminologia.buscar_exacto("Hiperlipasemia")
        assert concepto is not None
        assert contexto.pacientes.crear({"id": id_vacio, "nombre": "Caso vacío"})

        class PipelineDoble:
            async def ejecutar(self, narrativa, holon, *, skill_forzada):
                return ResultadoTic(
                    paciente_id=holon.paciente_id,
                    texto_original=narrativa,
                    skill_activa=skill_forzada,
                    inferencia=InferenciaBayesiana(
                        diagnostico="Hipótesis del ensayo",
                        probabilidad_previa=5,
                        probabilidad_porcentaje=58.33,
                        evidencia_utilizada=[lr],
                    ),
                    infones=[
                        Infon(
                            texto_origen="Lipasa 900 U/L",
                            termino_propuesto="Hiperlipasemia",
                            termino="Hiperlipasemia",
                            concepto_id=concepto.concepto_id,
                            codigo=concepto.codigo,
                            sistema=concepto.sistema,
                            estado=EstadoInfon.VALIDADO,
                        )
                    ],
                )

        contexto.pipeline = PipelineDoble()
        guardado = cliente.post(
            "/api/crystallize",
            json={
                "texto": texto,
                "paciente_id": id_con_consulta,
                "skill": "acute_pancreatitis",
            },
        )
        assert guardado.status_code == 200
        tic_id = guardado.json()["tic_id"]
        evolucion = guardado.json()["evolucion"]
        assert tic_id
        assert evolucion["problemas"][0]["numero"] == 1

    with TestClient(crear_app(ajustes)) as cliente:
        indice = cliente.get("/api/pacientes/indice.yaml")
        assert indice.status_code == 200
        assert indice.headers["cache-control"] == "no-store"
        rutas = {
            entrada["id"]: entrada["ruta"]
            for entrada in yaml.safe_load(indice.text)["pacientes"]
        }
        assert set(rutas) == {id_con_consulta, id_vacio}
        assert all(ruta.startswith("./expediente.json?id=") for ruta in rutas.values())

        respuesta = cliente.get(urljoin(str(indice.url), rutas[id_con_consulta]))
        assert respuesta.status_code == 200
        assert respuesta.headers["cache-control"] == "no-store"
        ficha = respuesta.json()
        assert ficha["paciente_id"] == id_con_consulta
        assert ficha["consulta"]["tic_id"] == tic_id
        assert ficha["consulta"]["texto_original"] == texto
        assert ficha["consulta"]["inferencia"]["evidencia_utilizada"] == [lr]
        assert ficha["consulta"]["detalle"]["evolucion"] == evolucion
        assert ficha["consulta"]["infones"][0]["concepto_id"] == concepto.concepto_id
        assert [p["termino"] for p in ficha["problemas"]] == ["Hiperlipasemia"]
        assert [t["id"] for t in ficha["historia"]] == [tic_id]
        assert {n["termino"] for n in ficha["grafo"]["nodos"]} >= {"Hiperlipasemia"}

        vacio = cliente.get(urljoin(str(indice.url), rutas[id_vacio]))
        assert vacio.json() == {
            "paciente_id": id_vacio,
            "consulta": None,
            "problemas": [],
            "historia": [],
            "grafo": {"nodos": [], "aristas": []},
        }
        assert (
            cliente.get("/api/pacientes/expediente.json?id=inexistente").status_code
            == 404
        )
