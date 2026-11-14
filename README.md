# FunnelForge

**FunnelForge** is a lightweight, modular marketing data analytics pipeline designed to ingest, validate, model, and analyze multi-channel digital marketing campaigns, customer acquisition funnels, and conversion events.

---

## 1. Project Overview

FunnelForge establishes a reliable data foundation for marketing analytics through a two-phase architecture:
- **Phase 1 (P1 — Data Foundation & Ingestion):** Relational PostgreSQL raw storage, reproducible synthetic generation (11,020 records), and transactional bulk CSV ingestion.
- **Phase 2 (P2 — Data Cleaning & Quality Assurance):** An automated data-quality validation engine that transforms raw marketing data into trustworthy analytics-ready datasets, separates accepted from rejected records, captures multi-error lineage in PostgreSQL JSONB, and compiles dynamic data quality summaries.

### Central Distinctions: Raw vs. Processed vs. Rejected Records

| Category | Storage Location | State & Purpose |
| :--- | :--- | :--- |
| **Raw Records** | `data/raw/*.csv`<br>`raw_*` PostgreSQL tables | Faithful replica of incoming source data. Ingested as-is without filtering or validation to ensure raw auditability. |
| **Processed Records** | `data/processed/*.csv`<br>`processed_*` PostgreSQL tables | Validated, normalized, deduplicated records that have satisfied every schema constraint, business rule, and referential integrity check. |
| **Rejected Records** | `data/rejected/*_rejected.csv`<br>`data_quality_issues` PostgreSQL table | Corrupt or invalid records quarantined with source dataset, record identifier, all failure reasons, original raw payload in JSONB, and detection timestamp. |

---

## 2. Technology Stack

