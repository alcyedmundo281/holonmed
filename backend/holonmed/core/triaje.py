"""Triaje clínico determinista basado en criterios ontológicos de consenso.

Este módulo sustituye la selección de protocolo por prompt ("inteligencia") por
una evaluación determinista basada en las construcciones ontológicas de
medsemiotics-db y las skills de HolonMed.

A partir de la lista de problemas del paciente (conceptos clínicos validados,
signos, síntomas, hallazgos de laboratorio o exploratorios), el motor consulta
los criterios diagnósticos consensuados por expertos (Atlanta, MDS, Centor,
McIsaac, Wells, etc.) consignados en las fichas ontológicas y sustentados
en la literatura médica con sus respectivos PMID.

Los problemas se agrupan bajo las construcciones diagnósticas correspondientes:
- Cuántos y cuáles criterios se satisfacen (satisfechos vs. requeridos).
- Núcleo motor o clínico obligatorio (p. ej. bradicinesia en Parkinson).
- Tupla bayesiana de Weed (manifestación, prueba sensible, prueba específica).
- Escalas clínicas validadas y reglas de predicción clínica.
- Trazabilidad y procedencia completa: fuente del consenso y PMID.
"""

from __future__ import annotations

import logging
import math
import os
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from ..models import AgrupacionDiagnostica, Infon, Polaridad, ProblemaAgrupado

if TYPE_CHECKING:
    from .skills import SkillManager

logger = logging.getLogger(__name__)

# Mapa conocido de mapeo entre ID de condición y nombres de skills en HolonMed
MAPA_CONDICION_SKILL = {
    "HM:6040": "acute_pancreatitis",
    "HM:6007": "sindrome_coronario_agudo",
    "HM:6044": "tromboembolia_pulmonar",
    "HM:6016": "embarazo_ectopico",
    "HM:6017": "conjuntivitis_bacteriana",
    "HM:6018": "apnea_obstructiva_del_sueno",
    "HM:6015": "enfermedad_de_parkinson",
    "HM:6009": "faringitis_estreptococica",
    "HM:6004": "meningitis_aguda",
    "HM:6043": "apendicitis_aguda",
    "HM:6042": "colecistitis_aguda",
    "HM:6010": "sincope_cardiaco",
    "HM:6008": "hipovolemia",
    "HM:6011": "infeccion_precoz_por_vih",
    "HM:6012": "artrosis_de_cadera",
    "HM:6030": "infarto_agudo_de_miocardio",
    "HM:6035": "trombosis_venosa_profunda",
    "HM:6037": "sobrecarga_de_volumen",
}

MAPA_SKILL_CONDICION = {v: k for k, v in MAPA_CONDICION_SKILL.items()}


