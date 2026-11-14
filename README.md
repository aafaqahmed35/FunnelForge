# FunnelForge

**FunnelForge** is a lightweight, modular marketing data analytics pipeline designed to ingest, model, and analyze multi-channel digital marketing campaigns, customer acquisition funnels, and conversion events.

---

## 1. Project Overview

FunnelForge establishes a robust data foundation for marketing analytics. In **Phase 1 (P1 — Data Foundation & Ingestion)**, the system provides:
- A relational PostgreSQL schema for raw marketing data with referential integrity and domain constraints.
- A synthetic data generator producing realistic, clean marketing datasets across campaigns, customers, and funnel events.
- An idempotent, transactional CSV ingestion engine built with Pandas and Psycopg 3.
- A command-line interface supporting end-to-end execution and individual stage isolation.
- A unit test suite verifying data integrity, schema validation, and database operations without requiring a live database.

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
+-----------------------------------------------------------+
|                     FunnelForge P1                        |
+-----------------------------------------------------------+

   [Synthetic Generator] (Configurable Seed)
             |
             v
   +-------------------+  +-------------------+  +-------------------+
   |   campaigns.csv   |  |   customers.csv   |  |    events.csv     |
   |    (20 records)   |  |  (1,000 records)  |  |  (10,000 records) |
   +-------------------+  +-------------------+  +-------------------+
             |                      |                      |
             +----------------------+----------------------+
                                    |
                                    v
                         [Pandas CSV Ingestion]
                     (Validation & Type Sanitization)
                                    |
                                    v
                     [Transactional Table Replacement]
                 (TRUNCATE CASCADE inside atomic transaction)
                                    |
                                    v
                           [psycopg executemany]
                                    |
                                    v
                    +-------------------------------+
                    |     PostgreSQL (Raw Layer)    |
                    |  - raw_campaigns              |
                    |  - raw_customers              |
                    |  - raw_events                 |
                    +-------------------------------+
```

### Ingestion Strategy: Transactional Table Replacement
For this initial raw-data pipeline, FunnelForge uses **transactional table replacement** (`TRUNCATE TABLE raw_events, raw_customers, raw_campaigns CASCADE;` followed by bulk insertion within a single atomic database transaction).
- **Idempotency:** Running the ingestion workflow repeatedly produces the exact same clean state with zero duplicate records.
- **Referential Integrity:** Parent tables (`raw_campaigns`, `raw_customers`) are populated before the dependent child table (`raw_events`), ensuring all foreign key constraints are strictly satisfied.
- **Atomicity & Fault Tolerance:** If any error occurs during reading, validation, or loading, psycopg issues a complete rollback (`conn.rollback()`), preventing partial data states or orphaned rows.

---

## 4. Directory Structure

```
FunnelForge/
├── data/
│   └── raw/                       # Generated raw CSV datasets (gitignored)
│       └── .gitkeep
├── sql/
│   └── schema.sql                 # PostgreSQL DDL for raw tables and indexes
├── src/
│   └── funnelforge/
│       ├── __init__.py            # Package exports
│       ├── config.py              # Environment configuration & DB settings
│       ├── database.py            # Psycopg connection context & DDL execution
│       ├── generator.py           # Synthetic data generation logic
│       ├── ingestion.py           # CSV validation & bulk transactional loading
│       └── main.py                # Unified CLI entry point
├── tests/
│   ├── __init__.py
│   ├── test_config.py             # Config & env parsing unit tests
│   ├── test_database.py           # Database connection & error handling tests
│   ├── test_generator.py          # Data generation, counts, & seed reproducibility tests
│   ├── test_ingestion.py          # CSV validation & mocked ingestion tests
│   └── test_main.py               # CLI argument & orchestration tests
├── .env.example                   # Sample environment configuration template
├── .gitignore                     # Git ignore rules (env, cache, raw CSVs)
├── requirements.txt               # Pinned project dependencies
└── README.md                      # Project documentation
```

---

## 5. Database Schema

The raw layer is defined in `sql/schema.sql` and consists of three tables:

### `raw_campaigns`
Stores marketing campaign definitions, budgets, and operational schedules.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `campaign_id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique campaign identifier (e.g., `CMP-001`) |
| `campaign_name` | `VARCHAR(255)` | `NOT NULL` | Descriptive campaign title |
| `channel` | `VARCHAR(50)` | `NOT NULL` | Marketing channel (`Email`, `Social Media`, `Search`, `Display`, `Referral`) |
| `budget` | `NUMERIC(12, 2)` | `NOT NULL`, `CHECK (budget >= 0)` | Allocated campaign budget in USD |
| `start_date` | `DATE` | `NOT NULL` | Campaign launch date |
| `end_date` | `DATE` | `NOT NULL` | Campaign conclusion date (`CHECK (end_date >= start_date)`) |

