# 🏛️ SAT Data Pipeline Architecture & Topology

High-throughput, type-safe data extraction and analytical engine for Mexican Tax Authority (SAT) CFDI 3.3 and 4.0 XML vouchers. Built with Python 3.12, Pydantic, DuckDB, and SQLite.

---

## 1. Technology Stack

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Runtime** | Python 3.12+ | Native dataclasses, strict typing, match-case parsing |
| **Parsing & Validation** | `lxml` & `pydantic` | Fast XML element traversal, XML namespace resolution, schema validation |
| **Storage Engine** | SQLite / DuckDB | Embedded columnar and relational storage for local high-speed analytics |
| **Data Analytics** | `duckdb` & `pandas` | Analytical SQL queries over fiscal records (IVA, ISR, IEPS, retentions) |
| **CLI Framework** | `argparse` / `click` | Batch ingestion and terminal reporting interface |
| **Testing** | `pytest` | 100% test coverage over fiscal edge cases and malformed XMLs |

---

## 2. System Topology & Component Graph

```mermaid
flowchart TD
    subgraph Inputs["Data Ingestion"]
        XMLFiles["CFDI XML Files (3.3 / 4.0)"]
        DirInput["Batch Directory / ZIP"]
    end

    subgraph CoreEngine["sat_pipeline Core"]
        CLI["CLI Interface (sat_pipeline/cli.py)"]
        Parser["XML Parser & Sanitizer (sat_pipeline/parser.py)"]
        Models["Pydantic Data Models (sat_pipeline/models.py)"]
        Storage["Storage Engine (sat_pipeline/storage.py)"]
        Analytics["Fiscal Analytics & Ledger (sat_pipeline/analytics.py)"]
    end

    subgraph Persistence["Storage & Export"]
        DB[(SQLite / DuckDB Database)]
        Reports["CSV / Excel / JSON Fiscal Reports"]
    end

    Inputs --> CLI
    CLI --> Parser
    Parser --> Models
    Models --> Storage
    Storage --> DB
    DB --> Analytics
    Analytics --> Reports
```

---

## 3. Data Ingestion & Processing Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as Auditor / Engineer
    participant CLI as sat_pipeline CLI
    participant Parser as CFDI Parser (lxml)
    participant Validator as Pydantic Models
    participant Storage as DuckDB / SQLite Storage
    participant Analytics as Fiscal Ledger

    User->>CLI: sat-pipeline ingest /data/xmls/
    CLI->>Parser: Stream XML files
    Parser->>Parser: Extract namespaces, TimbreFiscal, Conceptos, Impuestos
    Parser->>Validator: Instantiate CFDIVoucher model
    Validator->>Validator: Validate UUID, RFC, SubTotal, Total, Tasas
    Validator-->>Storage: Validated fiscal records
    Storage->>Storage: Upsert to database (idempotent by UUID)
    User->>CLI: sat-pipeline report --quarter Q1-2026
    CLI->>Analytics: Query cumulative revenue, deductible expenses, net tax
    Analytics-->>User: Formatted fiscal summary table
```

---

## 4. Directory Structure & Module Breakdown

```
sat-data-pipeline/
├── sat_pipeline/             # Main Python package
│   ├── parser.py             # XML schema and namespace resolver for CFDI 3.3/4.0
│   ├── models.py             # Pydantic schemas (Voucher, Issuer, Receiver, Tax)
│   ├── storage.py            # SQLite/DuckDB relational database manager
│   ├── analytics.py          # Fiscal reconciliation, tax calculations, reports
│   └── cli.py                # Command-line interface for batch processing
├── tests/                    # Automated unit and integration test suite
│   ├── test_parser.py        # Parser assertions on sample vouchers
│   ├── test_storage.py       # Upsert, query, and constraint test cases
│   └── test_analytics.py     # Fiscal arithmetic and reconciliation tests
├── data/samples/             # Canonical test XML samples
├── pyproject.toml            # Project build configuration and dependencies
└── requirements.txt          # Python runtime requirements
```
