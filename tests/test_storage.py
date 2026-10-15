import os
import shutil
import pytest
from sat_pipeline.storage import CFDIStorage
from sat_pipeline.models import ComprobanteRow, ConceptoRow, ImpuestoRow

@pytest.fixture
def temp_lake(tmp_path):
    lake_dir = str(tmp_path / "lake")
    storage = CFDIStorage(base_dir=lake_dir)
    yield storage
    storage.close()

def test_storage_save_and_query(temp_lake):
    storage = temp_lake
    
    comp = ComprobanteRow(
        uuid="UUID-123-TEST",
        version="4.0",
        fecha="2026-03-15T10:00:00",
        año=2026,
        mes=3,
        dia=15,
        tipo_de_comprobante="I",
        metodo_pago="PUE",
        forma_pago="03",
        moneda="MXN",
        tipo_cambio=1.0,
        subtotal=1000.0,
        descuento=0.0,
        total=1160.0,
        rfc_emisor="EMISOR123456",
        nombre_emisor="EMISOR CORP",
        regimen_fiscal_emisor="601",
        rfc_receptor="RECEPTOR9876",
        nombre_receptor="RECEPTOR SA",
        uso_cfdi_receptor="G03",
        total_impuestos_trasladados=160.0,
        total_impuestos_retenidos=0.0
    )
    
    conc = ConceptoRow(
        uuid="UUID-123-TEST",
        clave_prod_serv="81111508",
        no_identificacion="001",
        cantidad=1.0,
        clave_unidad="E48",
        unidad="Servicio",
        descripcion="Consultoria",
        valor_unitario=1000.0,
        importe=1000.0,
        descuento=0.0,
        objeto_imp="02"
    )

    imp = ImpuestoRow(
        uuid="UUID-123-TEST",
        tipo="TRASLADO",
        base=1000.0,
        impuesto="002",
        tipo_factor="Tasa",
        tasa_o_cuota=0.16,
        importe=160.0
    )

    count = storage.save_batch([comp], [conc], [imp])
    assert count == 1

    # Query directly from DuckDB
    rows = storage.con.execute("SELECT uuid, total FROM comprobantes").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "UUID-123-TEST"
    assert rows[0][1] == 1160.0
