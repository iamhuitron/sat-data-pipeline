"""
Fiscal and transactional analytics engine using embedded DuckDB queries.
"""

from typing import List, Dict, Any, Optional
import duckdb


class SATAnalytics:
    def __init__(self, duckdb_conn: duckdb.DuckDBPyConnection):
        self.con = duckdb_conn

    def get_kpis_summary(self, target_rfc: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates executive fiscal KPIs:
        - Total Invoiced (Ingresos)
        - Total Expenses (Egresos)
        - Total Payroll Paid (Nómina)
        - Net VAT Balance (IVA Trasladado - IVA Acreditable)
        """
        rfc_filter = ""
        params = []
        if target_rfc:
            rfc_filter = "WHERE rfc_emisor = $1 OR rfc_receptor = $1"
            params = [target_rfc]

        query = f"""
            SELECT 
                COUNT(*) as total_vouchers,
                COALESCE(SUM(CASE WHEN tipo_de_comprobante = 'I' THEN total ELSE 0 END), 0) as total_ingresos,
                COALESCE(SUM(CASE WHEN tipo_de_comprobante = 'E' THEN total ELSE 0 END), 0) as total_egresos,
                COALESCE(SUM(CASE WHEN tipo_de_comprobante = 'N' THEN total ELSE 0 END), 0) as total_nomina,
                COALESCE(SUM(total_impuestos_trasladados), 0) as iva_trasladado_total,
                COALESCE(SUM(total_impuestos_retenidos), 0) as retenciones_total
            FROM comprobantes
            {rfc_filter}
        """
        res = self.con.execute(query, params).fetchone()
        
        return {
            "total_comprobantes": res[0],
            "total_ingresos": round(float(res[1]), 2),
            "total_egresos": round(float(res[2]), 2),
            "total_nomina": round(float(res[3]), 2),
            "iva_trasladado_total": round(float(res[4]), 2),
            "retenciones_total": round(float(res[5]), 2),
        }

    def get_monthly_trend(self) -> List[Dict[str, Any]]:
        """Computes revenue and expenditure breakdown grouped by year and month."""
        query = """
            SELECT 
                año,
                mes,
                COUNT(*) as num_facturas,
                ROUND(SUM(CASE WHEN tipo_de_comprobante = 'I' THEN total ELSE 0 END), 2) as ingresos,
                ROUND(SUM(CASE WHEN tipo_de_comprobante = 'E' THEN total ELSE 0 END), 2) as egresos,
                ROUND(SUM(CASE WHEN tipo_de_comprobante = 'N' THEN total ELSE 0 END), 2) as nomina
            FROM comprobantes
            GROUP BY año, mes
            ORDER BY año ASC, mes ASC
        """
        return self.con.execute(query).arrow().read_all().to_pylist()

    def get_top_suppliers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Identifies top suppliers by invoiced amount."""
        query = f"""
            SELECT 
                rfc_emisor,
                nombre_emisor,
                COUNT(*) as facturas_emitidas,
                ROUND(SUM(total), 2) as total_facturado
            FROM comprobantes
            GROUP BY rfc_emisor, nombre_emisor
            ORDER BY total_facturado DESC
            LIMIT {int(limit)}
        """
        return self.con.execute(query).arrow().read_all().to_pylist()

    def screen_against_efos(self, blacklisted_rfcs: List[str]) -> List[Dict[str, Any]]:
        """
        Screens all suppliers and clients against the official SAT Art. 69-B blacklist.
        Returns list of matching fraudulent or simulated operations.
        """
        if not blacklisted_rfcs:
            return []

        # Create temporary table for blacklisted RFCs
        self.con.execute("CREATE OR REPLACE TEMP TABLE efos_blacklist (rfc VARCHAR PRIMARY KEY);")
        for rfc in blacklisted_rfcs:
            self.con.execute("INSERT OR IGNORE INTO efos_blacklist VALUES (?)", [rfc.strip().upper()])

        query = """
            SELECT 
                c.uuid,
                c.fecha,
                c.rfc_emisor,
                c.nombre_emisor,
                c.rfc_receptor,
                c.nombre_receptor,
                c.total
            FROM comprobantes c
            INNER JOIN efos_blacklist b ON c.rfc_emisor = b.rfc OR c.rfc_receptor = b.rfc
            ORDER BY c.total DESC
        """
        alerts = self.con.execute(query).arrow().read_all().to_pylist()
        self.con.execute("DROP TABLE IF EXISTS efos_blacklist;")
        return alerts

    def get_category_breakdown(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Analyzes top SAT product & service codes (ClaveProdServ)."""
        query = f"""
            SELECT 
                clave_prod_serv,
                COUNT(*) as veces_facturado,
                ROUND(SUM(importe), 2) as importe_total
            FROM conceptos
            GROUP BY clave_prod_serv
            ORDER BY importe_total DESC
            LIMIT {int(limit)}
        """
        return self.con.execute(query).arrow().read_all().to_pylist()
