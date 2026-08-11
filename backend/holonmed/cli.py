"""Interfaz de línea de comandos.

Permite ejercitar el pipeline sin levantar la API ni el frontend, que es
como conviene depurar un validador: entrada de texto, salida legible.

    holonmed serve
    holonmed check
    holonmed tic "Paciente con amilasa 1200 y calcio 6.8"
"""

import argparse
import asyncio
import json
import sys

from .config import get_settings


def _cmd_serve(args) -> int:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "holonmed.api.app:app",
        host=args.host or settings.api_host,
        port=args.port or settings.api_port,
        reload=args.reload,
    )
    return 0


async def _check() -> int:
    from .api.deps import AppContext

    ctx = AppContext()
    estado = ctx.estado()
    llm_ok = await ctx.llm.disponible()
    modelos = await ctx.llm.modelos_disponibles()
    settings = ctx.settings
    await ctx.cerrar()

    def marca(ok: bool) -> str:
        return "[ok]  " if ok else "[--]  "

    print("\nHolonMed — comprobación del entorno\n" + "=" * 46)

    print(marca(llm_ok) + f"Ollama en {settings.ollama_host}")
    if llm_ok:
        print(f"        modelos instalados: {', '.join(modelos) or 'ninguno'}")
        for etiqueta, modelo in (
            ("clínico", settings.model_clinical),
            ("router", settings.model_router),
        ):
            presente = any(m.split(":")[0] == modelo.split(":")[0] for m in modelos)
            print(marca(presente) + f"modelo {etiqueta}: {modelo}")
            if not presente:
                print(f"        falta: ollama pull {modelo}")
    else:
        print("        arranca Ollama con: ollama serve")

    vocab = estado["vocabulario"]
    print(marca(vocab["disponible"]) + "vocabulario clínico")
    if vocab["sistemas"]:
        for sistema, n in sorted(vocab["sistemas"].items()):
            print(f"        {sistema}: {n:,} conceptos")
    else:
        print("        carga el base: python scripts/importar_terminologia.py --semilla")

    bd = estado["base_datos"]
    print(marca(bd["conectada"]) + f"base de datos ({bd['ruta']})")
    if not bd["conectada"]:
        print(f"        {bd['error']}")
    else:
        st = bd["estadisticas"]
        print(f"        {st['pacientes']} pacientes, {st['tics']} tics, {st['infones']} infones")

    print(marca(bool(estado["skills"])) + f"skills: {', '.join(estado['skills'])}")

    listo = llm_ok and vocab["disponible"]
    print("\n" + ("Sistema operativo." if listo else "Faltan requisitos."))
    return 0 if listo else 1


async def _tic(texto: str, paciente: str, skill: str) -> int:
    from .api.deps import AppContext

    ctx = AppContext()
    holon = ctx.pacientes.obtener_o_efimero(paciente)
    holon.linea_tiempo = ctx.tics.linea_tiempo(paciente)

    resultado = await ctx.pipeline.ejecutar(texto, holon, skill_forzada=skill)
    await ctx.cerrar()

    print(f"\nProtocolo activo: {resultado.skill_activa}")
    if resultado.resumen:
        print(f"Resumen: {resultado.resumen}")

    print(f"\nInfones ({len(resultado.infones)}):")
    for infon in resultado.infones:
        codigo = f"{infon.sistema}:{infon.codigo}" if infon.codigo else "sin código"
        cie = f" · CIE-10 {infon.cie10_code}" if infon.cie10_code else ""
        print(f"  [{infon.estado.value:9}] {infon.termino}")
        print(f"              {codigo}{cie} · confianza {infon.confianza}%")
        print(f"              {infon.razon_auditoria[:100]}")

    if resultado.inferencia:
        inf = resultado.inferencia
        print(f"\nInferencia: {inf.diagnostico}")
        print(f"  previa {inf.probabilidad_previa}% → posterior {inf.probabilidad_porcentaje}%")
        print(f"  veredicto: {inf.veredicto}")
        for paso in inf.traza_logica:
            print(f"    · {paso}")
        for ev in inf.evidencia_utilizada:
            print(f"    → {ev}")
    print()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="holonmed", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    p_serve = sub.add_parser("serve", help="Arranca la API")
    p_serve.add_argument("--host")
    p_serve.add_argument("--port", type=int)
    p_serve.add_argument("--reload", action="store_true")

    sub.add_parser("check", help="Comprueba el entorno")

    p_tic = sub.add_parser("tic", help="Procesa una narrativa clínica")
    p_tic.add_argument("texto")
    p_tic.add_argument("--paciente", default="demo")
    p_tic.add_argument("--skill", default=None)

    p_skill = sub.add_parser("skills", help="Inspecciona los protocolos")
    p_skill.add_argument("--nombre", default=None)

    args = parser.parse_args(argv)

    if args.comando == "serve":
        return _cmd_serve(args)
    if args.comando == "check":
        return asyncio.run(_check())
    if args.comando == "tic":
        return asyncio.run(_tic(args.texto, args.paciente, args.skill))
    if args.comando == "skills":
        from .core import SkillManager

        gestor = SkillManager()
        if args.nombre:
            skill = gestor.cargar(args.nombre)
            if not skill:
                print(f"No existe la skill '{args.nombre}'", file=sys.stderr)
                return 1
            print(json.dumps(skill.hints_snomed(), indent=2, ensure_ascii=False))
        else:
            for nombre in gestor.listar():
                skill = gestor.cargar(nombre)
                print(f"{nombre}: {skill.descripcion} ({len(skill.hints_snomed())} hints)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
