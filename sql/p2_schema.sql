-- =============================================================================
-- FunnelForge Schema: P2 Processed Data & Quality Assurance Layer
-- =============================================================================
-- This migration extends the FunnelForge schema to store validated marketing data
-- and preserve full audit visibility into rejected records via data_quality_issues.
-- Schema initialization is idempotent (safely repeatable using IF NOT EXISTS).
-- =============================================================================

-- 1. Processed Campaigns Table
CREATE TABLE IF NOT EXISTS processed_campaigns (
    campaign_id     VARCHAR(64) PRIMARY KEY,
    campaign_name   VARCHAR(255) NOT NULL,
    channel         VARCHAR(50) NOT NULL,
    budget          NUMERIC(12, 2) NOT NULL CHECK (budget >= 0),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    CONSTRAINT chk_proc_campaign_dates CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_proc_campaigns_channel ON processed_campaigns(channel);
CREATE INDEX IF NOT EXISTS idx_proc_campaigns_dates ON processed_campaigns(start_date, end_date);

-- 2. Processed Customers Table
CREATE TABLE IF NOT EXISTS processed_customers (
    customer_id         VARCHAR(64) PRIMARY KEY,
    customer_name       VARCHAR(255) NOT NULL,
    email               VARCHAR(255) NOT NULL,
    acquisition_source  VARCHAR(50) NOT NULL,
    signup_date         DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_proc_customers_email ON processed_customers(email);
CREATE INDEX IF NOT EXISTS idx_proc_customers_signup ON processed_customers(signup_date);
CREATE INDEX IF NOT EXISTS idx_proc_customers_source ON processed_customers(acquisition_source);

-- 3. Processed Events Table
CREATE TABLE IF NOT EXISTS processed_events (
    event_id        VARCHAR(64) PRIMARY KEY,
    customer_id     VARCHAR(64) NOT NULL REFERENCES processed_customers(customer_id) ON DELETE CASCADE,
    campaign_id     VARCHAR(64) NOT NULL REFERENCES processed_campaigns(campaign_id) ON DELETE CASCADE,
    event_type      VARCHAR(20) NOT NULL CHECK (event_type IN ('impression', 'click', 'conversion')),
    event_timestamp TIMESTAMPTZ NOT NULL,
    revenue         NUMERIC(12, 2) CHECK (
        (event_type = 'conversion' AND revenue IS NOT NULL AND revenue >= 0)
        OR (event_type != 'conversion' AND revenue IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_proc_events_customer ON processed_events(customer_id);
CREATE INDEX IF NOT EXISTS idx_proc_events_campaign ON processed_events(campaign_id);
CREATE INDEX IF NOT EXISTS idx_proc_events_timestamp ON processed_events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_proc_events_type ON processed_events(event_type);

-- 4. Data Quality Issues Table (Audit & Lineage)
CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id            BIGSERIAL PRIMARY KEY,
    source_dataset      VARCHAR(50) NOT NULL,
    record_id           VARCHAR(64),
    rejection_reason    TEXT NOT NULL,
    original_record     JSONB NOT NULL,
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dqi_dataset ON data_quality_issues(source_dataset);
CREATE INDEX IF NOT EXISTS idx_dqi_record_id ON data_quality_issues(record_id);
CREATE INDEX IF NOT EXISTS idx_dqi_detected_at ON data_quality_issues(detected_at);

