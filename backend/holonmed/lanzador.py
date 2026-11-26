"""Levanta backend y frontend en esta máquina, para usarlos desde el navegador.

Lo llama `iniciar-holonmed.bat`. Comprueba todo antes de arrancar nada y, si
falta algo, se detiene diciendo qué es y cómo se arregla. No enciende, apaga
ni carga nada en LM Studio: ese servidor es del usuario.

    python -m holonmed.lanzador [--sin-navegador]
"""

import argparse
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from collections.abc import MutableMapping

from .config import RAIZ, Settings
from .core.estado_llm import diagnosticar_modelo
from .llm.client import OllamaClient

FRONTEND = RAIZ.parent / "frontend"
VITE = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"

#: La configuración de LM Studio que documenta AGENTS.md. El router usa el
#: mismo modelo, que es el único que allí se declara.
LM_STUDIO = {
    "HOLONMED_LLM_BACKEND": "openai",
    "HOLONMED_OPENAI_HOST": "http://127.0.0.1:1234",
    "HOLONMED_MODEL_CLINICAL": "medgemma-1.5-4b-it",
    "HOLONMED_MODEL_ROUTER": "medgemma-1.5-4b-it",
}

# Sin proxy: un HTTP_PROXY del sistema no debe interponerse con 127.0.0.1.
_HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Falta(RuntimeError):
    """Algo impide arrancar. El mensaje dice qué y cómo se arregla."""


def usar_lm_studio(settings: Settings, entorno: MutableMapping[str, str]) -> bool:
    """Si la configuración no apunta ya a LM Studio, la fija para este proceso.

    Con `llm_backend=openai` se respeta entera la del usuario. En otro caso
    los nombres de modelo son de Ollama y no sirven en LM Studio, así que se
    sustituyen los cuatro valores. No se escribe ningún archivo.
    """
    if settings.llm_backend == "openai":
        return False
    entorno.update(LM_STUDIO)
    return True


