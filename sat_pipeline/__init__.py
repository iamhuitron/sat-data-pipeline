"""
SAT Data Pipeline: High-performance XML to Parquet ETL & DuckDB analytics engine.
"""

__version__ = "1.0.0"
__author__ = "Miguel Delgado Huitron (@iamhuitron)"

from .models import ComprobanteRow, ConceptoRow, ImpuestoRow
from .parser import parse_cfdi_xml
from .storage import CFDIStorage
from .analytics import SATAnalytics

__all__ = [
    "ComprobanteRow",
    "ConceptoRow",
    "ImpuestoRow",
    "parse_cfdi_xml",
    "CFDIStorage",
    "SATAnalytics",
]
