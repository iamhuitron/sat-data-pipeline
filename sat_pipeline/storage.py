"""
Storage engine: Materializes tabular CFDI records into Parquet datasets
and manages embedded DuckDB relational tables and views.
"""

import os
from typing import List, Dict, Any, Optional
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

from .models import ComprobanteRow, ConceptoRow, ImpuestoRow


class CFDIStorage:
    def __init__(self, base_dir: str = "./data/lake", db_path: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir)
        self.comprobantes_dir = os.path.join(self.base_dir, "comprobantes")
        self.conceptos_dir = os.path.join(self.base_dir, "conceptos")
        self.impuestos_dir = os.path.join(self.base_dir, "impuestos")
        
        os.makedirs(self.comprobantes_dir, exist_ok=True)
        os.makedirs(self.conceptos_dir, exist_ok=True)
        os.makedirs(self.impuestos_dir, exist_ok=True)

        self.db_path = db_path or os.path.join(self.base_dir, "sat_analytics.duckdb")
        self.con = duckdb.connect(self.db_path)
        self._init_duckdb_views()

    def _init_duckdb_views(self):
        """Initializes tables in DuckDB."""
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS comprobantes (
                uuid VARCHAR PRIMARY KEY,
                version VARCHAR,
                fecha VARCHAR,
                año INTEGER,
                mes INTEGER,
                dia INTEGER,
                tipo_de_comprobante VARCHAR,
                metodo_pago VARCHAR,
                forma_pago VARCHAR,
                moneda VARCHAR,
                tipo_cambio DOUBLE,
                subtotal DOUBLE,
                descuento DOUBLE,
                total DOUBLE,
                rfc_emisor VARCHAR,
                nombre_emisor VARCHAR,
                regimen_fiscal_emisor VARCHAR,
                rfc_receptor VARCHAR,
                nombre_receptor VARCHAR,
                uso_cfdi_receptor VARCHAR,
                total_impuestos_trasladados DOUBLE,
                total_impuestos_retenidos DOUBLE,
                es_cancelado BOOLEAN
            );
        """)

        self.con.execute("""
            CREATE TABLE IF NOT EXISTS conceptos (
                uuid VARCHAR,
                clave_prod_serv VARCHAR,
                no_identificacion VARCHAR,
                cantidad DOUBLE,
                clave_unidad VARCHAR,
                unidad VARCHAR,
                descripcion VARCHAR,
                valor_unitario DOUBLE,
                importe DOUBLE,
                descuento DOUBLE,
                objeto_imp VARCHAR
            );
        """)

        self.con.execute("""
            CREATE TABLE IF NOT EXISTS impuestos (
                uuid VARCHAR,
                tipo VARCHAR,
                base DOUBLE,
                impuesto VARCHAR,
                tipo_factor VARCHAR,
                tasa_o_cuota DOUBLE,
                importe DOUBLE
            );
        """)

    def save_batch(
        self,
        comprobantes: List[ComprobanteRow],
        conceptos: List[ConceptoRow],
        impuestos: List[ImpuestoRow]
    ) -> int:
        """
        Saves a batch of records into DuckDB and partitions them into Parquet.
        """
        if not comprobantes:
            return 0

        # Insert into DuckDB
        for comp in comprobantes:
            d = comp.to_dict()
            self.con.execute("""
                INSERT OR REPLACE INTO comprobantes VALUES (
                    $uuid, $version, $fecha, $año, $mes, $dia, $tipo_de_comprobante,
                    $metodo_pago, $forma_pago, $moneda, $tipo_cambio, $subtotal,
                    $descuento, $total, $rfc_emisor, $nombre_emisor, $regimen_fiscal_emisor,
                    $rfc_receptor, $nombre_receptor, $uso_cfdi_receptor,
                    $total_impuestos_trasladados, $total_impuestos_retenidos, $es_cancelado
                )
            """, d)

        for c in conceptos:
            self.con.execute("""
                INSERT INTO conceptos VALUES (
                    $uuid, $clave_prod_serv, $no_identificacion, $cantidad,
                    $clave_unidad, $unidad, $descripcion, $valor_unitario,
                    $importe, $descuento, $objeto_imp
                )
            """, c.to_dict())

        for imp in impuestos:
            self.con.execute("""
                INSERT INTO impuestos VALUES (
                    $uuid, $tipo, $base, $impuesto, $tipo_factor,
                    $tasa_o_cuota, $importe
                )
            """, imp.to_dict())

        # Also write / update Parquet files
        self._export_to_parquet()
        return len(comprobantes)

    def _export_to_parquet(self):
        """Exports DuckDB tables to Parquet partitions."""
        comp_df = self.con.execute("SELECT * FROM comprobantes").df()
        if not comp_df.empty:
            table = pa.Table.from_pandas(comp_df)
            pq.write_to_dataset(
                table,
                root_path=self.comprobantes_dir,
                partition_cols=["año", "mes"],
                existing_data_behavior="overwrite_or_ignore"
            )

        conc_df = self.con.execute("SELECT * FROM conceptos").df()
        if not conc_df.empty:
            pq.write_table(pa.Table.from_pandas(conc_df), os.path.join(self.conceptos_dir, "conceptos.parquet"))

        imp_df = self.con.execute("SELECT * FROM impuestos").df()
        if not imp_df.empty:
            pq.write_table(pa.Table.from_pandas(imp_df), os.path.join(self.impuestos_dir, "impuestos.parquet"))

    def close(self):
        self.con.close()
