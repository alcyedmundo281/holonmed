"""Generación de recetas en PDF.

Una receta es un documento legal. Este módulo no decide qué prescribir:
recibe una estructura ya revisada y la maqueta. La responsabilidad clínica
es del profesional que firma, y el pie de página lo dice explícitamente.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)

AZUL = (0.23, 0.51, 0.96)
GRIS = (0.35, 0.35, 0.35)


def _nombre_seguro(texto: str) -> str:
    """Sanea texto para usarlo en un nombre de archivo."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", texto).strip("_")[:40] or "documento"


class PrescriptionService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.directorio = Path(self.settings.docs_dir)
        self.directorio.mkdir(parents=True, exist_ok=True)

    def generar(
        self,
        items: list[dict[str, Any]],
        paciente: str,
        profesional: str = "",
        notas: str = "",
    ) -> Path | None:
        if not items:
            return None
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError:
            logger.error("reportlab no está instalado; no se pueden generar recetas")
            return None

        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = self.directorio / f"receta_{_nombre_seguro(paciente)}_{marca}.pdf"

        c = canvas.Canvas(str(ruta), pagesize=A4)
        ancho, alto = A4

        # Cabecera
        c.setFillColorRGB(*AZUL)
        c.rect(0, alto - 110, ancho, 110, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(40, alto - 60, "HolonMed")
        c.setFont("Helvetica", 10)
        c.drawString(40, alto - 80, "Receta médica")

        # Datos
        c.setFillColorRGB(0, 0, 0)
        y = alto - 145
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, f"Paciente: {paciente}")
        c.drawRightString(ancho - 40, y, datetime.now().strftime("%d/%m/%Y %H:%M"))

        y -= 45
        c.setFont("Helvetica-Bold", 20)
        c.drawString(40, y, "Rx.")
        y -= 28

        for item in items:
            if y < 140:  # salto de página antes de invadir el pie
                c.showPage()
                y = alto - 60
                c.setFillColorRGB(0, 0, 0)

            farmaco = str(item.get("farmaco") or item.get("drug") or "Fármaco")
            dosis = str(item.get("concentracion") or item.get("concentration") or "")
            indicacion = str(
                item.get("indicaciones") or item.get("instructions") or "Según criterio"
            )

            c.setFont("Helvetica-Bold", 12)
            c.drawString(60, y, f"• {farmaco} {dosis}".strip())
            y -= 16
            c.setFont("Helvetica-Oblique", 10)
            c.setFillColorRGB(*GRIS)
            c.drawString(78, y, f"Indicación: {indicacion}")
            c.setFillColorRGB(0, 0, 0)
            y -= 26

        if notas:
            y -= 10
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, "Notas:")
            y -= 14
            c.setFont("Helvetica", 10)
            for linea in notas.splitlines()[:6]:
                c.drawString(50, y, linea[:100])
                y -= 13

        # Firma y descargo
        c.setFont("Helvetica", 10)
        c.line(40, 120, 260, 120)
        c.drawString(40, 106, profesional or "Firma y sello del profesional")

        c.setFont("Helvetica-Oblique", 7)
        c.setFillColorRGB(*GRIS)
        c.drawString(
            40,
            48,
            "Documento generado con asistencia informática. Carece de validez sin la",
        )
        c.drawString(
            40,
            39,
            "firma del profesional responsable, que asume la decisión clínica.",
        )

        c.save()
        logger.info("Receta generada: %s", ruta.name)
        return ruta

    def ruta_documento(self, nombre: str) -> Path | None:
        """Resuelve un nombre de archivo dentro del directorio de documentos.

        Se normaliza y se comprueba la contención para que un nombre
        manipulado no pueda escapar del directorio.
        """
        candidato = (self.directorio / Path(nombre).name).resolve()
        base = self.directorio.resolve()
        if base not in candidato.parents or not candidato.is_file():
            return None
        return candidato
