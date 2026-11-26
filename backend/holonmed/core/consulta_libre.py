"""Qué respuestas libres del chat no se enseñan.

La respuesta libre no pasa por ninguna capa de validación. HolonMed no emite
diagnósticos ni indicaciones terapéuticas (`DISCLAIMER.md`), así que una
respuesta que concluye sobre un caso o dice qué hacer se retiene entera: no se
recorta ni se reescribe, porque lo que quedara seguiría apoyado en ella.

**Es una lista cerrada de fórmulas, no una comprensión del texto.** Reconoce las
formas habituales de concluir y de indicar; una paráfrasis puede pasar. Y puede
retener una explicación general que use las mismas palabras: ante la duda, no se
enseña.
"""

import re
import unicodedata

CONCLUSION = "una conclusión diagnóstica"
INDICACION = "una indicación de qué hacer"

_REGLAS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (categoria, re.compile(patron))
    for categoria, patron in (
        (CONCLUSION, r"\bsugier(?:e|en|o)\b|\bsugestiv[oa]s?\b"),
        (CONCLUSION, r"\b(?:compatible|consistente)s? con\b"),
        (CONCLUSION, r"\b(?:alta|elevada|gran|baja|moderada) probabilidad de\b"),
        (CONCLUSION, r"\bprobabilidad (?:es )?(?:muy )?(?:alta|elevada) de\b"),
        (CONCLUSION, r"\bcausa (?:es )?(?:la )?mas probable\b|\blo mas probable\b"),
        (CONCLUSION, r"\b(?:es|muy) probable que\b"),
        (
            CONCLUSION,
            r"\bprobablemente (?:se trat\w+|tiene|tenga|padece|presenta|sea|es)\b",
        ),
        (CONCLUSION, r"\bdiagnosticos? diferencial(?:es)?\b"),
        (CONCLUSION, r"\bposibles? diagnosticos?\b"),
        (
            CONCLUSION,
            r"\bdiagnostico (?:mas )?(?:probable|presuntivo|sugerido|definitivo|es)\b",
        ),
        (CONCLUSION, r"\b(?:el|la|este|esta) paciente (?:tiene|padece|sufre)\b"),
        (INDICACION, r"\b(?:se recomienda|recomiendo|recomendamos|se aconseja)n?\b"),
        (
            INDICACION,
            r"\b(?:se )?(?:debe|deben|deberia|deberian|debes)(?: de)? "
            r"(?:iniciar|administrar|tomar|suspender|recibir|solicitar|realizar|"
            r"repetir|acudir|tratar)(?:se)?\b",
        ),
        (
            INDICACION,
            r"\bse (?:podria[n]? solicitar|consideraria|requiere (?:una )?"
            r"(?:evaluacion|valoracion|tratamiento|estudios?))\b",
        ),
        (
            INDICACION,
            r"\b(?:inicie|administre|suspenda|prescriba|solicite|derive)(?:se)?\b",
        ),
        (INDICACION, r"\bproximos pasos\b"),
        (INDICACION, r"\bplan (?:de manejo|terapeutico|de tratamiento)\b"),
        (INDICACION, r"\btratamiento (?:recomendado|indicado|de eleccion)\b"),
        (INDICACION, r"\bguiar el tratamiento\b"),
    )
)


def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni marcas de formato, con un solo espacio."""
    plano = unicodedata.normalize("NFKD", texto.casefold())
    plano = "".join(
        c
        for c in plano
        # Tildes y caracteres invisibles, que partirían una fórmula en dos.
        if not unicodedata.combining(c) and unicodedata.category(c) != "Cf"
    )
    return " ".join(re.sub(r"[*_`#>~]", "", plano).split())


def motivos_de_retencion(respuesta: str) -> list[str]:
    """Las categorías que obligan a retener. Vacía si ninguna fórmula aparece.

    No devuelve los fragmentos: citarlos sería enseñar la conclusión.
    """
    texto = _normalizar(respuesta)
    return list(dict.fromkeys(c for c, patron in _REGLAS if patron.search(texto)))
