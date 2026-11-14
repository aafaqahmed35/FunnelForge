-- =============================================================================
-- FunnelForge Analytics: Customer Value & Behavior Analysis
-- =============================================================================
-- Identifies top converting customers, high-value purchasers, repeat converters,
-- and compares customer value against the benchmark cohort average.
--
-- Concepts demonstrated:
--   - INNER JOIN: Joins processed_events to processed_customers.
--   - CTE & GROUP BY: Computes customer-level conversion and revenue aggregates.
--   - HAVING: Filters for repeat converters (conversions > 1).
--   - Subquery: Calculates global average revenue per converting customer.
--   - Window Function: DENSE_RANK() to rank customers by total revenue.
-- =============================================================================

WITH customer_aggregates AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.email,
        c.acquisition_source,
        c.signup_date,
        COUNT(CASE WHEN e.event_type = 'conversion' THEN 1 END) AS total_conversions,
        COALESCE(SUM(e.revenue), 0.0) AS total_revenue
    FROM processed_customers c
    INNER JOIN processed_events e ON c.customer_id = e.customer_id
    GROUP BY c.customer_id, c.customer_name, c.email, c.acquisition_source, c.signup_date
    HAVING COUNT(CASE WHEN e.event_type = 'conversion' THEN 1 END) > 0
),
cohort_benchmarks AS (
    SELECT
        AVG(total_revenue) AS avg_revenue_per_converting_customer
    FROM customer_aggregates
)
SELECT
    ca.customer_id,
    ca.customer_name,
    ca.email,
    ca.acquisition_source,
    ca.signup_date,
    ca.total_conversions,
    ROUND(ca.total_revenue, 2) AS total_revenue,
    -- Repeat converter indicator
    CASE WHEN ca.total_conversions > 1 THEN TRUE ELSE FALSE END AS is_repeat_converter,
    -- Rank by total revenue
    DENSE_RANK() OVER (ORDER BY ca.total_revenue DESC) AS rank_revenue,
    -- Comparison against cohort average (subquery via CTE)
    ROUND(ca.total_revenue - cb.avg_revenue_per_converting_customer, 2) AS revenue_vs_cohort_avg
FROM customer_aggregates ca
CROSS JOIN cohort_benchmarks cb
ORDER BY ca.total_revenue DESC, ca.total_conversions DESC;
