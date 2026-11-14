# FunnelForge

**FunnelForge** is a lightweight, modular marketing data analytics pipeline designed to ingest, validate, model, and analyze multi-channel digital marketing campaigns, customer acquisition funnels, and conversion events.

---

## 1. Project Overview

FunnelForge establishes an end-to-end data pipeline across three foundational milestones:
- **Phase 1 (P1 — Data Foundation & Ingestion):** Relational PostgreSQL raw storage, reproducible synthetic generation (11,020 records), and transactional bulk CSV ingestion.
- **Phase 2 (P2 — Data Cleaning & Quality Assurance):** An automated data-quality validation engine that cleans raw marketing data, separates accepted from rejected records, captures multi-error lineage in PostgreSQL JSONB, and compiles dynamic data quality summaries.
- **Phase 3 (P3 — SQL Analytics & Business Metrics):** An analytical layer on top of validated PostgreSQL datasets providing actionable business intelligence across campaign performance, channel efficiency, conversion funnels, customer lifetime value, and revenue distribution.

### Data Layer Progression: Raw vs. Processed vs. Rejected

| Category | Storage Location | State & Purpose |
| :--- | :--- | :--- |
| **Raw Records** | `data/raw/*.csv`<br>`raw_*` PostgreSQL tables | Faithful replica of incoming source data. Ingested as-is without filtering or validation to ensure raw auditability. |
| **Processed Records** | `data/processed/*.csv`<br>`processed_*` PostgreSQL tables | Validated, normalized, deduplicated records that have satisfied every schema constraint, business rule, and referential integrity check. |
| **Rejected Records** | `data/rejected/*_rejected.csv`<br>`data_quality_issues` PostgreSQL table | Quarantined records with source dataset, record identifier, all failure reasons, original raw payload in JSONB, and detection timestamp. |
| **Analytical Layer** | `sql/analytics/*.sql`<br>`funnelforge.analytics` | Aggregations, window functions, and cohorts derived strictly from clean `processed_*` tables. |

---

## 2. Technology Stack

