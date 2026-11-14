-- =============================================================================
-- FunnelForge Schema: P1 Raw Ingestion Tables
-- =============================================================================
-- This file defines the raw data layer for FunnelForge marketing analytics.
-- Schema initialization is idempotent (safely repeatable using IF NOT EXISTS).
-- =============================================================================

-- 1. Raw Campaigns Table
CREATE TABLE IF NOT EXISTS raw_campaigns (
    campaign_id     VARCHAR(64) PRIMARY KEY,
    campaign_name   VARCHAR(255) NOT NULL,
    channel         VARCHAR(50) NOT NULL,
    budget          NUMERIC(12, 2) NOT NULL CHECK (budget >= 0),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    CONSTRAINT chk_campaign_dates CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_campaigns_channel ON raw_campaigns(channel);
CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON raw_campaigns(start_date, end_date);

-- 2. Raw Customers Table
CREATE TABLE IF NOT EXISTS raw_customers (
    customer_id         VARCHAR(64) PRIMARY KEY,
    customer_name       VARCHAR(255) NOT NULL,
    email               VARCHAR(255) NOT NULL,
    acquisition_source  VARCHAR(50) NOT NULL,
    signup_date         DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON raw_customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_signup_date ON raw_customers(signup_date);
CREATE INDEX IF NOT EXISTS idx_customers_source ON raw_customers(acquisition_source);

-- 3. Raw Events Table
CREATE TABLE IF NOT EXISTS raw_events (
    event_id        VARCHAR(64) PRIMARY KEY,
    customer_id     VARCHAR(64) NOT NULL REFERENCES raw_customers(customer_id) ON DELETE CASCADE,
    campaign_id     VARCHAR(64) NOT NULL REFERENCES raw_campaigns(campaign_id) ON DELETE CASCADE,
    event_type      VARCHAR(20) NOT NULL CHECK (event_type IN ('impression', 'click', 'conversion')),
    event_timestamp TIMESTAMPTZ NOT NULL,
    revenue         NUMERIC(12, 2) CHECK (
        (event_type = 'conversion' AND revenue IS NOT NULL AND revenue >= 0)
        OR (event_type != 'conversion' AND revenue IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_events_customer ON raw_events(customer_id);
CREATE INDEX IF NOT EXISTS idx_events_campaign ON raw_events(campaign_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON raw_events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON raw_events(event_type);
