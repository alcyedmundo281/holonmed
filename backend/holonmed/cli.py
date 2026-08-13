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


def _consola_utf8() -> None:
    """Fuerza UTF-8 en la salida estándar.

    La consola de Windows usa cp1252, que no sabe codificar ni flechas ni
    la mitad de los caracteres de una nota clínica en español. Sin esto,
    imprimir el resultado lanza UnicodeEncodeError y se pierde todo el
    trabajo del pipeline por un problema de presentación.
    """
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is not None:
            reconfigurar(encoding="utf-8", errors="replace")


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
        # La polaridad se marca porque invierte el sentido del dato: una
        # ausencia documentada resta en la inferencia en vez de sumar.
        marca = "" if infon.polaridad.value == "presente" else "  [AUSENTE]"
        derivado = "  ←derivado" if infon.derivado_de else ""
        print(f"  [{infon.estado.value:9}] {infon.termino}{marca}{derivado}")
        print(f"              {codigo}{cie} · confianza {infon.confianza}%")
        print(f"              {infon.razon_auditoria}")

    clas = resultado.clasificacion
    if clas:
        print(f"\nClasificación: {clas.nombre}")
        print(f"  {clas.satisfechos} criterios cumplidos de {clas.requiere} exigidos")
        for linea in clas.desglose():
            print(f"    · {linea}")
        if clas.cumple:
            print(f"  → CUMPLE. Trastorno acuñado: {clas.trastorno.termino}")
        else:
            estado = "alcanzable" if clas.alcanzable else "ya no alcanzable"
            print(f"  → No cumple ({estado})")
        # Un criterio sin datos no es un criterio negativo: es una
        # pregunta. Lo que falta es justo lo que hay que pedir.
        if clas.vacios:
            print("\n  Falta información sobre:")
            for v in clas.vacios:
                print(f"    ? {v.sugerencia}")

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
    _consola_utf8()
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
    p_skill.add_argument(
        "--validar",
        action="store_true",
        help="Comprueba los protocolos contra el vocabulario cargado",
    )

    args = parser.parse_args(argv)

    if args.comando == "serve":
        return _cmd_serve(args)
    if args.comando == "check":
        return asyncio.run(_check())
    if args.comando == "tic":
        return asyncio.run(_tic(args.texto, args.paciente, args.skill))
    if args.comando == "skills":
        return _skills(args)
    return 1


def _skills(args) -> int:
    from .config import get_settings
    from .core import SkillManager, TerminologyIndex
    from .db import Database, GraphRepo

    gestor = SkillManager()

    index = None
    if args.validar:
        db = Database(get_settings().db_path)
        index = TerminologyIndex(db, GraphRepo(db))
        if not index.disponible():
            print("Sin vocabulario cargado: los códigos no se comprobarán.")
            index = None

    nombres = [args.nombre] if args.nombre else gestor.listar()
    problemas_totales = 0

    for nombre in nombres:
        skill = gestor.cargar(nombre)
        if not skill:
            print(f"No existe la skill '{nombre}'", file=sys.stderr)
            return 1

        print()
        print(f"{skill.nombre}  —  {skill.titulo}  (v{skill.version})")
        print(f"  {skill.descripcion}")
        print(
            f"  {len(skill.signos)} signos · {len(skill.laboratorio)} criterios · "
            f"{len(skill.hints())} hints"
        )
        if skill.ambito_grafo:
            print(f"  ámbito de grafo: {', '.join(skill.ambito_grafo)}")
        if skill.bayes.declarado:
            print(
                f"  bayes: base {skill.bayes.probabilidad_base:.1%}, "
                f"{len(skill.bayes.factores_riesgo)} factores de riesgo"
            )

        if args.nombre and not args.validar:
            print("  hints:")
            print(json.dumps(skill.hints(), indent=4, ensure_ascii=False))

        if args.validar:
            fallos = skill.problemas(index)
            problemas_totales += len(fallos)
            if fallos:
                print(f"  {len(fallos)} problema(s):")
                for f in fallos:
                    print(f"    - {f}")
            else:
                print("  sin problemas")

    if args.validar:
        print()
        print(
            f"{problemas_totales} problema(s) en total."
            if problemas_totales
            else "Todos los protocolos son válidos."
        )
        return 1 if problemas_totales else 0
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
