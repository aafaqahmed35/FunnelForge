-- =============================================================================
-- FunnelForge Analytics: Revenue Distribution & Contribution Analysis
-- =============================================================================
-- Measures revenue generation by campaign, channel, and relative contribution.
--
-- Concepts demonstrated:
--   - INNER JOIN: Filters strictly for conversion events with revenue.
--   - Window Functions:
--       - SUM(SUM(...)) OVER (): Calculates total portfolio revenue for share %.
--       - DENSE_RANK(): Ranks campaigns by revenue.
--       - Running cumulative revenue sum across campaigns.
-- =============================================================================

WITH campaign_revenue AS (
    SELECT
        c.campaign_id,
        c.campaign_name,
        c.channel,
        c.budget,
        COUNT(e.event_id) AS conversion_count,
        SUM(e.revenue) AS campaign_revenue
    FROM processed_campaigns c
    INNER JOIN processed_events e ON c.campaign_id = e.campaign_id
    WHERE e.event_type = 'conversion' AND e.revenue IS NOT NULL
    GROUP BY c.campaign_id, c.campaign_name, c.channel, c.budget
)
SELECT
    campaign_id,
    campaign_name,
    channel,
    budget,
    conversion_count,
    ROUND(campaign_revenue, 2) AS campaign_revenue,
    -- Revenue Contribution Percentage across entire portfolio
    ROUND(
        (campaign_revenue * 100.0) / NULLIF(SUM(campaign_revenue) OVER (), 0),
        2
    ) AS revenue_contribution_pct,
    -- Running Cumulative Revenue
    ROUND(
        SUM(campaign_revenue) OVER (
            ORDER BY campaign_revenue DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS cumulative_revenue,
    DENSE_RANK() OVER (ORDER BY campaign_revenue DESC) AS revenue_rank
FROM campaign_revenue
ORDER BY campaign_revenue DESC;
