-- =============================================================================
-- FunnelForge Analytics: Channel Performance Analysis
-- =============================================================================
-- Compares cross-channel marketing effectiveness, aggregate budgets, and ROAS.
--
-- Concepts demonstrated:
--   - CTE: Separates campaign budget sums from event aggregates to prevent
--     fan-out budget multiplication across 1-to-many relationship.
--   - Window Functions: DENSE_RANK() for ranking channels by revenue,
--     conversion volume, and conversion efficiency.
--   - NULLIF & ROUND: Safe percentage and ratio formatting.
-- =============================================================================

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
),
channel_metrics AS (
    SELECT
        cc.channel,
        cc.total_campaigns,
        ROUND(cc.total_budget, 2) AS total_budget,
        ROUND(cc.avg_budget, 2) AS avg_budget,
        COALESCE(ce.impressions, 0) AS impressions,
        COALESCE(ce.clicks, 0) AS clicks,
        COALESCE(ce.conversions, 0) AS conversions,
        ROUND(COALESCE(ce.total_revenue, 0.0), 2) AS total_revenue,
        ROUND(
            (COALESCE(ce.clicks, 0)::numeric / NULLIF(ce.impressions, 0)) * 100.0,
            2
        ) AS ctr_pct,
        ROUND(
            (COALESCE(ce.conversions, 0)::numeric / NULLIF(ce.clicks, 0)) * 100.0,
            2
        ) AS conv_rate_pct,
        ROUND(
            (COALESCE(ce.total_revenue, 0.0) / NULLIF(cc.total_budget, 0)),
            2
        ) AS roas
    FROM channel_campaigns cc
    LEFT JOIN channel_events ce ON cc.channel = ce.channel
)
SELECT
    channel,
    total_campaigns,
    total_budget,
    avg_budget,
    impressions,
    clicks,
    conversions,
    total_revenue,
    ctr_pct,
    conv_rate_pct,
    roas,
    DENSE_RANK() OVER (ORDER BY total_revenue DESC) AS rank_revenue,
    DENSE_RANK() OVER (ORDER BY conversions DESC) AS rank_conversions,
    DENSE_RANK() OVER (ORDER BY conv_rate_pct DESC NULLS LAST) AS rank_efficiency
FROM channel_metrics
ORDER BY rank_revenue ASC;