def puerto_ocupado(puerto: int) -> bool:
    """Mira IPv4 e IPv6: `localhost` puede resolver a cualquiera de las dos."""
    for familia, direccion in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(familia, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((direccion, puerto)) == 0:
                    return True
        except OSError:
            continue
    # Nadie contesta, pero puede estar reservado por el sistema.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", puerto))
    except OSError:
        return True
    return False


async def comprobar_modelo(settings: Settings) -> None:
    async with OllamaClient(settings) as llm:
        responde, modelos = await llm.inventario()
    diagnostico = diagnosticar_modelo(
        responde=responde,
        modelos=modelos,
        requeridos=[settings.model_clinical, settings.model_router],
        backend=settings.llm_backend,
    )
    host = settings.llm_host
    if diagnostico.estado == "sin_conexion":
        raise Falta(
            f"El servidor de modelos no responde en {host}.\n"
            "Abre LM Studio y enciende su servidor local (pestaña Developer), o ejecuta:\n"
            "    lms server start"
        )
    if diagnostico.estado == "sin_comprobar":
        raise Falta(
            f"Algo responde en {host}, pero no entrega una lista de modelos legible.\n"
            "Comprueba que en ese puerto esté el servidor de LM Studio."
        )
    if diagnostico.estado == "falta_modelo":
        ordenes = "\n".join(f"    lms load {m}" for m in diagnostico.faltantes)
        raise Falta(
            f"El servidor de {host} no ofrece: {', '.join(diagnostico.faltantes)}\n"
            f"Descarga o carga el modelo en LM Studio:\n{ordenes}\n"
            "Si quieres usar otro, ponlo en HOLONMED_MODEL_CLINICAL y\n"
            "HOLONMED_MODEL_ROUTER (backend\\.env)."
        )


def comprobar_frontend() -> str:
    """Devuelve la ruta de `node`."""
    node = shutil.which("node")
    if node is None:
        raise Falta("No encuentro Node.js. Instala Node 20 o posterior.")
    if not VITE.is_file():
        raise Falta(
            "Faltan las dependencias del frontend (frontend\\node_modules).\n"
            "En la carpeta frontend del proyecto ejecuta:\n"
            "    npm ci"
        )
    return node


def comprobar_puertos(puertos: dict[str, int]) -> None:
    ocupados = [f"{p} ({uso})" for uso, p in puertos.items() if puerto_ocupado(p)]
    if ocupados:
        raise Falta(
            f"Puerto ocupado: {', '.join(ocupados)}.\n"
            "Quizá HolonMed ya está abierto en otra ventana. Para ver quién lo usa,\n"
            "en PowerShell:\n"
            "    Get-NetTCPConnection -State Listen -LocalPort <puerto> | "
            "ForEach-Object { Get-Process -Id $_.OwningProcess }\n"
            "Ciérralo y vuelve a intentarlo."
        )


def _esperar(url: str, proceso: subprocess.Popen, nombre: str, plazo: float) -> bytes:
    limite = time.monotonic() + plazo
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            raise Falta(f"El {nombre} se cerró al arrancar. El motivo está arriba.")
        try:
            with _HTTP.open(url, timeout=10) as res:
                return res.read()
        except OSError:
            time.sleep(0.5)
    raise Falta(f"El {nombre} no respondió en {plazo:.0f} s ({url}).")


def _detener(procesos: list[subprocess.Popen]) -> None:
    for proceso in procesos:
        if proceso.poll() is None:
            proceso.terminate()
    for proceso in procesos:
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()


def arrancar(args: argparse.Namespace) -> None:
    print("Comprobando requisitos...", flush=True)
    if usar_lm_studio(Settings(), os.environ):
        print(
            "  La configuración no apunta a LM Studio: en esta ventana se usa "
            f"{LM_STUDIO['HOLONMED_OPENAI_HOST']} con {LM_STUDIO['HOLONMED_MODEL_CLINICAL']}.",
            flush=True,
        )
    settings = Settings()
    node = comprobar_frontend()
    comprobar_puertos({"backend": args.puerto_backend, "frontend": args.puerto_frontend})
    asyncio.run(comprobar_modelo(settings))

    api = f"http://127.0.0.1:{args.puerto_backend}"
    web = f"http://localhost:{args.puerto_frontend}"
    procesos: list[subprocess.Popen] = []
    try:
        print(f"Arrancando el backend en {api} ...", flush=True)
        backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "holonmed.api.app:app"]
            + ["--host", "127.0.0.1", "--port", str(args.puerto_backend)],
            cwd=RAIZ,
        )
        procesos.append(backend)
        salud = json.loads(_esperar(f"{api}/health", backend, "backend", 90))
        if not salud["operativo"]:
            raise Falta(
                "El backend arrancó pero no está operativo: "
                f"modelo «{salud['llm']['estado']}», vocabulario "
                f"{'disponible' if salud['vocabulario']['disponible'] else 'NO disponible'}.\n"
                "Para el detalle, desde backend:  python -m holonmed.cli check"
            )

        print(f"Arrancando el frontend en {web} ...", flush=True)
        # `localhost` para Vite puede ser sólo ::1; se fija la dirección que
        # se acaba de comprobar libre y a la que `localhost` también llega.
        frontend = subprocess.Popen(
            [node, str(VITE), "--host", "127.0.0.1"]
            + ["--port", str(args.puerto_frontend), "--strictPort"],
            cwd=FRONTEND,
            env={**os.environ, "HOLONMED_API_URL": api},
        )
        procesos.append(frontend)
        local = f"http://127.0.0.1:{args.puerto_frontend}"
        _esperar(f"{local}/", frontend, "frontend", 60)
        _esperar(f"{local}/health", frontend, "frontend", 30)

        print(f"\nHolonMed listo en {web}")
        print("Para cerrarlo: Ctrl+C o cierra esta ventana.\n", flush=True)
        if not args.sin_navegador and not webbrowser.open(web):
            print(f"No pude abrir el navegador. Abre {web} a mano.", flush=True)

        while all(p.poll() is None for p in procesos):
            time.sleep(1)
        caido = "backend" if backend.poll() is not None else "frontend"
        raise Falta(f"El {caido} se detuvo. El motivo está arriba.")
    finally:
        _detener(procesos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="holonmed.lanzador", description=__doc__)
    parser.add_argument("--puerto-backend", type=int, default=8000)
    parser.add_argument("--puerto-frontend", type=int, default=5173)
    parser.add_argument("--sin-navegador", action="store_true")
    args = parser.parse_args(argv)

    # `.env` y las rutas relativas se resuelven desde `backend/`.
    os.chdir(RAIZ)
    try:
        arrancar(args)
    except Falta as exc:
        print(f"\nNo se puede continuar.\n{exc}", file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        print("\nHolonMed cerrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
