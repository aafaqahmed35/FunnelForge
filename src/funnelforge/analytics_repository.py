"""Analytics database repository for executing marketing analytical queries."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from psycopg.rows import dict_row

from funnelforge.config import DatabaseConfig, PROJECT_ROOT
from funnelforge.database import DatabaseError, get_connection

logger = logging.getLogger(__name__)

ANALYTICS_SQL_DIR = PROJECT_ROOT / "sql" / "analytics"


class AnalyticsRepository:
    """Executes SQL queries against processed marketing data in PostgreSQL."""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config

    def _execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query using dict_row factory and return rows as dictionaries."""
        try:
            with get_connection(self.config) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(sql, params)
                    return cur.fetchall()
        except Exception as err:
            logger.error("Analytics query failed: %s", err)
            raise DatabaseError(f"Analytics query execution failed: {err}") from err

    def _read_sql_file(self, filename: str) -> str:
        """Load SQL string from sql/analytics/ directory."""
        path = ANALYTICS_SQL_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(f"Analytics SQL file not found: {path}")
        return path.read_text(encoding="utf-8")

    def get_campaign_performance(self) -> List[Dict[str, Any]]:
        """Fetch campaign performance metrics (CTR, conversion rate, ROAS)."""
        sql = self._read_sql_file("campaign_performance.sql")
        return self._execute_query(sql)

    def get_channel_performance(self) -> List[Dict[str, Any]]:
        """Fetch marketing channel comparison and rankings."""
        sql = self._read_sql_file("channel_performance.sql")
        return self._execute_query(sql)

    def get_conversion_funnel(self) -> Dict[str, Any]:
        """Fetch macro conversion funnel counts and drop-off percentages."""
        sql = self._read_sql_file("conversion_analysis.sql")
        rows = self._execute_query(sql)
        return rows[0] if rows else {
            "total_impressions": 0,
            "total_clicks": 0,
            "total_conversions": 0,
            "impression_to_click_pct": 0.0,
            "click_to_conversion_pct": 0.0,
            "overall_conversion_pct": 0.0,
        }

    def get_customer_analysis(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch high-value customers, conversion frequency, and cohort comparisons."""
        sql = self._read_sql_file("customer_analysis.sql")
        if limit:
            sql = f"{sql.rstrip().rstrip(';')} LIMIT {int(limit)};"
        return self._execute_query(sql)

    def get_acquisition_source_performance(self) -> List[Dict[str, Any]]:
        """Fetch performance metrics aggregated by customer acquisition source."""
        sql = """
            SELECT
                c.acquisition_source,
                COUNT(DISTINCT c.customer_id) AS total_customers,
                COUNT(CASE WHEN e.event_type = 'conversion' THEN 1 END) AS total_conversions,
                ROUND(COALESCE(SUM(e.revenue), 0.0), 2) AS total_revenue,
                ROUND(
                    (COALESCE(SUM(e.revenue), 0.0) / NULLIF(COUNT(DISTINCT c.customer_id), 0)),
                    2
                ) AS revenue_per_customer
            FROM processed_customers c
            LEFT JOIN processed_events e ON c.customer_id = e.customer_id
            GROUP BY c.acquisition_source
            ORDER BY total_revenue DESC;
        """
        return self._execute_query(sql)

    def get_revenue_analysis(self, top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch campaign revenue contributions, cumulative running totals, and ranks."""
        sql = self._read_sql_file("revenue_analysis.sql")
        if top_n:
            sql = f"{sql.rstrip().rstrip(';')} LIMIT {int(top_n)};"
        return self._execute_query(sql)

    def get_monthly_revenue_trends(self) -> List[Dict[str, Any]]:
        """Fetch chronological monthly revenue and conversion volume trends."""
        sql = """
            SELECT
                DATE_TRUNC('month', event_timestamp)::DATE AS month,
                COUNT(CASE WHEN event_type = 'conversion' THEN 1 END) AS conversions,
                ROUND(COALESCE(SUM(revenue), 0.0), 2) AS monthly_revenue,
                ROUND(AVG(revenue), 2) AS avg_conversion_value
            FROM processed_events
            WHERE event_type = 'conversion' AND revenue IS NOT NULL
            GROUP BY DATE_TRUNC('month', event_timestamp)
            ORDER BY month ASC;
        """
        return self._execute_query(sql)

    def get_daily_revenue_trends(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Fetch daily revenue trends."""
        sql = """
            SELECT
                DATE_TRUNC('day', event_timestamp)::DATE AS day,
                COUNT(CASE WHEN event_type = 'conversion' THEN 1 END) AS conversions,
                ROUND(COALESCE(SUM(revenue), 0.0), 2) AS daily_revenue
            FROM processed_events
            WHERE event_type = 'conversion' AND revenue IS NOT NULL
            GROUP BY DATE_TRUNC('day', event_timestamp)
            ORDER BY day DESC
            LIMIT %s;
        """
        return self._execute_query(sql, (limit,))