def _normalizar(texto: str) -> str:
    """Normaliza texto para comparación eliminando acentos, mayúsculas y signos."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    # Limpiar puntuación básica para comparar términos clínicos
    texto = re.sub(r"[^\w\s]", " ", texto)
    return " ".join(texto.lower().strip().split())


def _extraer_pmid(texto: str) -> str | None:
    """Extrae el primer PMID numérico de una referencia o cita textual."""
    if not texto:
        return None
    m = re.search(r"pmid[:\s]+(\d+)", texto, re.IGNORECASE)
    return m.group(1) if m else None


def buscar_ruta_medsemiotics() -> Path | None:
    """Localiza el repositorio medsemiotics-db en el entorno."""
    env_dir = os.environ.get("HOLONMED_MEDSEMIOTICS_DIR")
    if env_dir and Path(env_dir).is_dir():
        return Path(env_dir)

    # Rutas relativas habituales en el workspace de trabajo
    # holonmed/backend/holonmed/core/triaje.py -> parents[3] es la raíz donde conviven repos
    candidato = Path(__file__).resolve().parents[3] / "medsemiotics-db"
    if candidato.is_dir():
        return candidato

    for p in Path(__file__).resolve().parents:
        if (p / "medsemiotics-db").is_dir():
            return p / "medsemiotics-db"

    return None


@dataclass
class ItemCriterio:
    """Un componente o criterio elemental dentro de una construcción diagnóstica."""

    nombre: str
    rol: str = "apoyo"
    conceptos: list[str] = field(default_factory=list)
    terminos_referencia: list[str] = field(default_factory=list)
    lr_positivo: float | None = None
    lr_negativo: float | None = None
    ref_pmid: str | None = None
    nota: str = ""


@dataclass
class ConstruccionDiagnostica:
    """Construcción ontológica diagnóstica con criterios de consenso."""

    condicion_id: str
    termino: str
    sinonimos: list[str] = field(default_factory=list)
    codigos: dict[str, str] = field(default_factory=dict)
    skill_nombre: str | None = None
    tipo_criterio: str = "clasificacion"
    consenso_nombre: str = ""
    fuente: str = ""
    pmid: str | None = None
    requiere: int = 1
    items: list[ItemCriterio] = field(default_factory=list)
    nucleo_requerido: list[str] = field(default_factory=list)
    nucleo_al_menos_uno: list[str] = field(default_factory=list)


@dataclass
class ProblemaClinico:
    """Representación normalizada de un problema clínico del paciente."""

    termino: str
    codigo: str | None = None
    sistema: str | None = None
    polaridad: Polaridad = Polaridad.PRESENTE
    valor: float | None = None
    unidad: str | None = None

    @classmethod
    def desde(cls, origen: Any) -> ProblemaClinico:
        if isinstance(origen, Infon):
            return cls(
                termino=origen.termino,
                codigo=origen.codigo,
                sistema=origen.sistema,
                polaridad=origen.polaridad,
                valor=origen.valor,
                unidad=origen.unidad,
            )
        if isinstance(origen, dict):
            pol = origen.get("polaridad", Polaridad.PRESENTE)
            if isinstance(pol, str):
                pol_enum = (
                    Polaridad.PRESENTE
                    if pol.lower() in ("presente", "true")
                    else Polaridad.AUSENTE
                )
            elif isinstance(pol, bool):
                pol_enum = Polaridad.PRESENTE if pol else Polaridad.AUSENTE
            else:
                pol_enum = Polaridad.PRESENTE
            return cls(
                termino=str(origen.get("termino") or origen.get("nombre") or ""),
                codigo=str(origen.get("codigo")) if origen.get("codigo") else None,
                sistema=origen.get("sistema"),
                polaridad=pol_enum,
                valor=origen.get("valor"),
                unidad=origen.get("unidad"),
            )
        texto = str(origen).strip()
        codigo = texto if texto.startswith("HM:") else None
        return cls(termino=texto, codigo=codigo, polaridad=Polaridad.PRESENTE)


class TriajeOntologico:
    """Motor de triaje ontológico basado en criterios de consenso de medsemiotics-db y skills."""

    def __init__(
        self,
        ruta_medsemiotics: Path | None = None,
        skills_manager: SkillManager | None = None,
    ):
        self.ruta_medsemiotics = ruta_medsemiotics or buscar_ruta_medsemiotics()
        self.skills_manager = skills_manager
        self._conceptos_cache: dict[str, dict[str, Any]] | None = None
        self._construcciones_cache: list[ConstruccionDiagnostica] | None = None

    def cargar_conceptos(self) -> dict[str, dict[str, Any]]:
        """Carga y cachea los conceptos de medsemiotics-db/conceptos."""
        if self._conceptos_cache is not None:
            return self._conceptos_cache

        conceptos: dict[str, dict[str, Any]] = {}
        if self.ruta_medsemiotics and (self.ruta_medsemiotics / "conceptos").is_dir():
            for archivo in (self.ruta_medsemiotics / "conceptos").glob("*.yaml"):
                try:
                    datos = yaml.safe_load(archivo.read_text(encoding="utf-8")) or {}
                    cid = datos.get("id")
                    if cid:
                        cid_str = str(cid).strip()
                        info = {
                            "id": cid_str,
                            "termino": str(datos.get("termino") or ""),
                            "sinonimos": datos.get("sinonimos") or [],
                            "codigos": datos.get("codigos") or {},
                        }
                        conceptos[cid_str] = info
                        # Alias sin dos puntos ("HM0202")
                        conceptos[cid_str.replace(":", "")] = info
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Error leyendo concepto en %s: %s", archivo.name, exc)

        self._conceptos_cache = conceptos
        return conceptos

    def cargar_construcciones(self) -> list[ConstruccionDiagnostica]:
        """Construye las entidades ontológicas con sus criterios diagnósticos de consenso."""
        if self._construcciones_cache is not None:
            return self._construcciones_cache

        conceptos = self.cargar_conceptos()
        construcciones: list[ConstruccionDiagnostica] = []
        condiciones_vistas: set[str] = set()

        # 1. Cargar desde las skills activas en HolonMed (tienen frontmatter validado)
        if self.skills_manager:
            for nombre_skill in self.skills_manager.listar():
                skill = self.skills_manager.cargar(nombre_skill)
                if not skill:
                    continue

                cond_id = ""
                cond_codigos = skill.condicion.get("codigos") or {}
                if "holonmed" in cond_codigos:
                    cond_id = str(cond_codigos["holonmed"])
                elif skill.condicion.get("id"):
                    cond_id = str(skill.condicion["id"])
                elif nombre_skill in MAPA_SKILL_CONDICION:
                    cond_id = MAPA_SKILL_CONDICION[nombre_skill]

                cond_nombre = str(skill.condicion.get("nombre") or skill.titulo).strip()

                # Criterios de clasificación (p. ej. Atlanta 2012 para pancreatitis)
                if skill.clasificacion.declarada:
                    clas = skill.clasificacion
                    pmid = _extraer_pmid(clas.fuente)
                    items: list[ItemCriterio] = []
                    for crit in clas.criterios:
                        ref_terms = [crit.nombre]
                        # Expandir términos de los códigos citados en satisface_si
                        for c in crit.satisface_si:
                            cinfo = conceptos.get(c) or conceptos.get(c.replace(":", ""))
                            if cinfo:
                                ref_terms.append(cinfo["termino"])
                                ref_terms.extend(cinfo.get("sinonimos", []))

                        items.append(
                            ItemCriterio(
                                nombre=crit.nombre,
                                rol=crit.rol,
                                conceptos=list(crit.satisface_si),
                                terminos_referencia=ref_terms,
                                ref_pmid=pmid,
                            )
                        )

                    c_diag = ConstruccionDiagnostica(
                        condicion_id=cond_id or f"SKILL:{nombre_skill}",
                        termino=cond_nombre,
                        skill_nombre=nombre_skill,
                        tipo_criterio="clasificacion",
                        consenso_nombre=clas.nombre,
                        fuente=clas.fuente,
                        pmid=pmid,
                        requiere=clas.requiere,
                        items=items,
                    )
                    construcciones.append(c_diag)
                    if cond_id:
                        condiciones_vistas.add(cond_id)

                # Criterios de núcleo (p. ej. MDS 2015 para Parkinson)
                if skill.nucleo.declarado:
                    nuc = skill.nucleo
                    pmid_nuc = _extraer_pmid(nuc.fuente)
                    items_nuc: list[ItemCriterio] = []
                    for req in nuc.requiere:
                        cinfo = conceptos.get(req) or conceptos.get(req.replace(":", ""))
                        t_ref = [req]
                        if cinfo:
                            t_ref.append(cinfo["termino"])
                            t_ref.extend(cinfo.get("sinonimos", []))
                        items_nuc.append(
                            ItemCriterio(
                                nombre=cinfo["termino"] if cinfo else req,
                                rol="nucleo",
                                conceptos=[req] if req.startswith("HM:") else [],
                                terminos_referencia=t_ref,
                                ref_pmid=pmid_nuc,
                            )
                        )

                    for alt in nuc.y_al_menos_uno_de:
                        cinfo = conceptos.get(alt) or conceptos.get(alt.replace(":", ""))
                        t_ref = [alt]
                        if cinfo:
                            t_ref.append(cinfo["termino"])
                            t_ref.extend(cinfo.get("sinonimos", []))
                        items_nuc.append(
                            ItemCriterio(
                                nombre=cinfo["termino"] if cinfo else alt,
                                rol="nucleo",
                                conceptos=[alt] if alt.startswith("HM:") else [],
                                terminos_referencia=t_ref,
                                ref_pmid=pmid_nuc,
                            )
                        )

                    c_diag = ConstruccionDiagnostica(
                        condicion_id=cond_id or f"SKILL:{nombre_skill}",
                        termino=cond_nombre,
                        skill_nombre=nombre_skill,
                        tipo_criterio="nucleo",
                        consenso_nombre="Criterios diagnósticos de consenso (Núcleo)",
                        fuente=nuc.fuente,
                        pmid=pmid_nuc,
                        requiere=len(nuc.requiere) + (1 if nuc.y_al_menos_uno_de else 0),
                        items=items_nuc,
                        nucleo_requerido=list(nuc.requiere),
                        nucleo_al_menos_uno=list(nuc.y_al_menos_uno_de),
                    )
                    construcciones.append(c_diag)
                    if cond_id:
                        condiciones_vistas.add(cond_id)

                # Si no tiene clasificación ni núcleo pero declara signos con roles y LR
                if (
                    not skill.clasificacion.declarada
                    and not skill.nucleo.declarado
                    and skill.signos
                ):
                    items_signos: list[ItemCriterio] = []
                    pmids_encontrados: list[str] = []
                    for signo in skill.signos:
                        pmid_s = _extraer_pmid(signo.fuente)
                        if pmid_s:
                            pmids_encontrados.append(pmid_s)
                        t_ref = [signo.nombre]
                        c_list = []
                        for s_cod in signo.codigos.values():
                            c_list.append(s_cod)
                            cinfo = conceptos.get(s_cod) or conceptos.get(
                                s_cod.replace(":", "")
                            )
                            if cinfo:
                                t_ref.append(cinfo["termino"])
                                t_ref.extend(cinfo.get("sinonimos", []))

                        items_signos.append(
                            ItemCriterio(
                                nombre=signo.nombre,
                                rol=signo.rol,
                                conceptos=c_list,
                                terminos_referencia=t_ref,
                                lr_positivo=signo.lr,
                                lr_negativo=signo.lr_negativo,
                                ref_pmid=pmid_s,
                                nota=signo.fuente,
                            )
                        )

                    fuente_gral = (
                        items_signos[0].nota
                        if items_signos and items_signos[0].nota
                        else skill.descripcion
                    )
                    pmid_gral = (
                        pmids_encontrados[0]
                        if pmids_encontrados
                        else _extraer_pmid(fuente_gral)
                    )

                    c_diag = ConstruccionDiagnostica(
                        condicion_id=cond_id or f"SKILL:{nombre_skill}",
                        termino=cond_nombre,
                        skill_nombre=nombre_skill,
                        tipo_criterio="tupla",
                        consenso_nombre=f"Construcción bayesiana de {cond_nombre}",
                        fuente=fuente_gral,
                        pmid=pmid_gral,
                        requiere=2,
                        items=items_signos,
                    )
                    construcciones.append(c_diag)
                    if cond_id:
                        condiciones_vistas.add(cond_id)

        # 2. Cargar desde medsemiotics-db/condiciones/*.yaml
        if self.ruta_medsemiotics and (self.ruta_medsemiotics / "condiciones").is_dir():
            for archivo in sorted(
                (self.ruta_medsemiotics / "condiciones").glob("*.yaml")
            ):
                try:
                    datos = yaml.safe_load(archivo.read_text(encoding="utf-8")) or {}
                    cid = datos.get("id")
                    if not cid:
                        continue
                    cid_str = str(cid).strip()
                    nombre_cond = str(datos.get("termino") or archivo.stem)
                    sinonimos = datos.get("sinonimos") or []
                    codigos = datos.get("codigos") or {}
                    proc = datos.get("procedencia") or {}
                    fuente_proc = (
                        str(proc.get("fuente") or "") if isinstance(proc, dict) else ""
                    )
                    skill_asoc = MAPA_CONDICION_SKILL.get(cid_str)

                    # a) Núcleo obligatorio (ej. HM:6015 Parkinson)
                    if "nucleo" in datos and cid_str not in condiciones_vistas:
                        nuc_data = datos["nucleo"]
                        ref_str = str(nuc_data.get("ref") or fuente_proc)
                        pmid_nuc = _extraer_pmid(ref_str)
                        req_list = nuc_data.get("requiere") or []
                        alt_list = nuc_data.get("y_al_menos_uno_de") or []

                        items_nuc = []
                        for req in req_list:
                            cinfo = conceptos.get(req) or conceptos.get(
                                req.replace(":", "")
                            )
                            t_ref = [req]
                            nom = req
                            if cinfo:
                                nom = cinfo["termino"]
                                t_ref.append(cinfo["termino"])
                                t_ref.extend(cinfo.get("sinonimos", []))
                            items_nuc.append(
                                ItemCriterio(
                                    nombre=nom,
                                    rol="nucleo",
                                    conceptos=[req],
                                    terminos_referencia=t_ref,
                                    ref_pmid=pmid_nuc,
                                )
                            )

                        for alt in alt_list:
                            cinfo = conceptos.get(alt) or conceptos.get(
                                alt.replace(":", "")
                            )
                            t_ref = [alt]
                            nom = alt
                            if cinfo:
                                nom = cinfo["termino"]
                                t_ref.append(cinfo["termino"])
                                t_ref.extend(cinfo.get("sinonimos", []))
                            items_nuc.append(
                                ItemCriterio(
                                    nombre=nom,
                                    rol="nucleo",
                                    conceptos=[alt],
                                    terminos_referencia=t_ref,
                                    ref_pmid=pmid_nuc,
                                )
                            )

                        construcciones.append(
                            ConstruccionDiagnostica(
                                condicion_id=cid_str,
                                termino=nombre_cond,
                                sinonimos=sinonimos,
                                codigos=codigos,
                                skill_nombre=skill_asoc,
                                tipo_criterio="nucleo",
                                consenso_nombre="Criterios clínicos de consenso (Núcleo)",
                                fuente=ref_str or fuente_proc,
                                pmid=pmid_nuc,
                                requiere=len(req_list) + (1 if alt_list else 0),
                                items=items_nuc,
                                nucleo_requerido=req_list,
                                nucleo_al_menos_uno=alt_list,
                            )
                        )
                        condiciones_vistas.add(cid_str)

                    # b) Escalas diagnósticas declaradas (ej. Centor, McIsaac, HEART, Wells)
                    for esc in datos.get("escalas") or []:
                        esc_nom = str(esc.get("nombre") or "Escala de consenso")
                        tramos = esc.get("tramos") or []
                        pmids_esc: list[str] = []
                        for tramo in tramos:
                            pmid_t = _extraer_pmid(str(tramo.get("ref") or ""))
                            if pmid_t:
                                pmids_esc.append(pmid_t)
                        pmid_final = (
                            pmids_esc[0]
                            if pmids_esc
                            else _extraer_pmid(
                                str(esc.get("componentes_declarados") or "")
                            )
                        )

                        # Parsear componentes declarados
                        comp_decl = str(esc.get("componentes_declarados") or "")
                        items_esc: list[ItemCriterio] = []

                        # Signos de la condición asociados
                        for s_data in datos.get("signos") or []:
                            cid_s = s_data.get("concepto")
                            if not cid_s:
                                continue
                            cinfo = conceptos.get(cid_s) or conceptos.get(
                                str(cid_s).replace(":", "")
                            )
                            t_ref = [str(cid_s)]
                            nom_s = str(cid_s)
                            if cinfo:
                                nom_s = cinfo["termino"]
                                t_ref.append(cinfo["termino"])
                                t_ref.extend(cinfo.get("sinonimos", []))

                            lr_pos = (
                                s_data.get("lr_positivo", {}).get("valor")
                                if isinstance(s_data.get("lr_positivo"), dict)
                                else None
                            )
                            lr_neg = (
                                s_data.get("lr_negativo", {}).get("valor")
                                if isinstance(s_data.get("lr_negativo"), dict)
                                else None
                            )
                            ref_pmid_s = None
                            if isinstance(s_data.get("lr_positivo"), dict):
                                ref_pmid_s = _extraer_pmid(
                                    str(s_data["lr_positivo"].get("ref") or "")
                                )

                            items_esc.append(
                                ItemCriterio(
                                    nombre=nom_s,
                                    rol=s_data.get("rol", "apoyo"),
                                    conceptos=[str(cid_s)],
                                    terminos_referencia=t_ref,
                                    lr_positivo=lr_pos,
                                    lr_negativo=lr_neg,
                                    ref_pmid=ref_pmid_s or pmid_final,
                                    nota=str(s_data.get("decision") or ""),
                                )
                            )

                        construcciones.append(
                            ConstruccionDiagnostica(
                                condicion_id=cid_str,
                                termino=nombre_cond,
                                sinonimos=sinonimos,
                                codigos=codigos,
                                skill_nombre=skill_asoc,
                                tipo_criterio="escala",
                                consenso_nombre=esc_nom,
                                fuente=comp_decl or fuente_proc,
                                pmid=pmid_final or _extraer_pmid(fuente_proc),
                                requiere=2,
                                items=items_esc,
                            )
                        )
                        condiciones_vistas.add(cid_str)

                    # c) Si no ha entrado aún, registrar su construcción bayesiana con signos y PMID
                    if cid_str not in condiciones_vistas and datos.get("signos"):
                        items_signos = []
                        pmids_cond = []
                        for s_data in datos.get("signos") or []:
                            cid_s = s_data.get("concepto")
                            if not cid_s:
                                continue
                            cinfo = conceptos.get(cid_s) or conceptos.get(
                                str(cid_s).replace(":", "")
                            )
                            t_ref = [str(cid_s)]
                            nom_s = str(cid_s)
                            if cinfo:
                                nom_s = cinfo["termino"]
                                t_ref.append(cinfo["termino"])
                                t_ref.extend(cinfo.get("sinonimos", []))

                            lr_pos = (
                                s_data.get("lr_positivo", {}).get("valor")
                                if isinstance(s_data.get("lr_positivo"), dict)
                                else None
                            )
                            lr_neg = (
                                s_data.get("lr_negativo", {}).get("valor")
                                if isinstance(s_data.get("lr_negativo"), dict)
                                else None
                            )
                            ref_pmid_s = None
                            if isinstance(s_data.get("lr_positivo"), dict):
                                ref_pmid_s = _extraer_pmid(
                                    str(s_data["lr_positivo"].get("ref") or "")
                                )
                            elif isinstance(s_data.get("lr_negativo"), dict):
                                ref_pmid_s = _extraer_pmid(
                                    str(s_data["lr_negativo"].get("ref") or "")
                                )
                            if ref_pmid_s:
                                pmids_cond.append(ref_pmid_s)

                            items_signos.append(
                                ItemCriterio(
                                    nombre=nom_s,
                                    rol=s_data.get("rol", "apoyo"),
                                    conceptos=[str(cid_s)],
                                    terminos_referencia=t_ref,
                                    lr_positivo=lr_pos,
                                    lr_negativo=lr_neg,
                                    ref_pmid=ref_pmid_s,
                                    nota=str(s_data.get("decision") or ""),
                                )
                            )

                        pmid_gral = (
                            pmids_cond[0] if pmids_cond else _extraer_pmid(fuente_proc)
                        )
                        c_diag = ConstruccionDiagnostica(
                            condicion_id=cid_str,
                            termino=nombre_cond,
                            sinonimos=sinonimos,
                            codigos=codigos,
                            skill_nombre=skill_asoc,
                            tipo_criterio="tupla",
                            consenso_nombre=f"Criterios de {nombre_cond}",
                            fuente=fuente_proc
                            or str(datos.get("conclusion_de_la_fuente") or ""),
                            pmid=pmid_gral,
                            requiere=2,
                            items=items_signos,
                        )
                        construcciones.append(c_diag)
                        condiciones_vistas.add(cid_str)

                except Exception as exc:  # noqa: BLE001
                    logger.debug("Error leyendo condición en %s: %s", archivo.name, exc)

        self._construcciones_cache = construcciones
        return construcciones

    def _coincide(
        self,
        problema: ProblemaClinico,
        item: ItemCriterio,
        conceptos: dict[str, dict[str, Any]],
    ) -> bool:
        """Determina si un problema clínico satisface un ítem de criterio."""
        # 1. Comparación por código (HM:xxxx o SNOMED)
        if problema.codigo:
            p_cod = problema.codigo.strip()
            for c in item.conceptos:
                if p_cod == c or p_cod.replace(":", "") == c.replace(":", ""):
                    return True

        # 2. Comparación textual normalizada
        norm_prob = _normalizar(problema.termino)
        if not norm_prob:
            return False

        norm_item = _normalizar(item.nombre)
        if norm_prob == norm_item or norm_item in norm_prob or norm_prob in norm_item:
            return True

        for ref_term in item.terminos_referencia:
            norm_ref = _normalizar(ref_term)
            if norm_ref and (
                norm_prob == norm_ref or norm_ref in norm_prob or norm_prob in norm_ref
            ):
                return True

        # 3. Consulta de sinónimos del concepto en medsemiotics-db
        for cid in item.conceptos:
            cinfo = conceptos.get(cid) or conceptos.get(cid.replace(":", ""))
            if cinfo:
                norm_t = _normalizar(cinfo.get("termino", ""))
                if norm_t and (
                    norm_prob == norm_t or norm_t in norm_prob or norm_prob in norm_t
                ):
                    return True
                for sin in cinfo.get("sinonimos", []):
                    norm_sin = _normalizar(sin)
                    if norm_sin and (
                        norm_prob == norm_sin
                        or norm_sin in norm_prob
                        or norm_prob in norm_sin
                    ):
                        return True

        return False

    def agrupar_problemas(
        self, problemas_o_texto: Sequence[Any] | str
    ) -> list[AgrupacionDiagnostica]:
        """Agrupa la lista de problemas contra los criterios diagnósticos ontológicos."""
        conceptos = self.cargar_conceptos()
        construcciones = self.cargar_construcciones()

        # Convertir a lista de ProblemaClinico
        problemas: list[ProblemaClinico] = []
        if isinstance(problemas_o_texto, str):
            # Texto libre: extraer ocurrencias deterministas de conceptos conocidos
            problemas = self._extraer_problemas_de_texto(
                problemas_o_texto, construcciones, conceptos
            )
        else:
            for p in problemas_o_texto:
                problemas.append(ProblemaClinico.desde(p))

        # Sólo los problemas presentes o afirmativos satisfacen criterios
        presentes = [p for p in problemas if p.polaridad is Polaridad.PRESENTE]
        if not presentes:
            return []

        agrupaciones: list[AgrupacionDiagnostica] = []

        for constr in construcciones:
            problemas_agrupados: list[ProblemaAgrupado] = []
            items_satisfechos_nombres: set[str] = set()

            for item in constr.items:
                coincidentes = [
                    p for p in presentes if self._coincide(p, item, conceptos)
                ]
                if coincidentes:
                    items_satisfechos_nombres.add(item.nombre)
                    for p in coincidentes:
                        problemas_agrupados.append(
                            ProblemaAgrupado(
                                termino=p.termino,
                                codigo=p.codigo,
                                criterio_nombre=item.nombre,
                                rol=item.rol,
                                lr_positivo=item.lr_positivo,
                                lr_negativo=item.lr_negativo,
                                ref_pmid=item.ref_pmid or constr.pmid,
                            )
                        )

            if not problemas_agrupados:
                continue

            # Evaluar cumplimiento del criterio
            cumplido = False
            estado = "SOSPECHA"

            if constr.tipo_criterio == "nucleo":
                # Comprobar si los obligatorios están todos y al menos uno de los alternativos
                req_ok = True
                for req in constr.nucleo_requerido:
                    req_matched = any(
                        p
                        for p in presentes
                        if self._coincide(
                            p, ItemCriterio(nombre=req, conceptos=[req]), conceptos
                        )
                    )
                    if not req_matched:
                        req_ok = False
                        break

                alt_ok = True
                if constr.nucleo_al_menos_uno:
                    alt_ok = any(
                        p
                        for p in presentes
                        for alt in constr.nucleo_al_menos_uno
                        if self._coincide(
                            p, ItemCriterio(nombre=alt, conceptos=[alt]), conceptos
                        )
                    )

                if req_ok and alt_ok:
                    cumplido = True
                    estado = "CUMPLIDO"
                elif req_ok or alt_ok:
                    estado = "PARCIAL"

            elif constr.tipo_criterio == "clasificacion":
                if len(items_satisfechos_nombres) >= constr.requiere:
                    cumplido = True
                    estado = "CUMPLIDO"
                elif len(items_satisfechos_nombres) >= 1:
                    estado = "PARCIAL"

            else:
                # Escala o tupla
                tiene_especifica = any(
                    pa.rol in ("prueba_especifica", "imagen")
                    for pa in problemas_agrupados
                )
                tiene_manifestacion = any(
                    pa.rol == "manifestacion" for pa in problemas_agrupados
                )
                if len(items_satisfechos_nombres) >= constr.requiere and (
                    tiene_especifica or tiene_manifestacion
                ):
                    cumplido = True
                    estado = "CUMPLIDO"
                elif tiene_especifica or len(items_satisfechos_nombres) >= 1:
                    estado = "PARCIAL"

            # Criterios pendientes (vacíos diagnósticos a investigar)
            pendientes: list[str] = [
                it.nombre
                for it in constr.items
                if it.nombre not in items_satisfechos_nombres
            ]

            # Puntuación determinista sin prompts
            score = 0.0
            if cumplido:
                score += 100.0
            elif estado == "PARCIAL":
                score += 40.0
            else:
                score += 10.0

            for pa in problemas_agrupados:
                if pa.rol == "prueba_especifica":
                    score += 25.0
                elif pa.rol == "prueba_sensible":
                    score += 15.0
                elif pa.rol == "imagen":
                    score += 20.0
                elif pa.rol == "manifestacion":
                    score += 15.0
                elif pa.rol == "nucleo":
                    score += 30.0
                else:
                    score += 5.0

                if pa.lr_positivo and pa.lr_positivo > 1.0:
                    score += round(math.log(pa.lr_positivo) * 10.0, 2)

            # Deduplicar problemas agrupados conservando el rol más relevante
            dedup_problemas: list[ProblemaAgrupado] = []
            vistos_terminos: set[str] = set()
            for pa in problemas_agrupados:
                llave = f"{_normalizar(pa.termino)}:{pa.criterio_nombre}"
                if llave not in vistos_terminos:
                    vistos_terminos.add(llave)
                    dedup_problemas.append(pa)

            explicacion = (
                f"{constr.consenso_nombre} ({estado}): "
                f"{len(items_satisfechos_nombres)} de {constr.requiere} criterios satisfechos. "
                f"Fuente: {constr.fuente}"
            )
            if constr.pmid:
                explicacion += f" (PMID: {constr.pmid})"

            agrupaciones.append(
                AgrupacionDiagnostica(
                    condicion_id=constr.condicion_id,
                    condicion_nombre=constr.termino,
                    skill_nombre=constr.skill_nombre,
                    consenso_nombre=constr.consenso_nombre,
                    fuente=constr.fuente,
                    pmid=constr.pmid,
                    tipo_criterio=constr.tipo_criterio,
                    problemas_agrupados=dedup_problemas,
                    criterios_satisfechos=sorted(items_satisfechos_nombres),
                    criterios_requeridos=constr.requiere,
                    criterios_pendientes=pendientes,
                    cumplido=cumplido,
                    estado=estado,
                    score=round(score, 2),
                    explicacion=explicacion,
                )
            )

        # Ordenar determinísticamente: primero cumplidos, luego por score descendente
        agrupaciones.sort(
            key=lambda a: (
                1 if a.cumplido else 0,
                1 if a.estado == "PARCIAL" else 0,
                a.score,
                len(a.problemas_agrupados),
            ),
            reverse=True,
        )

        return agrupaciones

    def seleccionar_protocolo(
        self,
        problemas: Sequence[Any] | str,
        disponibles: Sequence[str] | None = None,
    ) -> str | None:
        """Selecciona el protocolo clínico óptimo agrupando por criterios de consenso."""
        agrupaciones = self.agrupar_problemas(problemas)
        if not agrupaciones:
            return None

        disponibles_set = set(disponibles) if disponibles else None

        for ag in agrupaciones:
            if ag.skill_nombre:
                if disponibles_set is None or ag.skill_nombre in disponibles_set:
                    return ag.skill_nombre

            # Mapeo por ID de condición
            skill_map = MAPA_CONDICION_SKILL.get(ag.condicion_id)
            if skill_map and (disponibles_set is None or skill_map in disponibles_set):
                return skill_map

            # Búsqueda por similitud de nombre de condición
            if disponibles_set:
                norm_cond = _normalizar(ag.condicion_nombre).replace(" ", "_")
                for d in disponibles_set:
                    if d in norm_cond or norm_cond in d:
                        return d

        return None

    def triaje_texto(
        self, texto: str, disponibles: Sequence[str] | None = None
    ) -> tuple[str | None, list[AgrupacionDiagnostica]]:
        """Aplica el triaje determinista directamente sobre texto clínico."""
        agrupaciones = self.agrupar_problemas(texto)
        protocolo = self.seleccionar_protocolo(texto, disponibles=disponibles)
        return protocolo, agrupaciones

    def _extraer_problemas_de_texto(
        self,
        texto: str,
        construcciones: list[ConstruccionDiagnostica],
        conceptos: dict[str, dict[str, Any]],
    ) -> list[ProblemaClinico]:
        """Escanea el texto clínico en busca de problemas/conceptos ontológicos."""
        norm_texto = _normalizar(texto)
        encontrados: list[ProblemaClinico] = []
        terminos_vistos: set[str] = set()

        # Recorrer todos los ítems de criterios y conceptos conocidos
        for constr in construcciones:
            for item in constr.items:
                norm_item = _normalizar(item.nombre)
                if len(norm_item) >= 4 and norm_item in norm_texto:
                    if norm_item not in terminos_vistos:
                        terminos_vistos.add(norm_item)
                        cid = item.conceptos[0] if item.conceptos else None
                        encontrados.append(
                            ProblemaClinico(
                                termino=item.nombre,
                                codigo=cid,
                                polaridad=Polaridad.PRESENTE,
                            )
                        )

                for t_ref in item.terminos_referencia:
                    norm_ref = _normalizar(t_ref)
                    if len(norm_ref) >= 4 and norm_ref in norm_texto:
                        if norm_ref not in terminos_vistos:
                            terminos_vistos.add(norm_ref)
                            cid = item.conceptos[0] if item.conceptos else None
                            encontrados.append(
                                ProblemaClinico(
                                    termino=t_ref,
                                    codigo=cid,
                                    polaridad=Polaridad.PRESENTE,
                                )
                            )

        return encontrados
