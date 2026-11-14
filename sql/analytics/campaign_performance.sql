-- =============================================================================
-- FunnelForge Analytics: Campaign Performance Analysis
-- =============================================================================
-- Evaluates marketing campaign performance, engagement volume, conversion
-- efficiency, and return on ad spend (ROAS).
-- 
-- Concepts demonstrated:
--   - LEFT JOIN: Retains campaigns that recorded zero events.
--   - CASE WHEN: Conditional event aggregation (impressions, clicks, conversions).
--   - NULLIF: Guards against division-by-zero errors.
--   - CTE: Isolates event aggregation before metric derivation.
-- =============================================================================

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
    -- CTR: (Clicks / Impressions) * 100
    ROUND(
        (clicks::numeric / NULLIF(impressions, 0)) * 100.0,
        2
    ) AS ctr_pct,
    -- Conversion Rate: (Conversions / Clicks) * 100
    ROUND(
        (conversions::numeric / NULLIF(clicks, 0)) * 100.0,
        2
    ) AS conv_rate_pct,
    -- ROAS: Revenue / Budget (Revenue-to-budget ratio)
    ROUND(
        (total_revenue / NULLIF(budget, 0)),
        2
    ) AS roas
FROM campaign_event_aggregates
ORDER BY total_revenue DESC, roas DESC;
