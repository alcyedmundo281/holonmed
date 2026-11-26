"""Arranca HolonMed en modo demostración, contra LM Studio y con base separada.

    python scripts/demo.py
    python scripts/demo.py --modelo <id> --puerto 8765
    python scripts/demo.py --abrir        # abre el navegador al estar listo
    python scripts/demo.py --react --abrir # abre la app React con base persistente

En Windows basta con `demo-holonmed.bat`, en la raíz del repositorio.

Antes: arranca el servidor de LM Studio (puerto 1234) y carga el modelo
(`lms server start`, `lms load <modelo>`).

El tutorial usa una base temporal. React conserva los casos en una base de demo
del usuario, o usa una temporal con --temporal. Escucha sólo en 127.0.0.1.
"""

import argparse
import asyncio
import os
import socket
import sys
import tempfile
import threading
import time
import webbrowser
from contextlib import nullcontext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MODELO = "gemma-4-e4b-uncensored-hauhaucs-aggressive"


def directorio_react() -> Path:
    if os.name == "nt":
        return Path(os.environ["LOCALAPPDATA"]) / "HolonMed" / "demo-react"
    datos = os.environ.get("XDG_DATA_HOME")
    return (
        (Path(datos) if datos else Path.home() / ".local" / "share")
        / "holonmed"
        / "demo-react"
    )


def configurar(directorio: Path, modelo: str, lm_host: str, *, tutorial: bool) -> None:
    """Fija el entorno de la demo. Pisa lo que diga `.env` a propósito."""
    os.environ.update(
        {
            "HOLONMED_MODO_DEMO": "true" if tutorial else "false",
            "HOLONMED_LLM_BACKEND": "openai",
            "HOLONMED_OPENAI_HOST": lm_host,
            "HOLONMED_MODEL_CLINICAL": modelo,
            "HOLONMED_MODEL_ROUTER": modelo,
            "HOLONMED_DB_PATH": str(directorio / "demo.db"),
            "HOLONMED_DOCS_DIR": str(directorio / "documentos"),
        }
    )


async def modelos_servidos() -> list[str]:
    from holonmed.llm.client import OllamaClient

    async with OllamaClient() as cliente:
        return await cliente.modelos_disponibles()


def puerto_ocupado(puerto: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def abrir_cuando_responda(puerto: int, url: str) -> None:
    """Abre el navegador cuando el servidor ya escucha, no antes."""

    def esperar() -> None:
        for _ in range(120):
            if puerto_ocupado(puerto):
                webbrowser.open(url)
                return
            time.sleep(0.5)

    threading.Thread(target=esperar, daemon=True).start()


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--modelo", default=MODELO)
    parser.add_argument("--lm-host", default="http://127.0.0.1:1234")
    parser.add_argument("--puerto", type=int, default=8765)
    parser.add_argument("--react", action="store_true", help="abre la app React")
    parser.add_argument("--temporal", action="store_true", help="usa una base desechable")
    parser.add_argument("--puerto-frontend", type=int, default=5173)
    parser.add_argument("--abrir", action="store_true")
    parser.add_argument("--sin-navegador", action="store_true")
    args = parser.parse_args()
    url = f"http://localhost:{args.puerto}/tutorial"

    if not args.react and puerto_ocupado(args.puerto):
        print(
            f"No arranco: el puerto {args.puerto} ya está en uso. Puede que la demo "
            f"ya esté abierta en {url}. Ciérrala o usa --puerto.",
            file=sys.stderr,
        )
        return 1

    if args.react and not args.temporal:
        try:
            persistente = directorio_react()
            if not persistente.is_absolute():
                raise ValueError("se requiere un directorio de datos absoluto")
            persistente.mkdir(parents=True, exist_ok=True)
        except (KeyError, OSError, ValueError):
            print(
                "No se pudo preparar el almacenamiento local de la demo React.",
                file=sys.stderr,
            )
            return 1
        almacenamiento = nullcontext(str(persistente))
    else:
        almacenamiento = tempfile.TemporaryDirectory(
            prefix="holonmed-demo-", ignore_cleanup_errors=True
        )

    with almacenamiento as datos:
        configurar(Path(datos), args.modelo, args.lm_host, tutorial=not args.react)

        if args.react:
            from holonmed import lanzador

            # El navegador debe pasar por el proxy de esta sesión, incluso si
            # hay una URL de API de trabajo configurada en el entorno de Vite.
            os.environ["VITE_API_URL"] = ""
            opciones = [
                "--puerto-backend",
                str(args.puerto),
                "--puerto-frontend",
                str(args.puerto_frontend),
            ]
            if not args.abrir or args.sin_navegador:
                opciones.append("--sin-navegador")
            return lanzador.main(opciones)

        # Fallo cerrado: mejor no arrancar que descubrirlo delante del público.
        servidos = asyncio.run(modelos_servidos())
        if args.modelo not in servidos:
            print(
                f"No arranco: «{args.modelo}» no está en {args.lm_host}.\n"
                f"Modelos servidos: {', '.join(servidos) or 'ninguno'}.\n"
                "Revisa que el servidor de LM Studio esté encendido.",
                file=sys.stderr,
            )
            return 1

        import uvicorn

        print(f"\nTutorial:  {url}\nPara cerrar la demo: Ctrl+C o cierra esta ventana.\n")
        if args.abrir and not args.sin_navegador:
            abrir_cuando_responda(args.puerto, url)
        uvicorn.run("holonmed.api.app:app", host="127.0.0.1", port=args.puerto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