- **Language:** Python 3.11+ (Tested on Python 3.13)
- **Data Manipulation:** [Pandas](https://pandas.pydata.org/) (v2.2+)
- **Database:** [PostgreSQL](https://www.postgresql.org/) (v14+)
- **Database Driver:** [Psycopg 3](https://www.psycopg.org/psycopg3/) (`psycopg[binary]`)
- **Environment Management:** [python-dotenv](https://github.com/theskumar/python-dotenv)
- **Testing Framework:** [pytest](https://docs.pytest.org/) (v8+)

---

## 3. Architecture & Analytics Data Flow

```
+---------------------------------------------------------------------------------------+
|                                      FunnelForge                                      |
+---------------------------------------------------------------------------------------+

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
                                                |                    +--------------------+
                                                v
                               +----------------------------------+
                               |     P3: SQL Analytics Layer      |
                               |  - Campaign Performance (ROAS)   |
                               |  - Channel Comparison & Ranks    |
                               |  - Conversion Funnel Drop-off    |
                               |  - Customer Value & Repeaters    |
                               |  - Revenue Contribution & Trends |
                               +----------------------------------+
                                                |
                                                v
                               +----------------------------------+
                               |  Executive Terminal Dashboard    |
                               |  (python -m funnelforge --analytics)|
                               +----------------------------------+
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
│   ├── p2_schema.sql              # P2 DDL: processed tables & data_quality_issues
│   └── analytics/                 # P3 Analytical SQL Queries
│       ├── campaign_performance.sql
│       ├── channel_performance.sql
│       ├── conversion_analysis.sql
│       ├── customer_analysis.sql
│       └── revenue_analysis.sql
├── src/
│   └── funnelforge/
│       ├── __init__.py            # Package exports
│       ├── analytics.py           # Analytics coordinator & CLI reporting
│       ├── analytics_repository.py# SQL execution layer with psycopg dict_row
│       ├── analytics_service.py   # Business logic & structured formatting
│       ├── cleaning.py            # Data cleaning engine & record separation
│       ├── config.py              # Environment configuration & DB settings
│       ├── database.py            # Psycopg connection context & DDL execution
│       ├── generator.py           # Synthetic generator (clean and dirty modes)
│       ├── ingestion.py           # Raw CSV validation & bulk transactional loading
│       ├── main.py                # Unified CLI entry point (P1, P2, P3)
│       ├── quality.py             # Data quality metrics & reporting
│       └── validation.py          # Explicit validation rules & categorization
├── tests/
│   ├── __init__.py
│   ├── test_analytics_reporting.py# Analytics terminal reporting tests
│   ├── test_analytics_repository.py# Repository execution & error tests
│   ├── test_analytics_service.py  # Service DataFrame formatting tests
│   ├── test_cleaning.py           # Cleaning, deduplication, & file export tests
│   ├── test_config.py             # Config & env parsing unit tests
│   ├── test_database.py           # Database connection & error handling tests
│   ├── test_dirty_generator.py    # Dirty data generation & reproducibility tests
│   ├── test_generator.py          # Data generation, counts, & seed reproducibility tests
│   ├── test_ingestion.py          # CSV validation & mocked ingestion tests
│   ├── test_main.py               # P1 CLI argument & orchestration tests
│   ├── test_p2_cli.py             # P2 CLI argument & pipeline tests
│   ├── test_p2_database.py        # P2 DDL & transactional persistence tests
│   ├── test_p3_cli.py             # P3 CLI analytics argument tests
│   ├── test_quality.py            # Quality metrics & summary calculations
│   └── test_validation.py         # Explicit validation rules & multi-error tests
├── .env.example                   # Sample environment configuration template
├── .gitignore                     # Git ignore rules (env, cache, all CSV data)
├── requirements.txt               # Pinned project dependencies
└── README.md                      # Project documentation
```

---

## 5. SQL Concepts & Analytical Capabilities

The analytical queries in `sql/analytics/` demonstrate core SQL paradigms to solve practical marketing business problems:

| SQL Concept | Practical Application in FunnelForge |
| :--- | :--- |
| **`INNER JOIN`** | Joins conversion events to customer profiles and campaigns for revenue attribution. |
| **`LEFT JOIN`** | Retains marketing campaigns and channels with zero recorded events in performance reports. |
| **`GROUP BY`** | Aggregates volume and spend across campaigns, channels, acquisition sources, and calendar intervals. |
| **`HAVING`** | Filters aggregated customer profiles to identify repeat converters (`HAVING conversions > 1`). |
| **`CTE` (`WITH`)** | Deconstructs multi-stage aggregations and prevents budget fan-out bugs when joining 1-to-many event records. |
| **`Subqueries`** | Computes cohort benchmarks (e.g. comparing individual customer revenue against average converting customer revenue). |
| **`CASE WHEN`** | Conditionally aggregates funnel event types (`impression`, `click`, `conversion`) in a single table scan. |
| **Window Functions** | Ranks channels (`DENSE_RANK()`), computes portfolio revenue contribution percentages, and derives cumulative running totals. |
| **`NULLIF`** | Prevents division-by-zero crashes on conversion rates, CTR, and ROAS. |
| **Date Functions** | Groups event timestamps into chronological intervals via `DATE_TRUNC('month', ...)` and `DATE_TRUNC('day', ...)`. |

---

## 6. Metric Definitions & Formulas

1. **Click-Through Rate (CTR):**
   $$\text{CTR} = \frac{\text{Clicks}}{\text{NULLIF}(\text{Impressions}, 0)} \times 100$$
2. **Conversion Rate (Conv Rate):**
   $$\text{Conversion Rate} = \frac{\text{Conversions}}{\text{NULLIF}(\text{Clicks}, 0)} \times 100$$
3. **Return on Ad Spend (ROAS):**
   $$\text{ROAS} = \frac{\text{Total Revenue}}{\text{NULLIF}(\text{Campaign Budget}, 0)}$$
   *Note: ROAS measures gross revenue generated per dollar of marketing budget. It reflects top-line return, not net profit or ROI.*
4. **Impression-to-Click Rate:**
   $$\text{Step 1 Drop-off} = \frac{\text{Clicks}}{\text{NULLIF}(\text{Impressions}, 0)} \times 100$$
5. **Click-to-Conversion Rate:**
   $$\text{Step 2 Drop-off} = \frac{\text{Conversions}}{\text{NULLIF}(\text{Clicks}, 0)} \times 100$$
6. **Overall Conversion Rate:**
   $$\text{Overall Rate} = \frac{\text{Conversions}}{\text{NULLIF}(\text{Impressions}, 0)} \times 100$$
7. **Revenue Contribution Percentage:**
   $$\text{Revenue Share \%} = \frac{\text{Campaign Revenue}}{\text{SUM}(\text{Campaign Revenue})\text{ OVER }()} \times 100$$

---

## 7. Representative SQL Queries

### Campaign Performance Analysis ([campaign_performance.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/analytics/campaign_performance.sql))
```sql
WITH campaign_event_aggregates AS (
    SELECT
        c.campaign_id,
        c.campaign_name,
        c.channel,
        c.budget,
        COUNT(CASE WHEN e.event_type = 'impression' THEN 1 END) AS impressions,
        COUNT(CASE WHEN e.event_type = 'click' THEN 1 END) AS clicks,
        COUNT(CASE WHEN e.event_type = 'conversion' THEN 1 END) AS conversions,
        COALESCE(SUM(e.revenue), 0.0) AS total_revenue
    FROM processed_campaigns c
    LEFT JOIN processed_events e ON c.campaign_id = e.campaign_id
    GROUP BY c.campaign_id, c.campaign_name, c.channel, c.budget
)
SELECT
    campaign_id,
    campaign_name,
    channel,
    budget,
    impressions,
    clicks,
    conversions,
    ROUND(total_revenue, 2) AS total_revenue,
    ROUND((clicks::numeric / NULLIF(impressions, 0)) * 100.0, 2) AS ctr_pct,
    ROUND((conversions::numeric / NULLIF(clicks, 0)) * 100.0, 2) AS conv_rate_pct,
    ROUND((total_revenue / NULLIF(budget, 0)), 2) AS roas
FROM campaign_event_aggregates
ORDER BY total_revenue DESC, roas DESC;
```

### Channel Comparison with Ranks ([channel_performance.sql](file:///Users/mohammedaafaqahmed/Developer/FunnelForge/sql/analytics/channel_performance.sql))
```sql
WITH channel_campaigns AS (
    SELECT
        channel,
        COUNT(campaign_id) AS total_campaigns,
        SUM(budget) AS total_budget,
        AVG(budget) AS avg_budget
    FROM processed_campaigns
    GROUP BY channel
),
channel_events AS (
    SELECT
        c.channel,
        COUNT(CASE WHEN e.event_type = 'impression' THEN 1 END) AS impressions,
        COUNT(CASE WHEN e.event_type = 'click' THEN 1 END) AS clicks,
        COUNT(CASE WHEN e.event_type = 'conversion' THEN 1 END) AS conversions,
        COALESCE(SUM(e.revenue), 0.0) AS total_revenue
    FROM processed_campaigns c
    LEFT JOIN processed_events e ON c.campaign_id = e.campaign_id
    GROUP BY c.channel
)
SELECT
    cc.channel,
    cc.total_campaigns,
    ROUND(cc.total_budget, 2) AS total_budget,
    COALESCE(ce.conversions, 0) AS conversions,
    ROUND(COALESCE(ce.total_revenue, 0.0), 2) AS total_revenue,
    ROUND((COALESCE(ce.total_revenue, 0.0) / NULLIF(cc.total_budget, 0)), 2) AS roas,
    DENSE_RANK() OVER (ORDER BY ce.total_revenue DESC) AS rank_revenue,
    DENSE_RANK() OVER (ORDER BY ce.conversions DESC) AS rank_conversions
FROM channel_campaigns cc
LEFT JOIN channel_events ce ON cc.channel = ce.channel
ORDER BY rank_revenue ASC;
```

---

## 8. Installation & Execution

### Prerequisites
- Python 3.11+
- PostgreSQL

### Virtual Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Executive Analytics Dashboard (Single Command)
Run all marketing intelligence queries and render the dashboard:
```bash
python3 -m funnelforge.main --analytics all
```

### Individual Analytics Reporting Options

| Task | Command |
| :--- | :--- |
| **All Analytics Together** | `python3 -m funnelforge.main --analytics all` |
| **Campaign Performance & ROAS** | `python3 -m funnelforge.main --analytics campaigns` |
| **Channel Efficiency & Rankings** | `python3 -m funnelforge.main --analytics channels` |
| **Conversion Funnel Drop-Off** | `python3 -m funnelforge.main --analytics funnel` |
| **Customer Value & Acquisition** | `python3 -m funnelforge.main --analytics customers` |
| **Revenue Contribution & Trends** | `python3 -m funnelforge.main --analytics revenue` |

### P1 and P2 Operations

| Task | Command |
| :--- | :--- |
| **P1 End-to-End Pipeline** | `python3 -m funnelforge.main --all` |
| **P2 Complete Quality Pipeline** | `python3 -m funnelforge.main --p2 --dirty` |
| **Clean Existing CSVs Only** | `python3 -m funnelforge.main --clean` |

---

## 9. Example Analytics Query Outputs

### 1. Macro Conversion Funnel
```
============================================================
                   CONVERSION FUNNEL
============================================================
  [1] Impressions  :     5,901
         ↓  (Click-Through: 36.06%)
  [2] Clicks       :     2,128
         ↓  (Conversion Efficiency: 20.16%)
  [3] Conversions  :       429
------------------------------------------------------------
  Overall Impression-to-Conversion Rate: 7.27%
  * Note: Event-level progression volume.
============================================================
```

### 2. Channel Performance & Efficiency
```
===============================================================================================
                         CHANNEL PERFORMANCE & EFFICIENCY
===============================================================================================
Channel          Camps       Budget  Impressions   Clicks   Conv      Revenue   ROAS   Rank
-----------------------------------------------------------------------------------------------
Social Media         4  $191,393.88        1,364      481    116   $30,919.02   0.16 #    1
Display              4  $153,592.64        1,422      486    102   $25,524.15   0.17 #    2
Referral             4  $185,753.43        1,421      537     86   $21,604.00   0.12 #    3
Email                3   $78,104.26        1,025      379     71   $20,043.38   0.26 #    4
Search               2  $101,348.01          669      245     54   $12,798.61   0.13 #    5
===============================================================================================
```

### 3. Top Revenue Generating Campaigns
```
=====================================================================================
                TOP 5 REVENUE GENERATING CAMPAIGNS
=====================================================================================
Rank   Campaign Name                Channel             Revenue    Share %   Cumulative
-------------------------------------------------------------------------------------
#1     Autumn Lead Gen 2024         Social Media     $10,343.95      9.33%   $10,343.95
#2     Display Programmatic Wave... Display          $10,264.33      9.26%   $20,608.28
#3     Mid-Year Video Ads 2024      Social Media      $9,054.12      8.17%   $29,662.40
#4     Winter Kickoff 2024          Email             $8,958.79      8.08%   $38,621.19
#5     Back to School Email Blas... Email             $7,502.38      6.77%   $46,123.57
=====================================================================================
```

---

## 10. Important Assumptions & Limitations

- **Event-Level Funnel Attribution:** Funnel metrics reflect aggregate event counts across steps rather than deduplicated individual user sessions. A single customer may register multiple impressions or clicks before converting.
- **Top-Line ROAS vs. Profitability:** The ROAS metric reflects gross revenue generated relative to budget spend ($\text{Revenue} / \text{Budget}$). Cost of goods sold (COGS), operational overhead, and agency fees are not accounted for.
- **Budget Aggregation:** Because campaigns run over multi-day windows, budget figures are reported per campaign allocation. In multi-channel joins, CTEs isolate campaign budgets to avoid multiplication across multiple events.

---

## 11. Testing Instructions

All unit tests use `pytest` and mock database interactions, ensuring tests execute quickly and reliably:

```bash
PYTHONPATH=src pytest -v
```

### Test Suite Summary (69 Passing Tests):
- **`test_analytics_repository.py`:** Tests SQL execution, query file loading, database exception handling, and empty dataset fallbacks.
- **`test_analytics_service.py`:** Tests DataFrame conversion, metric column integrity, empty results handling, and full executive summaries.
- **`test_analytics_reporting.py`:** Tests terminal dashboard formatting, revenue formatting, and table alignment.
- **`test_p3_cli.py`:** Tests CLI flags (`--analytics all`, `--analytics campaigns`, `--analytics channels`, etc.).
- **P1 & P2 Regression Suites:** Verifies schema creation, data generation, cleaning validation rules, and quality metrics remain regression-free.

---

## 12. Roadmap

- [x] **P1 — Data Foundation & Ingestion**
  - Project architecture, raw schema, synthetic generator (11,020 records), transactional bulk ingestion, unit test suite.
- [x] **P2 — Data Cleaning & Quality Assurance**
  - Dirty data generator, multi-rule validation engine, accepted/rejected partitioning, PostgreSQL processed layer & JSONB audit issues, dynamic data quality metrics.
- [x] **P3 — SQL Analytics & Business Metrics**
  - Analytics repository and service, SQL queries for campaigns/channels/funnels/customers/revenue, window functions, and executive CLI dashboard.
- [ ] **P4 — Analytics & Reporting Engine**
  - KPI calculation, automated summary dashboards, and report generation.
