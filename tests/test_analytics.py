import pytest
from sat_pipeline.storage import CFDIStorage
from sat_pipeline.analytics import SATAnalytics
from sat_pipeline.models import ComprobanteRow, ConceptoRow, ImpuestoRow

@pytest.fixture
def analytics_setup(tmp_path):
    storage = CFDIStorage(base_dir=str(tmp_path / "lake"))
    
    c1 = ComprobanteRow(
        uuid="U1", version="4.0", fecha="2026-01-10T10:00:00", año=2026, mes=1, dia=10,
        tipo_de_comprobante="I", metodo_pago="PUE", forma_pago="03", moneda="MXN", tipo_cambio=1.0,
        subtotal=10000.0, descuento=0.0, total=11600.0,
        rfc_emisor="EMP_BUENA_1", nombre_emisor="EMPRESA 1", regimen_fiscal_emisor="601",
        rfc_receptor="MI_EMPRESA", nombre_receptor="MI EMPRESA", uso_cfdi_receptor="G03",
        total_impuestos_trasladados=1600.0, total_impuestos_retenidos=0.0
    )

    c2 = ComprobanteRow(
        uuid="U2", version="4.0", fecha="2026-01-15T12:00:00", año=2026, mes=1, dia=15,
        tipo_de_comprobante="E", metodo_pago="PUE", forma_pago="03", moneda="MXN", tipo_cambio=1.0,
        subtotal=2000.0, descuento=0.0, total=2320.0,
        rfc_emisor="EMP_FANTASMA", nombre_emisor="EMPRESA FANTASMA SA", regimen_fiscal_emisor="601",
        rfc_receptor="MI_EMPRESA", nombre_receptor="MI EMPRESA", uso_cfdi_receptor="G03",
        total_impuestos_trasladados=320.0, total_impuestos_retenidos=0.0
    )

    storage.save_batch([c1, c2], [], [])
    analytics = SATAnalytics(storage.con)
    yield storage, analytics
    storage.close()

def test_kpis_summary(analytics_setup):
    _, analytics = analytics_setup
    kpis = analytics.get_kpis_summary()
    assert kpis["total_comprobantes"] == 2
    assert kpis["total_ingresos"] == 11600.0
    assert kpis["total_egresos"] == 2320.0
    assert kpis["iva_trasladado_total"] == 1920.0

def test_efos_screening(analytics_setup):
    _, analytics = analytics_setup
    blacklist = ["EMP_FANTASMA", "OTRO_RFC"]
    alerts = analytics.screen_against_efos(blacklist)
    
    assert len(alerts) == 1
    assert alerts[0]["rfc_emisor"] == "EMP_FANTASMA"
    assert alerts[0]["total"] == 2320.0
