"""
Command Line Interface for SAT Data Pipeline.
"""

import sys
import os
import argparse
import json
from .parser import parse_cfdi_xml
from .storage import CFDIStorage
from .analytics import SATAnalytics


def main():
    parser = argparse.ArgumentParser(
        description="SAT Data Pipeline: High-performance XML to Parquet ETL & DuckDB analytics engine"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingesta y parsea un archivo XML o directorio de XMLs")
    ingest_parser.add_argument("path", help="Ruta al archivo XML o directorio de comprobantes CFDI")
    ingest_parser.add_argument("--lake-dir", default="./data/lake", help="Directorio raíz para Parquet y DuckDB")

    # KPIs command
    kpis_parser = subparsers.add_parser("kpis", help="Calcula KPIs fiscales ejecutivos desde la base de datos")
    kpis_parser.add_argument("--lake-dir", default="./data/lake", help="Directorio raíz del data lake")
    kpis_parser.add_argument("--rfc", help="Filtrar por RFC emisor o receptor")

    # Screen EFOS command
    screen_parser = subparsers.add_parser("screen-efos", help="Cruza los comprobantes contra lista negra del SAT")
    screen_parser.add_argument("--lake-dir", default="./data/lake", help="Directorio raíz del data lake")
    screen_parser.add_argument("blacklist_file", help="Archivo de texto con RFCs sospechosos (uno por línea)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    storage = CFDIStorage(base_dir=args.lake_dir)
    analytics = SATAnalytics(storage.con)

    if args.command == "ingest":
        target = args.path
        xml_files = []
        if os.path.isfile(target) and target.endswith(".xml"):
            xml_files.append(target)
        elif os.path.isdir(target):
            for root, _, files in os.walk(target):
                for f in files:
                    if f.endswith(".xml"):
                        xml_files.append(os.path.join(root, f))
        else:
            print(f"Error: La ruta '{target}' no es un archivo XML válido ni un directorio.")
            sys.exit(1)

        print(f"Encontrados {len(xml_files)} archivos XML. Procesando...")
        comprobantes, conceptos, impuestos = [], [], []
        
        for fp in xml_files:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    comp, conc, imp = parse_cfdi_xml(content)
                    comprobantes.append(comp)
                    conceptos.extend(conc)
                    impuestos.extend(imp)
            except Exception as e:
                print(f"Advertencia al parsear {fp}: {e}")

        total_saved = storage.save_batch(comprobantes, conceptos, impuestos)
        print(f"✓ Ingesta completada con éxito. {total_saved} comprobantes persistidos en DuckDB y particionados en Parquet.")

    elif args.command == "kpis":
        kpis = analytics.get_kpis_summary(target_rfc=args.rfc)
        print("\n============================== RESUMEN FISCAL ==============================")
        print(f"Total de Comprobantes : {kpis['total_comprobantes']}")
        print(f"Total Ingresos (I)    : ${kpis['total_ingresos']:,.2f} MXN")
        print(f"Total Egresos (E)     : ${kpis['total_egresos']:,.2f} MXN")
        print(f"Total Nómina (N)      : ${kpis['total_nomina']:,.2f} MXN")
        print(f"IVA Trasladado Total  : ${kpis['iva_trasladado_total']:,.2f} MXN")
        print(f"Retenciones Totales   : ${kpis['retenciones_total']:,.2f} MXN")
        print("============================================================================\n")

    elif args.command == "screen-efos":
        if not os.path.isfile(args.blacklist_file):
            print(f"Error: No se encontró el archivo {args.blacklist_file}")
            sys.exit(1)
        with open(args.blacklist_file, "r") as f:
            rfcs = [line.strip() for line in f if line.strip()]
        alerts = analytics.screen_against_efos(rfcs)
        print(f"\nSe encontraron {len(alerts)} operaciones coincidentes con la lista negra:")
        for alert in alerts:
            print(f" - [ALERTA] UUID: {alert['uuid']} | Fecha: {alert['fecha']} | Emisor: {alert['rfc_emisor']} | Total: ${alert['total']:,.2f}")

    storage.close()


if __name__ == "__main__":
    main()
