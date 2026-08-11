"""Extracción de texto de informes de laboratorio en PDF.

El texto extraído entra al mismo pipeline de cristalización que una nota
dictada: los criterios de laboratorio del protocolo activo convierten los
valores numéricos en hallazgos clínicos con su código SNOMED.
"""

import logging

logger = logging.getLogger(__name__)

MAX_BYTES = 20 * 1024 * 1024  # 20 MB


class LabExtractionError(RuntimeError):
    pass


def extraer_texto_pdf(contenido: bytes, max_paginas: int = 30) -> str:
    if len(contenido) > MAX_BYTES:
        raise LabExtractionError(
            f"El archivo supera el límite de {MAX_BYTES // (1024 * 1024)} MB"
        )

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise LabExtractionError("pypdf no está instalado") from exc

    import io

    try:
        lector = PdfReader(io.BytesIO(contenido))
    except Exception as exc:  # noqa: BLE001 — PDFs corruptos son habituales
        raise LabExtractionError(f"PDF ilegible: {exc}") from exc

    if lector.is_encrypted:
        raise LabExtractionError("El PDF está protegido con contraseña")

    partes = []
    for pagina in lector.pages[:max_paginas]:
        try:
            texto: str | None = pagina.extract_text()
        except Exception:  # noqa: BLE001
            continue
        if texto:
            partes.append(texto)

    resultado = "\n".join(partes).strip()
    if not resultado:
        raise LabExtractionError(
            "No se extrajo texto. ¿Es un PDF escaneado? Requeriría OCR."
        )
    return resultado
