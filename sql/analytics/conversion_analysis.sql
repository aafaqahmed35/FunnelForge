-- =============================================================================
-- FunnelForge Analytics: Conversion Funnel Analysis
-- =============================================================================
-- Models the sequential customer conversion journey:
--   Impressions -> Clicks -> Conversions
--
-- Metric Definitions (Event-Level):
--   - Impression-to-Click Rate: (Clicks / Impressions) * 100
--   - Click-to-Conversion Rate: (Conversions / Clicks) * 100
--   - Overall Conversion Rate:  (Conversions / Impressions) * 100
--
-- Note: These metrics measure event-level progression volume rather than
-- deduplicated user-level attribution.
-- =============================================================================

WITH stage_counts AS (
    SELECT
        COUNT(CASE WHEN event_type = 'impression' THEN 1 END) AS total_impressions,
        COUNT(CASE WHEN event_type = 'click' THEN 1 END) AS total_clicks,
        COUNT(CASE WHEN event_type = 'conversion' THEN 1 END) AS total_conversions
    FROM processed_events
)
SELECT
    total_impressions,
    total_clicks,
    total_conversions,
    -- Step 1 to Step 2 Drop-off Conversion
    ROUND(
        (total_clicks::numeric / NULLIF(total_impressions, 0)) * 100.0,
        2
    ) AS impression_to_click_pct,
    -- Step 2 to Step 3 Final Conversion
    ROUND(
        (total_conversions::numeric / NULLIF(total_clicks, 0)) * 100.0,
        2
    ) AS click_to_conversion_pct,
    -- Full Funnel Efficiency
    ROUND(
        (total_conversions::numeric / NULLIF(total_impressions, 0)) * 100.0,
        2
    ) AS overall_conversion_pct
FROM stage_counts;