- **Language:** Python 3.11+ (Tested on Python 3.13)
- **Data Manipulation:** [Pandas](https://pandas.pydata.org/) (v2.2+)
- **Database:** [PostgreSQL](https://www.postgresql.org/) (v14+)
- **Database Driver:** [Psycopg 3](https://www.psycopg.org/psycopg3/) (`psycopg[binary]`)
- **Environment Management:** [python-dotenv](https://github.com/theskumar/python-dotenv)
- **Testing Framework:** [pytest](https://docs.pytest.org/) (v8+)

---

## 3. Architecture & Data Flow

```
+-------------------------------------------------------------------------------+
|                                  FunnelForge                                  |
+-------------------------------------------------------------------------------+

                      [Synthetic Data Generator]
                       (Clean or Dirty Mode: Seed)
                                  |
                                  v
                      +------------------------+
                      |       data/raw/        |
                      |  - campaigns.csv       |
                      |  - customers.csv       |
                      |  - events.csv          |
                      +------------------------+
                                  |
            +---------------------+---------------------+
            | (P1: Raw Ingestion)                       | (P2: Quality Pipeline)
            v                                           v
+------------------------+                  +------------------------+
|   Transactional Raw    |                  |   Cleaning Engine      |
|   Table Replacement    |                  |   - Normalization      |
+------------------------+                  |   - Validation Rules   |
            |                               |   - Deduplication      |
            v                               +------------------------+
+------------------------+                              |
| PostgreSQL: Raw Layer  |              +---------------+---------------+
|  - raw_campaigns       |              |                               |
|  - raw_customers       |        (ACCEPTED)                       (REJECTED)
|  - raw_events          |              v                               v
+------------------------+   +--------------------+          +--------------------+
                             |  data/processed/   |          |   data/rejected/   |
                             |  - campaigns.csv   |          |  - campaigns_rej   |
                             |  - customers.csv   |          |  - customers_rej   |
                             |  - events.csv      |          |  - events_rej      |
                             +--------------------+          |  - issues audit    |
                                        |                    +--------------------+
                                        v                               |
                             +--------------------+                     v
                             |  PostgreSQL:       |          +--------------------+
                             |  Processed Layer   |          |  PostgreSQL:       |
                             |  - processed_*     |          |  data_quality_     |
                             +--------------------+          |  issues (JSONB)    |
                                                             +--------------------+
```

---

## 4. Directory Structure

```
FunnelForge/
├── data/
│   ├── raw/                       # Raw input CSV datasets (gitignored)
│   │   └── .gitkeep
│   ├── processed/                 # Validated, clean CSV datasets (gitignored)
│   │   └── .gitkeep
│   └── rejected/                  # Quarantined CSV datasets & audit logs (gitignored)
│       └── .gitkeep
├── sql/
│   ├── schema.sql                 # P1 DDL: raw tables & indexes
│   └── p2_schema.sql              # P2 DDL: processed tables & data_quality_issues
├── src/
│   └── funnelforge/
│       ├── __init__.py            # Package exports
│       ├── cleaning.py            # Data cleaning engine & record separation
│       ├── config.py              # Environment configuration & DB settings
│       ├── database.py            # Psycopg connection context & DDL execution
│       ├── generator.py           # Synthetic generator (clean and dirty modes)
│       ├── ingestion.py           # Raw CSV validation & bulk transactional loading
│       ├── main.py                # Unified CLI entry point (P1 and P2)
│       ├── quality.py             # Data quality metrics & reporting
│       └── validation.py          # Explicit validation rules & categorization
├── tests/
│   ├── __init__.py
│   ├── test_cleaning.py           # Cleaning, deduplication, & file export tests
│   ├── test_config.py             # Config & env parsing unit tests
│   ├── test_database.py           # Database connection & error handling tests
│   ├── test_dirty_generator.py    # Dirty data generation & reproducibility tests
│   ├── test_generator.py          # Data generation, counts, & seed reproducibility tests
│   ├── test_ingestion.py          # CSV validation & mocked ingestion tests
│   ├── test_main.py               # P1 CLI argument & orchestration tests
│   ├── test_p2_cli.py             # P2 CLI argument & pipeline tests
│   ├── test_p2_database.py        # P2 DDL & transactional persistence tests
│   ├── test_quality.py            # Quality metrics & summary calculations
│   └── test_validation.py         # Explicit validation rules & multi-error tests
├── .env.example                   # Sample environment configuration template
├── .gitignore                     # Git ignore rules (env, cache, all CSV data)
├── requirements.txt               # Pinned project dependencies
└── README.md                      # Project documentation
```

---

## 5. Database Schema

The database schema is organized into two layers:

### Raw Layer (`sql/schema.sql`)
- `raw_campaigns`: Stores raw campaign records (`campaign_id` PK, name, channel, budget, dates).
- `raw_customers`: Stores raw customer profiles (`customer_id` PK, name, email, acquisition source, signup date).
- `raw_events`: Stores raw funnel events (`event_id` PK, customer/campaign FKs, event type, timestamp, revenue).

### Processed & Quality Assurance Layer (`sql/p2_schema.sql`)
- `processed_campaigns`: Stores validated, clean campaigns (`campaign_id` PK, name, channel, budget $\ge 0$, start date, end date $\ge$ start date).
- `processed_customers`: Stores validated, clean customer profiles (`customer_id` PK, name, formatted email, acquisition source, signup date).
- `processed_events`: Stores validated, clean funnel events with foreign keys referencing `processed_customers` and `processed_campaigns`.
- `data_quality_issues`: Audit trail table capturing quarantined records:
  - `issue_id`: `BIGSERIAL PRIMARY KEY`
  - `source_dataset`: `VARCHAR(50) NOT NULL` (e.g., `campaigns`, `customers`, `events`)
  - `record_id`: `VARCHAR(64)` (primary identifier or `UNKNOWN`)
  - `rejection_reason`: `TEXT NOT NULL` (semicolon-separated list of all captured errors)
  - `original_record`: `JSONB NOT NULL` (complete raw payload for auditability)
  - `detected_at`: `TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`

---

## 6. Validation Rules & Rejection Handling

Every incoming record is evaluated through the validation engine (`src/funnelforge/validation.py`). If one or more rules fail, the record is flagged as **REJECTED**, and **all** failure reasons are captured:

| Category | Validation Rule | Impact on Failure |
| :--- | :--- | :--- |
| **Missing Required Fields** | Primary keys, campaign name, customer name, email, channel, acquisition source, event type, dates must not be null/blank. | Quarantined to `rejected/` and `data_quality_issues` |
| **Duplicate Detection** | Duplicate primary keys (`campaign_id`, `customer_id`, `event_id`). First occurrence accepted; subsequent occurrences rejected. | Preserves first instance, rejects subsequent duplicates |
| **Format Validation** | Email format must match RFC standard regex; dates and timestamps must be valid ISO-8601 strings; numeric values must be parseable. | Quarantined with specific format violation message |
| **Business Rules** | Campaign `end_date` $\ge$ `start_date`; budget $\ge 0$; revenue $\ge 0$; non-conversion events must have `NULL` revenue; conversion events must have valid positive revenue. | Quarantined with business logic violation reason |
| **Referential Integrity** | Event `customer_id` and `campaign_id` must exist within the set of **accepted** parent records. | Prevents orphaned records in processed layer |

---

## 7. Synthetic Data Generator Modes

The generator (`src/funnelforge/generator.py`) produces **11,020 records** across two deterministic modes:

- **Clean Mode (P1 default):** Produces pristine, valid records across all datasets with 0% defects.
- **Dirty Mode (P2 `--dirty`):** Injects realistic, reproducible data quality defects:
  - Missing customer and campaign names
  - Invalid email formats
  - Duplicate customer and event records
  - Missing campaign identifiers
  - Invalid event types (`hover`, `bounce`, `purchase`)
  - Negative revenue values
  - Non-conversion events carrying revenue / conversion events missing revenue
  - Invalid timestamp formats
  - Events referencing nonexistent customers (`CUST-9999`) and campaigns (`CMP-999`)
  - Invalid campaign date ranges (`end_date < start_date`)

---

## 8. Installation & Execution

### Prerequisites
- Python 3.11+
- PostgreSQL (for live database ingestion)

### Virtual Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Complete P2 Quality Workflow (Single Command)
To run the full end-to-end P2 pipeline with dirty data generation, schema initialization, cleaning, file partitioning, database persistence, and quality reporting:
```bash
python3 -m funnelforge.main --p2 --dirty
```

### Additional Execution Commands

| Task | Command |
| :--- | :--- |
| **P1 End-to-End Pipeline** | `python3 -m funnelforge.main --all` |
| **Generate Clean CSVs Only** | `python3 -m funnelforge.main --generate --seed 42` |
| **Generate Dirty CSVs Only** | `python3 -m funnelforge.main --generate --dirty --seed 42` |
| **Clean Existing Raw CSVs** | `python3 -m funnelforge.main --clean` |
| **Clean Without DB (Files Only)** | `python3 -m funnelforge.main --clean --no-db` |
| **Initialize P1 Raw DB Schema** | `python3 -m funnelforge.main --init-db` |
| **Initialize P2 Processed DB Schema** | `python3 -m funnelforge.main --init-p2-db` |

---

## 9. Example Data Quality Report

When running the P2 quality pipeline in dirty mode (`python3 -m funnelforge.main --p2 --dirty`), FunnelForge outputs:

```
======================================================================
                     DATA QUALITY REPORT
======================================================================
Dataset            Examined   Accepted   Rejected    Acceptance Rate
----------------------------------------------------------------------
Campaigns                20         17          3              85.0%
Customers             1,000        969         31              96.9%
Events               10,000      8,458      1,542              84.6%
----------------------------------------------------------------------
Total                11,020      9,444      1,576              85.7%
======================================================================
Overall acceptance rate: 85.7%
Overall rejection rate:  14.3%

Issue Counts by Category:
  • Referential Integrity     : 1,374
  • Invalid Format            :   111
  • Business Rule Violation   :    84
  • Missing Required Fields   :    45
  • Duplicate Record          :    27

Issue Counts by Source Dataset:
  • events                    : 1,542
  • customers                 :    31
  • campaigns                 :     3

Top Rejection Reasons:
  • [496x] Referenced campaign_id 'CMP-003' does not exist in accepted campaigns
  • [479x] Referenced campaign_id 'CMP-013' does not exist in accepted campaigns
  • [75x] Referenced customer_id 'CUST-9999' does not exist in accepted customers
  • [75x] Referenced campaign_id 'CMP-999' does not exist in accepted campaigns
  • [30x] Non-conversion event of type 'click' must not have revenue (got 49.99)
======================================================================
```

---

## 10. Testing Instructions

All unit tests use `pytest` and mock database interactions. Unit tests execute in under 2 seconds without requiring a live PostgreSQL instance:

```bash
PYTHONPATH=src pytest -v
```

### Test Suite Summary:
- **`test_validation.py`:** Tests each validation rule independently, multiple errors per record, format checks, and categorization.
- **`test_cleaning.py`:** Tests normalization, customer/event deduplication, referential integrity isolation, and file persistence.
- **`test_dirty_generator.py`:** Tests clean vs. dirty mode generation, specific defect counts, and seed reproducibility.
- **`test_quality.py`:** Tests metric calculations, acceptance/rejection percentages, and report rendering.
- **`test_p2_database.py`:** Tests DDL execution, transactional table replacement, rollback on error, and JSONB issue persistence.
- **`test_p2_cli.py`:** Tests CLI flags (`--p2`, `--clean`, `--init-p2-db`, `--no-db`) and pipeline orchestration.
- **P1 Regression Suite:** Preserves all existing tests for P1 configuration, database connectivity, and raw ingestion.

---

## 11. Roadmap

- [x] **P1 — Data Foundation & Ingestion**
  - Project architecture, raw schema, synthetic generator (11,020 records), transactional bulk ingestion, unit test suite.
- [x] **P2 — Data Cleaning & Quality Assurance**
  - Dirty data generator, multi-rule validation engine, accepted/rejected partitioning, PostgreSQL processed layer & JSONB audit issues, dynamic data quality metrics.
- [ ] **P3 — Transformation & Marketing Modeling**
  - Staging transformations, dbt/SQL modeling, attribution modeling (first-touch, last-touch, linear), and customer cohort analysis.
- [ ] **P4 — Analytics & Reporting Engine**
  - KPI calculation (CAC, ROAS, conversion rates, channel ROI), automated summary dashboards, and report generation.