### `raw_customers`
Stores acquired customer profiles and initial attribution.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `customer_id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique customer identifier (e.g., `CUST-0001`) |
| `customer_name` | `VARCHAR(255)` | `NOT NULL` | Full customer name |
| `email` | `VARCHAR(255)` | `NOT NULL` | Customer contact email |
| `acquisition_source` | `VARCHAR(50)` | `NOT NULL` | First-touch acquisition channel |
| `signup_date` | `DATE` | `NOT NULL` | Account registration date |

### `raw_events`
Stores granular funnel engagement events with foreign key linkage to customers and campaigns.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `event_id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique event identifier (e.g., `EVT-00001`) |
| `customer_id` | `VARCHAR(64)` | `NOT NULL`, `REFERENCES raw_customers(customer_id) ON DELETE CASCADE` | Associated customer |
| `campaign_id` | `VARCHAR(64)` | `NOT NULL`, `REFERENCES raw_campaigns(campaign_id) ON DELETE CASCADE` | Associated campaign |
| `event_type` | `VARCHAR(20)` | `NOT NULL`, `CHECK IN ('impression', 'click', 'conversion')` | Interaction stage |
| `event_timestamp` | `TIMESTAMPTZ` | `NOT NULL` | UTC timestamp of interaction |
| `revenue` | `NUMERIC(12, 2)` | `CHECK` | Monetary value for conversions; `NULL` for impressions & clicks |

---

## 6. Dataset Descriptions

The synthetic generator produces exactly **11,020 records** across three files in `data/raw/`:

| Dataset | Target File | Record Count | Description |
| :--- | :--- | :--- | :--- |
| **Campaigns** | `data/raw/campaigns.csv` | **20** | 20 marketing campaigns across 5 core channels with realistic budgets ($5,000–$75,000) and date ranges. |
| **Customers** | `data/raw/customers.csv` | **1,000** | 1,000 customer accounts with unique IDs, names, emails, and acquisition sources. |
| **Events** | `data/raw/events.csv` | **10,000** | 10,000 funnel interactions (impressions, clicks, conversions) with realistic timestamps bounded by campaign duration, valid foreign keys, and positive revenue on conversions. |
| **Total** | | **11,020** | |

Reproducibility is guaranteed via a configurable random seed (default `42`).

---

## 7. Environment Configuration

1. Copy `.env.example` to create your local `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your PostgreSQL connection parameters:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=funnelforge
   DB_USER=postgres
   DB_PASSWORD=your_password

   # Optional: Full connection URL
   # DATABASE_URL=postgresql://postgres:your_password@localhost:5432/funnelforge

   DATA_DIR=data/raw
   RANDOM_SEED=42
   ```

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

### Execution Options

#### 1. Run Complete Pipeline (Generate + Init DB + Ingest)
```bash
python3 -m funnelforge.main
# Or explicitly:
python3 -m funnelforge.main --all
```

#### 2. Run Individual Operations
- **Generate synthetic CSVs only:**
  ```bash
  python3 -m funnelforge.main --generate --seed 42
  ```
- **Initialize database schema only:**
  ```bash
  python3 -m funnelforge.main --init-db
  ```
- **Ingest existing CSVs into database only:**
  ```bash
  python3 -m funnelforge.main --ingest
  ```

---

## 9. Testing Instructions

All unit tests use `pytest` and mock database interactions, ensuring tests execute quickly and reliably **without requiring a live PostgreSQL instance**:

```bash
PYTHONPATH=src pytest -v
```

### Test Coverage Highlights:
- **`test_generator.py`**: Verifies exact record counts (20, 1,000, 10,000), column presence, referential integrity across IDs, revenue constraints, and seed reproducibility.
- **`test_config.py`**: Validates environment variable parsing, default fallbacks, and connection string generation.
- **`test_database.py`**: Tests connection lifecycle, exception handling, rollback semantics, and idempotent schema execution.
- **`test_ingestion.py`**: Tests CSV validation, missing file handling, missing column validation, `NaN` to `None` SQL sanitization, transactional table replacement, and database error rollback.
- **`test_main.py`**: Validates command-line flags and pipeline orchestration.

---

## 10. Roadmap

- [x] **P1 — Data Foundation & Ingestion**
  - Project architecture, raw schema, synthetic generator (11,020 records), transactional bulk ingestion, unit test suite.
- [ ] **P2 — Data Cleaning & Quality Assurance**
  - Introduction of realistic dirty data, automated quality checks, anomaly detection, deduplication, and schema validation gates.
- [ ] **P3 — Transformation & Marketing Modeling**
  - Staging transformations, dbt/SQL modeling, attribution modeling (first-touch, last-touch, linear), and customer cohort analysis.
- [ ] **P4 — Analytics & Reporting Engine**
  - KPI calculation (CAC, ROAS, conversion rates, channel ROI), automated summary dashboards, and report generation.
