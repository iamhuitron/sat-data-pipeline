"""
Data models and typed schemas for CFDI 4.0 / 3.3 columnar tables.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from decimal import Decimal


@dataclass
class ComprobanteRow:
    uuid: str
    version: str
    fecha: str
    año: int
    mes: int
    dia: int
    tipo_de_comprobante: str
    metodo_pago: Optional[str]
    forma_pago: Optional[str]
    moneda: str
    tipo_cambio: float
    subtotal: float
    descuento: float
    total: float
    rfc_emisor: str
    nombre_emisor: str
    regimen_fiscal_emisor: Optional[str]
    rfc_receptor: str
    nombre_receptor: str
    uso_cfdi_receptor: Optional[str]
    total_impuestos_trasladados: float
    total_impuestos_retenidos: float
    es_cancelado: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConceptoRow:
    uuid: str
    clave_prod_serv: str
    no_identificacion: Optional[str]
    cantidad: float
    clave_unidad: str
    unidad: Optional[str]
    descripcion: str
    valor_unitario: float
    importe: float
    descuento: float
    objeto_imp: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImpuestoRow:
    uuid: str
    tipo: str  # "TRASLADO" o "RETENCION"
    base: float
    impuesto: str  # "002" (IVA), "001" (ISR), "003" (IEPS)
    tipo_factor: str  # "Tasa", "Cuota", "Exento"
    tasa_o_cuota: float
    importe: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FiscalMetric:
    rfc: str
    periodo: str
    total_ingresos: float
    total_egresos: float
    iva_trasladado: float
    iva_retenido: float
    isr_retenido: float
    balance_iva: float
    num_comprobantes: int
