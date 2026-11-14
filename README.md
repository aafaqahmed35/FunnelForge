# FunnelForge

**FunnelForge** is an enterprise-grade, lightweight marketing data analytics pipeline designed to ingest, validate, model, analyze, and report on multi-channel marketing campaigns, customer acquisition funnels, and conversion events.

---

## 1. Project Overview & Motivation

Modern growth and performance marketing pipelines face severe data reliability challenges:
- **Corrupted Ingestion:** Ad networks and tracking pixels frequently emit malformed payloads, duplicate customer registrations, negative revenue values, and orphan events referencing non-existent campaigns.
- **Silent Metric Distortions:** When dirty tracking data enters reporting dashboards unchecked, critical business metrics—such as Return on Ad Spend (ROAS), Customer Acquisition Cost (CAC), and Click-Through Rate (CTR)—are silently skewed, causing misallocated marketing capital.
- **Lack of Governance & Traceability:** Traditional ETL scripts often discard invalid rows silently or fail catastrophically midway, providing neither visibility into data quality degradation nor safe transaction boundaries.

**FunnelForge** solves these challenges through an end-to-end, reproducible data engineering architecture:
1. **Raw Storage & Extraction:** Generates and ingests high-volume multi-channel marketing datasets (11,020 records across campaigns, customers, and events).
2. **Quality Assurance & Quarantine:** Validates records against strict business rules, partitioning data into accepted vs. rejected streams while persisting granular failure metadata to PostgreSQL `JSONB`.
3. **Advanced SQL Analytics:** Computes conversion funnels, channel efficiencies, customer lifetime values, and revenue trajectories using window functions and conditional aggregations.
4. **Automated Multi-Format Reporting:** Generates audit-ready reports across CSV, structured JSON, and terminal-friendly executive summaries.
5. **Operational Reliability:** Hardened with connection management, transaction rollbacks, idempotent table replacement, and standardized logging.

---

## 2. Architecture & End-to-End Data Flow

```
+---------------------------------------------------------------------------------------------------------+
|                                              FunnelForge                                                |
+---------------------------------------------------------------------------------------------------------+

                                    [Synthetic Data Generator]
                                    (Configurable Seed, Clean / Dirty)
                                                 |
                                                 v
                                     +-----------------------+
                                     |       data/raw/       |
                                     |  - campaigns.csv      |
                                     |  - customers.csv      |
                                     |  - events.csv         |
                                     +-----------------------+
                                                 |
                       +-------------------------+-------------------------+
                       | (Clean Mode)                                      | (Dirty Mode / All Runs)
                       v                                                   v
           +-----------------------+                           +-----------------------+
           |   P1: Raw Ingestion   |                           |  P2: Cleaning Engine  |
           |   - Schema Init       |                           |  - Normalization      |
           |   - Bulk Ingest       |                           |  - Format Checks      |
           +-----------------------+                           |  - Business Rules     |
                       |                                       |  - Referential Checks |
                       v                                       +-----------------------+
           +-----------------------+                                       |
           |    PostgreSQL: Raw    |                       +---------------+---------------+
           |    - raw_campaigns    |                       |                               |
           |    - raw_customers    |                 (ACCEPTED)                       (REJECTED)
           |    - raw_events       |                       v                               v
           +-----------------------+            +---------------------+         +---------------------+
                                                |   data/processed/   |         |   data/rejected/    |
                                                |   - campaigns.csv   |         |   - campaigns_rej   |
                                                |   - customers.csv   |         |   - customers_rej   |
                                                |   - events.csv      |         |   - events_rej      |
                                                +---------------------+         |   - quality issues  |
                                                           |                    +---------------------+
                                                           v                               |
                                                +---------------------+                    v
                                                |  PostgreSQL:        |         +---------------------+
                                                |  Processed Layer    |         |  PostgreSQL:        |
                                                |  - processed_*      |         |  data_quality_      |
                                                +---------------------+         |  issues (JSONB)     |
                                                           |                    +---------------------+
                                                           v
                                          +---------------------------------+
                                          |    P3: SQL Analytics Layer      |
                                          |  - Campaign Performance (ROAS)  |
                                          |  - Channel Comparison & Ranks   |
                                          |  - Funnel Conversion Drop-off   |
                                          |  - Customer Lifetime & Repeats  |
                                          |  - Monthly Revenue Progression  |
                                          +---------------------------------+
                                                           |
                                                           v
                                          +---------------------------------+
                                          |  P4: Automated Reporting Engine |
                                          |  - ReportGenerator Service      |
                                          +---------------------------------+
                                                           |
                          +--------------------------------+-------------------------------+
                          |                                |                               |
                          v                                v                               v
                +--------------------+           +--------------------+          +--------------------+
                |    CSV Exports     |           |    JSON Export     |          |     TXT Report     |
                | - campaign_perf    |           | - funnel_report    |          | - executive_       |
                | - channel_perf     |           |   .json (metadata, |          |   summary.txt      |
                | - customer_anal    |           |   quality, metrics)|          |   (terminal ready) |
                | - revenue_anal     |           +--------------------+          +--------------------+
                +--------------------+
```

