"""Conciliación entre lo ordenado y lo ejecutado.

De los tres resultados posibles, **sólo uno es de facturación**:

    orden sin ejecución   el paciente no recibió lo prescrito
    ejecución sin orden   se administró algo que nadie autorizó
    orden + ejecución     facturable

Los dos primeros son incidentes de seguridad clínica, y hoy se detectan
tarde o nunca. El mismo mecanismo que cuadra la cuenta cuadra la
medicación, y de las dos cosas la segunda importa más.

Por eso este módulo no se llama «facturador»: factura como efecto
secundario de comprobar que lo ordenado se cumplió.
"""

import logging
from dataclasses import dataclass, field

from ..db.store import normalizar
from .modelos import (
    Cargo,
    Cuenta,
    Descuadre,
    Ejecucion,
    EstadoCargo,
    EstadoOrden,
    Orden,
    TipoDescuadre,
)
from .repositorio import CargoRepo, EjecucionRepo, OrdenRepo, TarifarioRepo

logger = logging.getLogger(__name__)


@dataclass
class Pareja:
    """Una orden con su ejecución. Lo único que se puede facturar."""

    orden: Orden
    ejecucion: Ejecucion


@dataclass
class ResultadoConciliacion:
    parejas: list[Pareja] = field(default_factory=list)
    descuadres: list[Descuadre] = field(default_factory=list)

    @property
    def cuadra(self) -> bool:
        return not self.descuadres


class Conciliador:
    """Empareja órdenes con ejecuciones y deriva los cargos."""

    def __init__(
        self,
        ordenes: OrdenRepo,
        ejecuciones: EjecucionRepo,
        cargos: CargoRepo,
        tarifario: TarifarioRepo,
        sistema_tarifario: str = "demo",
    ):
        self.ordenes = ordenes
        self.ejecuciones = ejecuciones
        self.cargos = cargos
        self.tarifario = tarifario
        self.sistema_tarifario = sistema_tarifario

    # --- Conciliación --------------------------------------------------

    def conciliar(self, paciente_id: str) -> ResultadoConciliacion:
        ordenes = [
            o
            for o in self.ordenes.listar(paciente_id)
            if o.estado is not EstadoOrden.ANULADA
        ]
        ejecuciones = self.ejecuciones.listar(paciente_id)

        resultado = ResultadoConciliacion()
        usadas: set[str] = set()

        for orden in ordenes:
            ejecucion = self._buscar_ejecucion(orden, ejecuciones, usadas)
            if ejecucion is None:
                resultado.descuadres.append(
                    Descuadre(
                        tipo=TipoDescuadre.ORDEN_SIN_EJECUTAR,
                        termino=orden.termino,
                        timestamp=orden.timestamp,
                        orden_id=orden.id,
                        detalle=(
                            "Prescrito pero sin registro de que se cumpliera. "
                            "El paciente puede no haberlo recibido."
                        ),
                    )
                )
                continue

            usadas.add(str(ejecucion.id))
            resultado.parejas.append(Pareja(orden, ejecucion))
            if ejecucion.orden_id != orden.id:
                self.ejecuciones.vincular(str(ejecucion.id), str(orden.id))
            if orden.estado is EstadoOrden.PENDIENTE:
                self.ordenes.marcar(str(orden.id), EstadoOrden.CUMPLIDA)

        for ejecucion in ejecuciones:
            if str(ejecucion.id) in usadas:
                continue
            resultado.descuadres.append(
                Descuadre(
                    tipo=TipoDescuadre.EJECUCION_SIN_ORDEN,
                    termino=ejecucion.termino,
                    timestamp=ejecucion.timestamp,
                    ejecucion_id=ejecucion.id,
                    detalle=(
                        f"Registrado por {ejecucion.actor or ejecucion.origen} sin "
                        "orden que lo autorice."
                    ),
                )
            )

        return resultado

    @staticmethod
    def _buscar_ejecucion(
        orden: Orden, ejecuciones: list[Ejecucion], usadas: set[str]
    ) -> Ejecucion | None:
        """Empareja por vínculo explícito, luego por código, luego por término.

        No se empareja nada anterior a la orden: una ejecución previa a su
        autorización no la cumple, y tratarla como si lo hiciera ocultaría
        justo el caso que queremos detectar.
        """
        candidatas = [
            e
            for e in ejecuciones
            if str(e.id) not in usadas and e.timestamp >= orden.timestamp
        ]

        for e in candidatas:
            if e.orden_id and e.orden_id == orden.id:
                return e
        if orden.codigo:
            for e in candidatas:
                if e.codigo and e.codigo == orden.codigo:
                    return e
        objetivo = normalizar(orden.termino)
        for e in candidatas:
            if normalizar(e.termino) == objetivo:
                return e
        return None

    # --- Facturación ---------------------------------------------------

    def facturar(self, paciente_id: str) -> Cuenta:
        """Deriva cargos de las parejas conciliadas.

        Todo cargo nace **propuesto**: cobrarle a un paciente por algo que
        dedujo un modelo de lenguaje sin que nadie lo revisara sería
        indefendible. Y nace de una orden: sin autorización no hay cargo.
        """
        conciliacion = self.conciliar(paciente_id)

        for pareja in conciliacion.parejas:
            cargo = self._cargo_de(pareja)
            if cargo:
                self.cargos.crear(cargo)

        return Cuenta(
            paciente_id=paciente_id,
            cargos=self.cargos.listar(paciente_id),
            descuadres=conciliacion.descuadres,
        )

    def _cargo_de(self, pareja: Pareja) -> Cargo | None:
        orden = pareja.orden

        codigo = None
        if orden.concepto_id:
            codigo = self.tarifario.codigo_para(
                orden.concepto_id, self.sistema_tarifario
            )
        # Un protocolo puede declarar el código tarifario directamente.
        if not codigo and orden.sistema == self.sistema_tarifario:
            codigo = orden.codigo

        if not codigo:
            # Sin código no se factura. Es un hueco de catálogo, no un
            # motivo para inventar un precio.
            logger.info(
                "Sin código tarifario para '%s'; no se genera cargo", orden.termino
            )
            return None

        tarifa = self.tarifario.buscar(
            self.sistema_tarifario, codigo, fecha=pareja.ejecucion.timestamp
        )
        if not tarifa:
            logger.info("Código %s sin tarifa vigente; no se genera cargo", codigo)
            return None

        cantidad = float(pareja.ejecucion.detalle.get("cantidad", 1) or 1)

        return Cargo(
            paciente_id=orden.paciente_id,
            orden_id=orden.id,
            ejecucion_id=pareja.ejecucion.id,
            codigo_tarifario=codigo,
            sistema_tarifario=self.sistema_tarifario,
            descripcion=tarifa["descripcion"] or orden.termino,
            cantidad=cantidad,
            importe_unitario=float(tarifa["importe"]),
            estado=EstadoCargo.PROPUESTO,
        )

    # --- Alta ----------------------------------------------------------

    def cuenta(self, paciente_id: str) -> Cuenta:
        """La cuenta al día, sin recalcular nada.

        El problema de las seis horas de espera al alta no es de velocidad
        de proceso: es que la cuenta se calcula en bloque al final. Aquí
        los cargos se acumulan según se concilian, y esto sólo proyecta.
        """
        return Cuenta(
            paciente_id=paciente_id,
            cargos=self.cargos.listar(paciente_id),
            descuadres=self.conciliar(paciente_id).descuadres,
        )
