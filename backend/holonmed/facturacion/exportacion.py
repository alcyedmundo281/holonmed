"""Exportación de la cuenta a los formatos que consumen otros sistemas.

Aquí el XML **sí** se gana el sitio, y por una razón distinta a la de los
prompts. En el prompt ganó la prosa porque el consumidor es un modelo de
lenguaje y se midió que las etiquetas no aportaban nada. Aquí el consumidor
es otro sistema con reglas propias: valida contra un esquema, a veces exige
firma electrónica, y no negocia el formato.

Ese es el criterio: **XML donde un tercero con esquema consume el
documento; prosa donde lo lee un modelo.**

HolonMed no conoce el esquema de ningún organismo ni de ningún hospital, y
no debería. Lo que ofrece es la estructura de datos completa y trazable, y
un formato genérico. El mapeo al esquema concreto de cada sitio —sus
nombres de etiqueta, su firma, sus claves de acceso— es una capa de
integración que se escribe una vez por centro, no algo que puedan traer
cableado desde aquí.
"""

import csv
import io
import json
import logging
from xml.etree import ElementTree as ET

from .modelos import Cuenta

logger = logging.getLogger(__name__)

FORMATOS = ("xml", "json", "csv")


def exportar(cuenta: Cuenta, formato: str = "xml", **opciones) -> str:
    if formato == "json":
        return _a_json(cuenta)
    if formato == "csv":
        return _a_csv(cuenta)
    return _a_xml(cuenta, **opciones)


def _a_xml(
    cuenta: Cuenta,
    emisor: str | None = None,
    incluir_propuestos: bool = False,
) -> str:
    """Documento genérico con la cuenta y su trazabilidad.

    Por defecto sólo salen los cargos **confirmados**: exportar un cargo
    que nadie ha revisado sería enviar a facturar algo que el sistema
    apenas propuso.

    Cada línea lleva su orden y su ejecución. No es adorno: es lo que
    permite defender el cargo ante una auditoría sin volver a la historia
    clínica.
    """
    cargos = cuenta.cargos if incluir_propuestos else cuenta.confirmados

    raiz = ET.Element("cuenta", {"version": "1.0", "moneda": cuenta.moneda})
    ET.SubElement(raiz, "paciente").text = cuenta.paciente_id
    ET.SubElement(raiz, "generada").text = cuenta.generada
    if emisor:
        ET.SubElement(raiz, "emisor").text = emisor

    lineas = ET.SubElement(raiz, "lineas")
    for c in cargos:
        linea = ET.SubElement(
            lineas,
            "linea",
            {
                "codigo": c.codigo_tarifario,
                "tarifario": c.sistema_tarifario,
                "estado": c.estado.value,
            },
        )
        ET.SubElement(linea, "descripcion").text = c.descripcion
        ET.SubElement(linea, "cantidad").text = f"{c.cantidad:g}"
        ET.SubElement(linea, "importeUnitario").text = f"{c.importe_unitario:.2f}"
        ET.SubElement(linea, "importe").text = f"{c.importe:.2f}"

        # La trazabilidad va dentro de la línea a propósito: un cargo sin
        # su orden no se puede defender, y separarlos invita a perderla.
        trazas = ET.SubElement(linea, "trazabilidad")
        if c.orden_id:
            ET.SubElement(trazas, "orden").text = str(c.orden_id)
        if c.ejecucion_id:
            ET.SubElement(trazas, "ejecucion").text = str(c.ejecucion_id)

    totales = ET.SubElement(raiz, "totales")
    ET.SubElement(totales, "confirmado").text = f"{cuenta.total_confirmado:.2f}"
    ET.SubElement(totales, "propuesto").text = f"{cuenta.total_propuesto:.2f}"

    # Los descuadres viajan con la cuenta. Son incidentes clínicos, y
    # omitirlos por ser un documento de facturación los haría invisibles
    # justo para quien puede resolverlos.
    if cuenta.descuadres:
        nodo = ET.SubElement(raiz, "descuadres")
        for d in cuenta.descuadres:
            item = ET.SubElement(nodo, "descuadre", {"tipo": d.tipo.value})
            ET.SubElement(item, "termino").text = d.termino
            ET.SubElement(item, "detalle").text = d.detalle

    ET.indent(raiz, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        raiz, encoding="unicode"
    )


def _a_json(cuenta: Cuenta) -> str:
    return json.dumps(cuenta.model_dump(mode="json"), indent=2, ensure_ascii=False)


def _a_csv(cuenta: Cuenta) -> str:
    """Plano, para los sistemas que sólo aceptan tabla."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\n")
    escritor.writerow(
        [
            "paciente",
            "codigo",
            "tarifario",
            "descripcion",
            "cantidad",
            "importe_unitario",
            "importe",
            "estado",
            "orden",
            "ejecucion",
        ]
    )
    for c in cuenta.cargos:
        escritor.writerow(
            [
                cuenta.paciente_id,
                c.codigo_tarifario,
                c.sistema_tarifario,
                c.descripcion,
                f"{c.cantidad:g}",
                f"{c.importe_unitario:.2f}",
                f"{c.importe:.2f}",
                c.estado.value,
                c.orden_id or "",
                c.ejecucion_id or "",
            ]
        )
    return salida.getvalue()
