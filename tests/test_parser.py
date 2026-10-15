import pytest
from sat_pipeline.parser import parse_cfdi_xml

SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="4.0" Fecha="2026-03-15T10:30:00" SubTotal="5000.00" Total="5800.00" TipoDeComprobante="I">
  <cfdi:Emisor Rfc="XAXX010101000" Nombre="TEST EMISOR"/>
  <cfdi:Receptor Rfc="URE180429CE4" Nombre="UNIVERSIDAD EJEMPLO"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81111508" Cantidad="2.00" ValorUnitario="2500.00" Importe="5000.00" Descripcion="Licencias de software">
      <cfdi:Impuestos>
        <cfdi:Traslados>
          <cfdi:Traslado Base="5000.00" Impuesto="002" TasaOCuota="0.160000" Importe="800.00"/>
        </cfdi:Traslados>
      </cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="AAAA-BBBB-CCCC-DDDD"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""

def test_parse_valid_cfdi():
    comp, conceptos, impuestos = parse_cfdi_xml(SAMPLE_XML)
    
    assert comp.uuid == "AAAA-BBBB-CCCC-DDDD"
    assert comp.año == 2026
    assert comp.mes == 3
    assert comp.subtotal == 5000.00
    assert comp.total == 5800.00
    assert comp.rfc_emisor == "XAXX010101000"
    assert comp.rfc_receptor == "URE180429CE4"
    assert comp.tipo_de_comprobante == "I"

    assert len(conceptos) == 1
    assert conceptos[0].clave_prod_serv == "81111508"
    assert conceptos[0].importe == 5000.00

    assert len(impuestos) == 1
    assert impuestos[0].tipo == "TRASLADO"
    assert impuestos[0].importe == 800.00

def test_invalid_xml_raises_error():
    with pytest.raises(ValueError):
        parse_cfdi_xml("<broken>xml")
