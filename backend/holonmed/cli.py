"""Interfaz de línea de comandos.

Permite ejercitar el pipeline sin levantar la API ni el frontend, que es
como conviene depurar un validador: entrada de texto, salida legible.

    holonmed serve
    holonmed check
    holonmed tic "Paciente con amilasa 1200 y calcio 6.8"

`tic` imprime las tres lecturas y en el orden en que se leen: primero el
criterio contado —porque un veto retira la hipótesis y entonces no hay nada
más que decir sobre ella—, después la probabilidad y el acoplamiento, que
se leen JUNTOS y nunca uno en lugar del otro, y al final la duda, que es lo
que queda por hacer.
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


# --- La lectura semiótica, en funciones y no en `print` sueltos ------
#
# Estas tres deciden algo —cuál de las dos lecturas de Φ manda, si un veto
# calla lo que viene detrás, qué se dice cuando un factor no existe— y una
# decisión metida dentro de un `print` no se puede probar. La regla de qué
# Φ se lee ya se equivocó dos veces en este repositorio; aquí no hace falta
# reescribirla, porque `phi_legible` es una propiedad del modelo y la CLI
# habla Python. La del navegador sí tuvo que reproducirla, y por eso vive
# en un solo sitio allí también.


def _lineas_veredicto(veredicto) -> list[str]:
    """El criterio contado, con el veto primero porque retira la hipótesis."""
    if veredicto is None:
        return []

    if veredicto.veto:
        return [
            "",
            f"HIPÓTESIS RETIRADA: {veredicto.veto.hipotesis}",
            f"  {veredicto.veto.motivo}",
            "  Una exclusión absoluta no es una probabilidad baja: es una "
            "imposibilidad,",
            "  y ninguna cantidad de evidencia la contrarresta.",
        ]

    lineas = ["", f"Criterio publicado: {veredicto.nivel or 'no alcanza ningún nivel'}"]
    lineas.append(
        f"  {len(veredicto.apoyos)} apoyo(s), "
        f"{len(veredicto.banderas_rojas)} bandera(s) roja(s)"
    )
    for apoyo in veredicto.apoyos:
        lineas.append(f"    + {apoyo}")
    for bandera in veredicto.banderas_rojas:
        lineas.append(f"    ! {bandera}")
    if veredicto.fuente:
        lineas.append(f"  fuente: {veredicto.fuente}")
    return lineas


def _lineas_acoplamiento(acoplamiento, repite_indagacion: bool = True) -> list[str]:
    """Φ con sus tres factores.

    Se imprime `phi_legible` y no `phi`: para un protocolo que declara
    categorías y no cocientes `phi` vale 0 porque no hay vector ponderado
    que proyectar, y ese 0 se leería como INERCIA — una afirmación falsa
    sobre el caso, y sobre la mayor parte del índice.

    Un factor que no existe se escribe «n/d» y no «0.00». Sin ninguna
    dimensión medida no hay ángulo entre h y e, de modo que la dirección
    no vale cero: no existe.

    `repite_indagacion` en False cuando debajo va a imprimirse una
    reapertura: la reapertura hereda estas mismas preguntas y las dice con
    el contexto de por qué se preguntan, así que repetirlas aquí sólo
    alarga la salida. Sin duda no hay reapertura y las preguntas siguen
    siendo útiles —lo que queda por mirar—, de modo que ahí sí se imprimen.
    """
    if acoplamiento is None:
        return []

    ponderada = acoplamiento.cobertura is not None
    if ponderada:
        factores = (
            acoplamiento.direccion,
            acoplamiento.cobertura,
            acoplamiento.explicacion,
        )
    else:
        factores = (
            acoplamiento.direccion_categorica,
            acoplamiento.cobertura_categorica,
            acoplamiento.explicacion_categorica,
        )

    def cifra(valor) -> str:
        return "n/d" if valor is None else f"{valor:.4f}"

    lineas = [
        "",
        f"Acoplamiento (Φ): {acoplamiento.phi_legible:+.4f}  {acoplamiento.veredicto.value}",
        f"  hipótesis: {acoplamiento.hipotesis}",
        f"  lectura {'ponderada' if ponderada else 'categórica'} · "
        f"α {acoplamiento.anclaje:.4f}",
        f"  dirección {cifra(factores[0])} · cobertura {cifra(factores[1])} · "
        f"explicación {cifra(factores[2])}",
        "    (los tres se informan y no se vuelven a aplicar: ya están dentro "
        "del coseno)",
    ]

    if acoplamiento.resto_no_simbolizado:
        lineas.append(
            f"  sin explicar ({len(acoplamiento.resto_no_simbolizado)}): "
            + ", ".join(acoplamiento.resto_no_simbolizado)
        )
    if repite_indagacion:
        for pregunta in acoplamiento.indagacion:
            lineas.append(f"    ? {pregunta}")
    # El cuadrante es una frase y no un dato: va en su propia línea.
    lineas.append(f"  {acoplamiento.cuadrante}")
    return lineas


def _lineas_reapertura(reapertura) -> list[str]:
    """La duda, y lo que abre. Sólo aparece cuando hay algo que reabrir."""
    if reapertura is None:
        return []

    lineas = [
        "",
        f"LA INDAGACIÓN SE REABRE — Φ {reapertura.phi:+.4f}",
        f"  «{reapertura.hipotesis}» ha dejado de funcionar como regla de acción.",
        f"  {reapertura.motivo}",
    ]

    # `None` se dice en voz alta: callarlo dejaría suponiendo que la
    # creencia venía estable, que es justo lo que no se sabe.
    if reapertura.trayectoria is None:
        lineas.append(
            "  Sin medida anterior de esta hipótesis: no se puede decir si la "
            "creencia se rompió o si nunca arraigó."
        )
    elif reapertura.trayectoria.value == "se_rompio":
        lineas.append(
            f"  La creencia SE ROMPIÓ: venía en Φ {reapertura.phi_previo:+.4f}. "
            "Lo que la desbarató está en los hallazgos de este tic."
        )
    else:
        lineas.append(
            f"  NUNCA ARRAIGÓ: la vez anterior ya daba Φ "
            f"{reapertura.phi_previo:+.4f}. No se ha roto nada."
        )

    if reapertura.alternativa:
        lineas.append(
            f"  La competencia abductiva prefiere «{reapertura.alternativa}»."
        )
    for pregunta in reapertura.preguntas:
        lineas.append(f"    ? {pregunta}")
    return lineas


def _lineas_competencia(resultado) -> list[str]:
    """Contra qué compitió, con las perdedoras y su motivo."""
    if not resultado.competencia:
        return []

    lineas = ["", f"Competencia abductiva ({len(resultado.competencia)} candidatas):"]
    if resultado.triaje_coincide is None:
        lineas.append("  No hubo candidata admitida con la que comparar el triaje.")
    elif resultado.triaje_coincide:
        lineas.append(f"  El triaje y el grafo coinciden en {resultado.ganadora_abductiva}.")
    else:
        lineas.append(
            f"  DISCREPAN: el triaje usó {resultado.skill_activa} y el grafo "
            f"habría elegido {resultado.ganadora_abductiva}."
        )
    if resultado.aviso_competencia:
        lineas.append(f"  AVISO: {resultado.aviso_competencia}")

    for c in resultado.competencia:
        if c.vetada:
            estado = f"vetada — {c.motivo_veto}"
        elif not c.admitida:
            estado = "sin anclaje (α = 0): no compite"
        else:
            estado = c.lectura
        clave = "n/d" if c.clave is None else f"{c.clave:.4f}"
        lineas.append(f"    {clave:>8}  {c.skill}  [{estado}]")
    return lineas


async def _tic(texto: str, paciente: str, skill: str) -> int:
    from .api.deps import AppContext

    ctx = AppContext()
    holon = ctx.pacientes.obtener_o_efimero(paciente)
    holon.linea_tiempo = ctx.tics.linea_tiempo(paciente)
    holon.phi_previo = ctx.tics.phi_por_hipotesis(paciente)

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

    # El orden es el de la lectura. Un veto retira la hipótesis, así que va
    # antes que cualquier número sobre ella; después los dos ejes, que se
    # leen JUNTOS y nunca uno en lugar del otro; y la duda cierra, porque es
    # lo que queda por hacer.
    # Antes que nada: si el grafo propuso candidatas y el veto las retiró
    # todas, no hay hipótesis de la que hablar y el motivo es lo único
    # accionable que queda.
    if resultado.todas_vetadas:
        print("")
        print("NINGUNA HIPÓTESIS EN PIE")
        print(f"  {resultado.todas_vetadas}")
        print()
        return 0

    for linea in _lineas_veredicto(resultado.veredicto_declarado):
        print(linea)

    # Con un veto no se dice nada más sobre esa hipótesis: imprimir
    # «Φ 0.69 ARMONIA» debajo de «hipótesis retirada» sería la
    # contradicción que Φ existe justo para delatar.
    vetada = bool(
        resultado.veredicto_declarado and resultado.veredicto_declarado.veto
    )
    if not vetada:
        if resultado.inferencia:
            inf = resultado.inferencia
            print(f"\nInferencia: {inf.diagnostico}")
            print(f"  previa {inf.probabilidad_previa}% → posterior {inf.probabilidad_porcentaje}%")
            print(f"  veredicto: {inf.veredicto}")
            for paso in inf.traza_logica:
                print(f"    · {paso}")
            for ev in inf.evidencia_utilizada:
                print(f"    → {ev}")

        for bloque in (
            _lineas_acoplamiento(
                resultado.acoplamiento, resultado.reapertura is None
            ),
            _lineas_reapertura(resultado.reapertura),
            _lineas_competencia(resultado),
        ):
            for linea in bloque:
                print(linea)

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

    p_cuenta = sub.add_parser("cuenta", help="Cuenta y conciliación de un paciente")
    p_cuenta.add_argument("paciente")
    p_cuenta.add_argument(
        "--calcular",
        action="store_true",
        help="Deriva cargos de las parejas conciliadas antes de mostrar",
    )

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
    if args.comando == "cuenta":
        return _cuenta(args)
    if args.comando == "skills":
        return _skills(args)
    return 1


def _cuenta(args) -> int:
    from .api.deps import AppContext

    ctx = AppContext()
    cuenta = (
        ctx.conciliador.facturar(args.paciente)
        if args.calcular
        else ctx.conciliador.cuenta(args.paciente)
    )

    print()
    print(f"Cuenta de {args.paciente}   [{ctx.settings.sistema_tarifario}]")
    print("=" * 66)

    if cuenta.cargos:
        print()
        for c in cuenta.cargos:
            marca = {"propuesto": "?", "confirmado": "+", "anulado": "-"}[c.estado.value]
            print(f"  {marca} {c.descripcion[:44]:46} {c.cantidad:>4g} x {c.importe_unitario:>8.2f} = {c.importe:>9.2f}")
            print(f"      {c.sistema_tarifario}:{c.codigo_tarifario}  orden {c.orden_id}")
    else:
        print("\n  Sin cargos.")

    print()
    print(f"  Confirmado           {cuenta.total_confirmado:>9.2f} {cuenta.moneda}")
    print(f"  Pendiente de revisar {cuenta.total_propuesto:>9.2f} {cuenta.moneda}")

    if cuenta.descuadres:
        # Estos no son problemas de facturación. Una orden sin ejecutar
        # significa que el paciente no recibió lo prescrito.
        print(f"\n  DESCUADRES ({len(cuenta.descuadres)}) — revisar antes del alta:")
        for d in cuenta.descuadres:
            etiqueta = (
                "orden sin ejecutar"
                if d.tipo.value == "orden_sin_ejecutar"
                else "ejecución sin orden"
            )
            print(f"    ! [{etiqueta:19}] {d.termino}")
            print(f"      {d.detalle}")

    print()
    if cuenta.cerrable:
        print("  Cuenta cerrable: nada pendiente.")
    else:
        pend = []
        if cuenta.propuestos:
            pend.append(f"{len(cuenta.propuestos)} cargo(s) por confirmar")
        if cuenta.descuadres:
            pend.append(f"{len(cuenta.descuadres)} descuadre(s)")
        print(f"  NO cerrable: {', '.join(pend)}.")
    print()
    return 0


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