---

## 3. Technology Stack & Dependencies

- **Language:** Python 3.11+ (Tested and certified on Python 3.13)
- **Data Manipulation:** [Pandas](https://pandas.pydata.org/) (v2.2+)
- **Relational Database:** [PostgreSQL](https://www.postgresql.org/) (v14+)
- **Database Driver:** [Psycopg 3](https://www.psycopg.org/psycopg3/) (`psycopg[binary]>=3.2.0`) with context managers, connection pooling, and `dict_row` factories.
- **Environment Management:** [python-dotenv](https://github.com/theskumar/python-dotenv)
- **Automated Testing:** [pytest](https://docs.pytest.org/) (v8.0+)
- **Logging:** Python Standard Library `logging` configured with dual-destination streaming (stdout + rotating file).

---

## 4. Database Design & Schemas

The database architecture is partitioned into two distinct physical schemas across three operational layers:

### A. Raw Data Layer ([sql/schema.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/schema.sql))
Maintains raw auditability of inbound source files:
- **`raw_campaigns`**: Primary key `campaign_id` (VARCHAR), `campaign_name`, `channel`, `budget` (NUMERIC >= 0), `start_date`, `end_date`, and date integrity constraints (`end_date >= start_date`).
- **`raw_customers`**: Primary key `customer_id` (VARCHAR), `customer_name`, `email`, `acquisition_source`, and `signup_date`.
- **`raw_events`**: Primary key `event_id` (VARCHAR), foreign keys to `raw_customers` and `raw_campaigns`, `event_type` check constraint (`impression`, `click`, `conversion`), `event_timestamp` (TIMESTAMPTZ), and conditional revenue check constraints.

### B. Processed Data Layer ([sql/p2_schema.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/p2_schema.sql))
Stores clean, validated, and normalized marketing records:
- **`processed_campaigns`**: Validated marketing campaigns with verified budget boundaries and chronological intervals.
- **`processed_customers`**: Deduplicated customer entities with validated email addresses and standardized acquisition sources.
- **`processed_events`**: Verified conversion events with guaranteed referential integrity linking to existing processed customers and campaigns.

### C. Data Quality Audit Layer ([sql/p2_schema.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/p2_schema.sql))
- **`data_quality_issues`**: Quarantines rejected records with full audit traceability:
  - `issue_id`: SERIAL PRIMARY KEY.
  - `source_dataset`: Identifies originating CSV (`campaigns`, `customers`, `events`).
  - `record_id`: Offending record ID when extractable.
  - `failure_reasons`: PostgreSQL `TEXT[]` array capturing all triggered rule violations.
  - `raw_record`: PostgreSQL `JSONB` preserving the exact inbound payload for inspection.
  - `created_at`: TIMESTAMPTZ capture timestamp.

### Indexing & Performance Optimizations
- B-tree indexes on foreign keys (`idx_proc_events_cust`, `idx_proc_events_camp`).
- Temporal composite indexes on event timestamps and types (`idx_proc_events_type_time`).
- Specialized indexes on JSONB and audit logs (`idx_dq_dataset`, `idx_dq_record_id`).

---

## 5. Synthetic Data Generation

The synthetic generator ([src/funnelforge/generator.py](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/src/funnelforge/generator.py)) produces realistic, multi-touch digital marketing records across two deterministic modes:

| Dataset | Clean Volume | Dirty Volume | Description & Key Attributes |
| :--- | :---: | :---: | :--- |
| **Campaigns** | 20 | 20 | Paid channels (Email, Social Media, Search, Display, Referral), budgets (\$5,000–\$75,000), date windows. |
| **Customers** | 1,000 | 1,000 | First & last names, email addresses, 7 acquisition channels, 2024 signup dates. |
| **Events** | 10,000 | 10,000 | Multi-touch customer interactions: Impressions (60%), Clicks (25%), Conversions (15%) with conversion revenue (\$10–\$500). |
| **Total** | **11,020** | **11,020** | Controlled via `--seed` (default: 42) for 100% reproducible test scenarios. |

### Controlled Defect Injection (Dirty Mode)
When running with `--dirty`, intentional anomalies are deterministically injected to test quality gates:
1. **Missing Required Fields:** Null campaign names, missing customer names, omitted campaign IDs.
2. **Format Violations:** Corrupted email addresses (missing `@`, spaces, invalid domains), unparseable timestamps.
3. **Duplicate Entities:** Injected duplicate customer IDs with conflicting signup metadata.
4. **Business Rule Violations:** Campaign end dates preceding start dates, negative conversion revenue, non-conversion events carrying revenue.
5. **Orphan Records:** Events referencing non-existent campaigns (`CMP-999`) or deleted customers (`CUST-9999`).

---

## 6. Data Quality & Cleaning Engine

The cleaning engine ([src/funnelforge/cleaning.py](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/src/funnelforge/cleaning.py), [validation.py](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/src/funnelforge/validation.py), [quality.py](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/src/funnelforge/quality.py)) enforces a zero-tolerance policy against bad data entering the analytics layer:

```
           +-----------------------------------------------------------+
           |                      Raw Record Input                     |
           +-----------------------------------------------------------+
                                         |
                                         v
           +-----------------------------------------------------------+
           | 1. Missing Values: Reject missing IDs / required fields   |
           +-----------------------------------------------------------+
                                         |
                                         v
           +-----------------------------------------------------------+
           | 2. Formatting: Validate RFC-compliant email, dates & nums  |
           +-----------------------------------------------------------+
                                         |
                                         v
           +-----------------------------------------------------------+
           | 3. Business Rules: Check date order, revenue > 0, types   |
           +-----------------------------------------------------------+
                                         |
                                         v
           +-----------------------------------------------------------+
           | 4. Deduplication: Detect duplicate customer / event IDs   |
           +-----------------------------------------------------------+
                                         |
                                         v
           +-----------------------------------------------------------+
           | 5. Referential Integrity: Verify foreign key links        |
           +-----------------------------------------------------------+
                                         |
                        +----------------+----------------+
                        |                                 |
                   (All Pass)                       (Any Failure)
                        v                                 v
           +-------------------------+       +-------------------------+
           |    ACCEPTED STREAM      |       |    REJECTED STREAM      |
           | - data/processed/*.csv  |       | - data/rejected/*.csv   |
           | - processed_* tables    |       | - data_quality_issues   |
           +-------------------------+       +-------------------------+
```

### Rejection Issue Categorization
1. **Missing Required Fields:** Blank IDs, empty names, omitted channels.
2. **Invalid Format:** Regex-validated email formats, ISO-8601 timestamps, valid numerical types.
3. **Business Rule Violation:** Negative revenue, invalid event types (`purchase`, `view`), campaign date inversion.
4. **Duplicate Record:** First-seen customer ID retained; subsequent conflicting duplicates quarantined.
5. **Referential Integrity:** Events referencing unaccepted or missing customer or campaign IDs.

---

## 7. SQL Analytics & Business Logic

The analytical queries in [sql/analytics/](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/analytics/) provide executive intelligence across five key dimensions:

### 1. Macro Conversion Funnel ([conversion_analysis.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/analytics/conversion_analysis.sql))
Tracks the drop-off across marketing stages using conditional `CASE WHEN` aggregations:
- **Impression-to-Click Rate (CTR):** $\frac{\text{Clicks}}{\text{NULLIF}(\text{Impressions}, 0)} \times 100$
- **Click-to-Conversion Rate:** $\frac{\text{Conversions}}{\text{NULLIF}(\text{Clicks}, 0)} \times 100$
- **Overall Conversion Rate:** $\frac{\text{Conversions}}{\text{NULLIF}(\text{Impressions}, 0)} \times 100$

### 2. Campaign Performance & ROAS ([campaign_performance.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/analytics/campaign_performance.sql))
Evaluates individual campaign efficiency while guarding against division by zero:
- **Return on Ad Spend (ROAS):** $\frac{\text{Total Revenue}}{\text{NULLIF}(\text{Budget}, 0)}$

### 3. Channel Performance & Ranking ([channel_performance.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/analytics/channel_performance.sql))
Ranks marketing channels using window functions:
- `DENSE_RANK() OVER (ORDER BY total_revenue DESC)` for revenue leadership.
- `DENSE_RANK() OVER (ORDER BY conversions DESC)` for volume efficiency.

### 4. Customer Lifetime Value & Cohorts ([customer_analysis.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/analytics/customer_analysis.sql))
Segments high-value customers and identifies repeat purchasers using `HAVING COUNT(conversions) > 1` alongside acquisition channel revenue contributions.

### 5. Revenue Trajectory & Trends ([revenue_analysis.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/analytics/revenue_analysis.sql))
Computes monthly revenue progression via `DATE_TRUNC('month', event_timestamp)`, Average Order Value (AOV), and cumulative revenue share percentages.

---

## 8. Reporting & Export Engine

FunnelForge includes an automated reporting engine ([src/funnelforge/reporting.py](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/src/funnelforge/reporting.py)) that outputs analytical findings and data-quality governance summaries in three standard formats:

```
reports/generated/
├── campaign_performance.csv    # Individual campaign financial and conversion metrics
├── channel_performance.csv     # Aggregated channel spend, conversion volume, and ROAS
├── customer_analysis.csv       # High-value customers, order volume, and repeat status
├── revenue_analysis.csv        # Top revenue drivers and cumulative portfolio contribution
├── funnel_report.json          # Consolidated structured report with full metadata
└── executive_summary.txt       # Clean, human-readable terminal summary
```

### Export Formats:
1. **Tabular CSV Exports:** Clean CSV files exported directly from Pandas DataFrames for ingestion into BI tools (Tableau, PowerBI, Looker).
2. **Consolidated Structured JSON (`funnel_report.json`):** Comprehensive JSON artifact containing run metadata, complete data-quality governance metrics, and full marketing analytics. Uses custom serialization to safely handle `datetime`, `date`, `Decimal`, and `Path` objects.
3. **Executive Summary TXT (`executive_summary.txt`):** Formatted text document summarizing scale, traffic, top campaigns, revenue leaders, and data governance observations.

---

## 9. Reliability & Pipeline Hardening

1. **Transactional Boundaries & Safe Rollbacks:** Database writes are wrapped in atomic transactions (`BEGIN ... COMMIT`). If an unexpected error occurs during data ingestion, table replacement, or processed persistence, a full `ROLLBACK` is executed, preventing database corruption.
2. **Safe Idempotent Execution:** Database schemas use `CREATE TABLE IF NOT EXISTS`, and ingestion utilizes transactional table replacement (`TRUNCATE TABLE ... CASCADE`), allowing repeated executions without duplicate records.
3. **Strict Connection Management:** All PostgreSQL interactions utilize Python context managers (`with get_connection(...) as conn`), guaranteeing connections and cursors are cleanly released even upon fatal exceptions.
4. **Empty Dataset Handling:** Analytics repositories and reporting services feature defensive fallbacks returning typed empty structures rather than throwing runtime exceptions when tables contain zero rows.
5. **JSONB Serialization Sanitization:** Rejection payloads containing Pandas `NaN` or `pd.NA` tokens are recursively sanitized to Python `None` to prevent PostgreSQL JSON syntax violations.

---

## 10. Standardized Logging

FunnelForge uses a centralized logging architecture ([src/funnelforge/logging.py](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/src/funnelforge/logging.py)) providing clear operational visibility:
- **Format:** `[%(asctime)s] [%(levelname)-7s] [%(name)s]: %(message)s`
- **Dual Destinations:**
  - **Console (stdout):** Real-time operational feedback.
  - **Log File (`logs/funnelforge.log`):** Persistent, append-only log file for auditing and debugging.
- **Idempotent Setup:** Handlers are cleanly reset on re-initialization to prevent duplicate log lines.
- **Configurable Levels:** Supported via `--log-level [DEBUG|INFO|WARNING|ERROR]`.

---

## 11. Project Directory Structure

```
FunnelForge/
├── data/
│   ├── raw/                       # Raw input CSV datasets (gitignored)
│   │   └── .gitkeep
│   ├── processed/                 # Clean, validated CSV datasets (gitignored)
│   │   └── .gitkeep
│   └── rejected/                  # Quarantined invalid records & audits (gitignored)
│       └── .gitkeep
├── logs/
│   ├── funnelforge.log            # Standardized application execution log (gitignored)
│   └── .gitkeep
├── reports/
│   └── generated/                 # Generated CSV, JSON, and TXT reports (gitignored)
│       ├── campaign_performance.csv
│       ├── channel_performance.csv
│       ├── customer_analysis.csv
│       ├── executive_summary.txt
│       ├── funnel_report.json
│       ├── revenue_analysis.csv
│       └── .gitkeep
├── sql/
│   ├── schema.sql                 # P1 DDL: raw landing tables & constraints
│   ├── p2_schema.sql              # P2 DDL: processed tables & data_quality_issues
│   └── analytics/                 # P3 Analytical SQL Queries
│       ├── campaign_performance.sql
│       ├── channel_performance.sql
│       ├── conversion_analysis.sql
│       ├── customer_analysis.sql
│       └── revenue_analysis.sql
├── src/
│   └── funnelforge/
│       ├── __init__.py            # Package exports and version metadata
│       ├── analytics.py           # Analytics coordinator & CLI reporting
│       ├── analytics_repository.py# SQL execution layer with psycopg dict_row
│       ├── analytics_service.py   # Business logic & structured formatting
│       ├── cleaning.py            # Data cleaning engine & record separation
│       ├── config.py              # Environment configuration & DB settings
│       ├── database.py            # Psycopg connection context & DDL execution
│       ├── generator.py           # Synthetic generator (clean and dirty modes)
│       ├── ingestion.py           # Raw CSV validation & bulk transactional loading
│       ├── logging.py             # Standardized dual-destination logging
│       ├── main.py                # Master CLI entry point (P1, P2, P3, P4)
│       ├── pipeline.py            # Master end-to-end pipeline orchestrator
│       ├── quality.py             # Data quality metrics & summary reporting
│       ├── reporting.py           # Multi-format report export engine
│       └── validation.py          # Explicit validation rules & categorization
├── tests/
│   ├── __init__.py
│   ├── test_analytics_reporting.py# Terminal analytics reporting tests
│   ├── test_analytics_repository.py# Repository execution & SQL error handling tests
│   ├── test_analytics_service.py  # Service DataFrame & metric calculation tests
│   ├── test_cleaning.py           # Cleaning, deduplication, & file export tests
│   ├── test_config.py             # Config & env parsing unit tests
│   ├── test_database.py           # Database connection & rollback tests
│   ├── test_dirty_generator.py    # Dirty data generation & reproducibility tests
│   ├── test_generator.py          # Data generation counts & seed tests
│   ├── test_ingestion.py          # CSV validation & mocked ingestion tests
│   ├── test_logging.py            # Logger setup, formatting, & file handling tests
│   ├── test_main.py               # P1 CLI argument & orchestration tests
│   ├── test_p2_cli.py             # P2 CLI argument & quality pipeline tests
│   ├── test_p2_database.py        # P2 DDL & transactional persistence tests
│   ├── test_p3_cli.py             # P3 CLI analytics argument tests
│   ├── test_p4_cli.py             # P4 CLI pipeline & reporting argument tests
│   ├── test_pipeline.py           # End-to-end orchestrator & status summary tests
│   ├── test_quality.py            # Quality metrics & summary calculations
│   ├── test_reporting.py          # Report export, JSON serializer, & fallback tests
│   └── test_validation.py         # Explicit validation rules & multi-error tests
├── .env.example                   # Sample environment configuration template
├── .gitignore                     # Git ignore rules (env, cache, data, reports, logs)
├── requirements.txt               # Pinned project dependencies
└── README.md                      # Comprehensive project documentation
```

---

## 12. Getting Started & Installation

### Prerequisites
- **Python 3.11+**
- **PostgreSQL 14+** (running locally or accessible via network)

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/aafaqahmed35/FunnelForge.git
cd FunnelForge

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set your PostgreSQL credentials:
```bash
cp .env.example .env
```

---

## 13. Environment Configuration

Edit `.env` to match your local PostgreSQL configuration:
```env
# Database Credentials
DB_HOST=localhost
DB_PORT=5432
DB_NAME=funnelforge
DB_USER=postgres
DB_PASSWORD=your_password

# Or full connection URL
# DATABASE_URL=postgresql://postgres:your_password@localhost:5432/funnelforge

# Execution Parameters
RANDOM_SEED=42
LOG_LEVEL=INFO

# Directory Configuration
DATA_DIR=data/raw
PROCESSED_DATA_DIR=data/processed
REJECTED_DATA_DIR=data/rejected
REPORTS_DIR=reports/generated
LOGS_DIR=logs
```

Ensure the target PostgreSQL database exists:
```bash
createdb funnelforge
```

---

## 14. Usage & CLI Reference

FunnelForge provides a unified command-line interface via `python -m funnelforge.main`:

### Master Pipeline Execution (P4)
Run the entire end-to-end pipeline (generation $\rightarrow$ ingestion $\rightarrow$ cleaning $\rightarrow$ analytics $\rightarrow$ reporting):

```bash
# Clean Mode (Production workflow: 100% acceptance rate)
python -m funnelforge.main --pipeline

# Dirty Mode (Audit & Governance workflow: with intentional defect quarantine)
python -m funnelforge.main --pipeline --dirty

# Custom Seed and Log Level
python -m funnelforge.main --pipeline --dirty --seed 123 --log-level DEBUG
```

### Standalone Report Export (P4)
Generate CSV, JSON, and TXT reports from current PostgreSQL data:
```bash
# Export to default directory (reports/generated/)
python -m funnelforge.main --report

# Export to a custom destination directory
python -m funnelforge.main --report --reports-dir reports/custom
```

### Marketing Analytics Dashboard (P3)
```bash
# Render all analytical tables
python -m funnelforge.main --analytics all

# Specific analytical queries
python -m funnelforge.main --analytics campaigns
python -m funnelforge.main --analytics channels
python -m funnelforge.main --analytics funnel
python -m funnelforge.main --analytics customers
python -m funnelforge.main --analytics revenue
```

### Data Quality & Cleaning Layer (P2)
```bash
# Run P2 quality pipeline on dirty synthetic data
python -m funnelforge.main --p2 --dirty

# Clean existing raw CSV files without regenerating
python -m funnelforge.main --clean

# Initialize P2 PostgreSQL schemas only
python -m funnelforge.main --init-p2-db
```

### Data Foundation & Raw Ingestion (P1)
```bash
# Run complete P1 raw workflow
python -m funnelforge.main --all

# Modular P1 operations
python -m funnelforge.main --generate
python -m funnelforge.main --init-db
python -m funnelforge.main --ingest
```

---

## 15. Testing Suite & Verification

The automated test suite contains **85 comprehensive unit and integration tests** covering all four project milestones. All tests utilize mocks to execute rapidly without requiring an active PostgreSQL connection:

```bash
PYTHONPATH=src pytest -v
```

### Test Suite Distribution (85 Passing Tests):
- **Pipeline Orchestration (`test_pipeline.py`, `test_p4_cli.py`):** Clean and dirty mode execution, raw table skip logic, dynamic summary formatting, error propagation.
- **Reporting Engine (`test_reporting.py`):** Multi-format export, JSON serialization for `Decimal`/`date`/`Path`, executive summary generation, empty dataset fallbacks.
- **Logging Architecture (`test_logging.py`):** Dual-destination handlers, idempotency, log level formatting.
- **Analytics Services (`test_analytics_service.py`, `test_analytics_repository.py`, `test_analytics_reporting.py`, `test_p3_cli.py`):** SQL queries, window functions, DataFrame conversions, terminal dashboards.
- **Data Quality & Validation (`test_validation.py`, `test_quality.py`, `test_cleaning.py`, `test_dirty_generator.py`, `test_p2_database.py`):** Multi-error rules, deduplication, referential integrity, quarantine exports, JSONB persistence.
- **Foundational Layer (`test_generator.py`, `test_ingestion.py`, `test_database.py`, `test_config.py`, `test_main.py`):** Reproducibility, CSV schema validation, connection lifecycle.

---

## 16. Sample Pipeline Results & Metrics

### Clean Mode Execution (`python -m funnelforge.main --pipeline`)
```
================================================
             FUNNELFORGE PIPELINE
================================================
Raw Records Processed:         11,020
Accepted Records:              11,020
Rejected Records:                   0
Data Acceptance Rate:          100.0%
Total Campaigns:                   20
Total Customers:                1,000
Total Events:                  10,000
Total Conversion Revenue:    $133,196.05
Overall Conversion Rate:        7.10%
Reports Generated:                  6
Pipeline Status: SUCCESS
================================================
```

### Dirty Mode Execution (`python -m funnelforge.main --pipeline --dirty`)
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

================================================
             FUNNELFORGE PIPELINE
================================================
Raw Records Processed:         11,020
Accepted Records:               9,444
Rejected Records:               1,576
Data Acceptance Rate:           85.7%
Total Campaigns:                   17
Total Customers:                  969
Total Events:                   8,458
Total Conversion Revenue:    $110,889.16
Overall Conversion Rate:        7.27%
Reports Generated:                  6
Pipeline Status: SUCCESS
================================================
```

---

## 17. Current Limitations & Future Improvements

### Current Design Decisions & Trade-Offs
- **In-Memory Cleaning via Pandas:** The current cleaning layer loads datasets into memory for fast vectorized validation. While optimal for batch files under ~5M records, scaling to hundreds of millions of events would necessitate distributed processing (Apache Spark / Polars) or stream processing (Kafka / Flink).
- **Single-Node PostgreSQL Analytics:** All analytical computations run directly within PostgreSQL. For petabyte-scale data lakes, transitioning the SQL analytics layer to Snowflake, BigQuery, or DuckDB with dbt orchestration would be the natural evolution.
- **Batch Processing Model:** Ingestion operates on scheduled batch intervals rather than real-time event streaming.
- **Macro Event Attribution:** Conversion attribution is currently evaluated on an aggregated portfolio basis. Session-based multi-touch attribution (first-touch, linear, time-decay, Markov chain models) would provide deeper customer journey granularity.

### Roadmap for Production Evolution
1. **Orchestration Integration:** Package pipeline jobs as Directed Acyclic Graphs (DAGs) using Apache Airflow, Prefect, or Dagster.
2. **dbt Transformation Layer:** Convert `sql/analytics/` into version-controlled dbt models with automated schema and freshness tests.
3. **Containerization & CI/CD:** Package the pipeline into a Docker container with automated GitHub Actions testing and schema migrations.
4. **Data Contract Enforcement:** Integrate Great Expectations or Pydantic models for automated upstream schema contract enforcement.

---

## 18. Milestone Completion Matrix

| Milestone | Scope & Deliverables | Status |
| :--- | :--- | :---: |
| **P1 — Data Foundation & Ingestion** | Database schema, synthetic generator (11,020 clean rows), bulk transactional ingestion, psycopg connectivity, pytest suite. | **Complete** |
| **P2 — Data Cleaning & Quality Assurance** | Dirty data generator, multi-rule validation engine, accepted/rejected separation, PostgreSQL processed layer & JSONB issue logging, dynamic quality reports. | **Complete** |
| **P3 — SQL Analytics & Business Metrics** | Analytical layer on processed data, campaign performance, channel efficiency, conversion funnels, customer LTV, window functions, terminal dashboard. | **Complete** |
| **P4 — Reporting, Reliability & Documentation** | Automated multi-format reporting (CSV, JSON, TXT), master pipeline orchestrator, dynamic execution summary, dual logging, 85 unit tests, comprehensive architectural documentation. | **Complete** |
