"""
High-throughput XML stream parser for SAT CFDI 4.0 and 3.3 vouchers.
Normalizes hierarchical XML into relational tabular tuples for Columnar storage.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Tuple, List, Optional
from datetime import datetime
from .models import ComprobanteRow, ConceptoRow, ImpuestoRow


CFDI_NAMESPACES = {
    "cfdi4": "http://www.sat.gob.mx/cfd/4",
    "cfdi3": "http://www.sat.gob.mx/cfd/3",
    "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
    "pago20": "http://www.sat.gob.mx/Pagos20",
    "nomina12": "http://www.sat.gob.mx/nomina12",
}


def _strip_tag_namespace(tag: str) -> str:
    """Removes XML namespace prefix from tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_cfdi_xml(xml_content: str) -> Tuple[ComprobanteRow, List[ConceptoRow], List[ImpuestoRow]]:
    """
    Parses a single CFDI XML string into relational tabular data structures.
    
    Returns:
        Tuple of (ComprobanteRow, List[ConceptoRow], List[ImpuestoRow])
    """
    try:
        root = ET.fromstring(xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content)
    except Exception as e:
        raise ValueError(f"XML parse error: {str(e)}")

    # Extract version & root attributes
    version = root.attrib.get("Version", root.attrib.get("version", "4.0"))
    fecha_raw = root.attrib.get("Fecha", root.attrib.get("fecha", ""))
    
    try:
        fecha_dt = datetime.fromisoformat(fecha_raw.replace("Z", ""))
    except Exception:
        fecha_dt = datetime.now()

    año = fecha_dt.year
    mes = fecha_dt.month
    dia = fecha_dt.day

    tipo_de_comprobante = root.attrib.get("TipoDeComprobante", root.attrib.get("tipoDeComprobante", "I")).upper()
    metodo_pago = root.attrib.get("MetodoPago", root.attrib.get("metodoPago"))
    forma_pago = root.attrib.get("FormaPago", root.attrib.get("formaPago"))
    moneda = root.attrib.get("Moneda", root.attrib.get("moneda", "MXN"))
    tipo_cambio = float(root.attrib.get("TipoCambio", root.attrib.get("tipoCambio", "1.0")) or 1.0)
    
    subtotal = float(root.attrib.get("SubTotal", root.attrib.get("subTotal", "0.0")) or 0.0)
    descuento = float(root.attrib.get("Descuento", root.attrib.get("descuento", "0.0")) or 0.0)
    total = float(root.attrib.get("Total", root.attrib.get("total", "0.0")) or 0.0)

    # Find TimbreFiscalDigital UUID
    uuid = None
    for elem in root.iter():
        clean_tag = _strip_tag_namespace(elem.tag)
        if clean_tag == "TimbreFiscalDigital":
            uuid = elem.attrib.get("UUID") or elem.attrib.get("uuid")
            break

    if not uuid:
        # Fallback to Folio/Serie or generated hash if uncertified
        serie = root.attrib.get("Serie", "")
        folio = root.attrib.get("Folio", "")
        if folio:
            uuid = f"LOCAL-{serie}-{folio}"
        else:
            uuid = f"UNKNOWN-{abs(hash(xml_content)) % 100000000:08d}"

    uuid = uuid.upper()

    # Emisor & Receptor
    rfc_emisor = "XAXX010101000"
    nombre_emisor = "EMISOR DESCONOCIDO"
    regimen_fiscal_emisor = None

    rfc_receptor = "XAXX010101000"
    nombre_receptor = "RECEPTOR DESCONOCIDO"
    uso_cfdi_receptor = None

    for elem in root:
        clean_tag = _strip_tag_namespace(elem.tag)
        if clean_tag == "Emisor":
            rfc_emisor = elem.attrib.get("Rfc", elem.attrib.get("rfc", rfc_emisor)).upper()
            nombre_emisor = elem.attrib.get("Nombre", elem.attrib.get("nombre", nombre_emisor))
            regimen_fiscal_emisor = elem.attrib.get("RegimenFiscal", elem.attrib.get("regimenFiscal"))
        elif clean_tag == "Receptor":
            rfc_receptor = elem.attrib.get("Rfc", elem.attrib.get("rfc", rfc_receptor)).upper()
            nombre_receptor = elem.attrib.get("Nombre", elem.attrib.get("nombre", nombre_receptor))
            uso_cfdi_receptor = elem.attrib.get("UsoCFDI", elem.attrib.get("usoCFDI"))

    # Conceptos
    conceptos_rows: List[ConceptoRow] = []
    impuestos_rows: List[ImpuestoRow] = []
    
    total_trasladados = 0.0
    total_retenidos = 0.0

    for elem in root.iter():
        clean_tag = _strip_tag_namespace(elem.tag)
        if clean_tag == "Concepto":
            cant = float(elem.attrib.get("Cantidad", elem.attrib.get("cantidad", "1.0")) or 1.0)
            val_unit = float(elem.attrib.get("ValorUnitario", elem.attrib.get("valorUnitario", "0.0")) or 0.0)
            imp = float(elem.attrib.get("Importe", elem.attrib.get("importe", str(cant * val_unit))) or 0.0)
            desc = float(elem.attrib.get("Descuento", elem.attrib.get("descuento", "0.0")) or 0.0)

            c_row = ConceptoRow(
                uuid=uuid,
                clave_prod_serv=elem.attrib.get("ClaveProdServ", elem.attrib.get("claveProdServ", "01010101")),
                no_identificacion=elem.attrib.get("NoIdentificacion", elem.attrib.get("noIdentificacion")),
                cantidad=cant,
                clave_unidad=elem.attrib.get("ClaveUnidad", elem.attrib.get("claveUnidad", "H87")),
                unidad=elem.attrib.get("Unidad", elem.attrib.get("unidad")),
                descripcion=elem.attrib.get("Descripcion", elem.attrib.get("descripcion", "")),
                valor_unitario=val_unit,
                importe=imp,
                descuento=desc,
                objeto_imp=elem.attrib.get("ObjetoImp", elem.attrib.get("objetoImp")),
            )
            conceptos_rows.append(c_row)

        elif clean_tag == "Traslado" and "Base" in elem.attrib:
            base = float(elem.attrib.get("Base", "0.0") or 0.0)
            imp_val = float(elem.attrib.get("Importe", "0.0") or 0.0)
            tasa = float(elem.attrib.get("TasaOCuota", "0.16") or 0.16)
            total_trasladados += imp_val

            impuestos_rows.append(ImpuestoRow(
                uuid=uuid,
                tipo="TRASLADO",
                base=base,
                impuesto=elem.attrib.get("Impuesto", "002"),
                tipo_factor=elem.attrib.get("TipoFactor", "Tasa"),
                tasa_o_cuota=tasa,
                importe=imp_val
            ))

        elif clean_tag == "Retencion" and "Base" in elem.attrib:
            base = float(elem.attrib.get("Base", "0.0") or 0.0)
            imp_val = float(elem.attrib.get("Importe", "0.0") or 0.0)
            tasa = float(elem.attrib.get("TasaOCuota", "0.0") or 0.0)
            total_retenidos += imp_val

            impuestos_rows.append(ImpuestoRow(
                uuid=uuid,
                tipo="RETENCION",
                base=base,
                impuesto=elem.attrib.get("Impuesto", "001"),
                tipo_factor=elem.attrib.get("TipoFactor", "Tasa"),
                tasa_o_cuota=tasa,
                importe=imp_val
            ))

    comprobante_row = ComprobanteRow(
        uuid=uuid,
        version=version,
        fecha=fecha_raw,
        año=año,
        mes=mes,
        dia=dia,
        tipo_de_comprobante=tipo_de_comprobante,
        metodo_pago=metodo_pago,
        forma_pago=forma_pago,
        moneda=moneda,
        tipo_cambio=tipo_cambio,
        subtotal=subtotal,
        descuento=descuento,
        total=total,
        rfc_emisor=rfc_emisor,
        nombre_emisor=nombre_emisor,
        regimen_fiscal_emisor=regimen_fiscal_emisor,
        rfc_receptor=rfc_receptor,
        nombre_receptor=nombre_receptor,
        uso_cfdi_receptor=uso_cfdi_receptor,
        total_impuestos_trasladados=total_trasladados,
        total_impuestos_retenidos=total_retenidos,
    )

    return comprobante_row, conceptos_rows, impuestos_rows
