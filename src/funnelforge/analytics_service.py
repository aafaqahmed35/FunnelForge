"""Analytics service layer providing structured marketing business intelligence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import pandas as pd

from funnelforge.analytics_repository import AnalyticsRepository
from funnelforge.config import DatabaseConfig


class AnalyticsService:
    """Service layer orchestrating marketing analytics operations and formatting."""

    def __init__(
        self,
        repository: Optional[AnalyticsRepository] = None,
        config: Optional[DatabaseConfig] = None,
    ):
        self.repository = repository or AnalyticsRepository(config=config)

    def get_campaign_performance(
        self, as_df: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Retrieve campaign performance metrics."""
        data = self.repository.get_campaign_performance()
        if as_df:
            cols = [
                "campaign_id", "campaign_name", "channel", "budget",
                "impressions", "clicks", "conversions", "total_revenue",
                "ctr_pct", "conv_rate_pct", "roas"
            ]
            return pd.DataFrame(data, columns=cols) if data else pd.DataFrame(columns=cols)
        return data

    def get_channel_performance(
        self, as_df: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Retrieve marketing channel performance and rankings."""
        data = self.repository.get_channel_performance()
        if as_df:
            cols = [
                "channel", "total_campaigns", "total_budget", "avg_budget",
                "impressions", "clicks", "conversions", "total_revenue",
                "ctr_pct", "conv_rate_pct", "roas",
                "rank_revenue", "rank_conversions", "rank_efficiency"
            ]
            return pd.DataFrame(data, columns=cols) if data else pd.DataFrame(columns=cols)
        return data

    def get_conversion_funnel(self) -> Dict[str, Any]:
        """Retrieve macro funnel conversion metrics."""
        return self.repository.get_conversion_funnel()

    def get_customer_analysis(
        self, limit: Optional[int] = 10, as_df: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Retrieve high-value customer rankings and repeat converter data."""
        data = self.repository.get_customer_analysis(limit=limit)
        if as_df:
            cols = [
                "customer_id", "customer_name", "email", "acquisition_source",
                "signup_date", "total_conversions", "total_revenue",
                "is_repeat_converter", "rank_revenue", "revenue_vs_cohort_avg"
            ]
            return pd.DataFrame(data, columns=cols) if data else pd.DataFrame(columns=cols)
        return data

    def get_acquisition_sources(
        self, as_df: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Retrieve acquisition source effectiveness."""
        data = self.repository.get_acquisition_source_performance()
        if as_df:
            cols = [
                "acquisition_source", "total_customers", "total_conversions",
                "total_revenue", "revenue_per_customer"
            ]
            return pd.DataFrame(data, columns=cols) if data else pd.DataFrame(columns=cols)
        return data

    def get_revenue_analysis(
        self, top_n: Optional[int] = None, as_df: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Retrieve campaign revenue contributions and ranks."""
        data = self.repository.get_revenue_analysis(top_n=top_n)
        if as_df:
            cols = [
                "campaign_id", "campaign_name", "channel", "budget",
                "conversion_count", "campaign_revenue",
                "revenue_contribution_pct", "cumulative_revenue", "revenue_rank"
            ]
            return pd.DataFrame(data, columns=cols) if data else pd.DataFrame(columns=cols)
        return data

    def get_monthly_revenue_trends(
        self, as_df: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Retrieve monthly revenue progression."""
        data = self.repository.get_monthly_revenue_trends()
        if as_df:
            cols = ["month", "conversions", "monthly_revenue", "avg_conversion_value"]
            return pd.DataFrame(data, columns=cols) if data else pd.DataFrame(columns=cols)
        return data

    def get_daily_revenue_trends(
        self, limit: int = 30, as_df: bool = False
    ) -> Union[List[Dict[str, Any]], pd.DataFrame]:
        """Retrieve daily revenue trends."""
        data = self.repository.get_daily_revenue_trends(limit=limit)
        if as_df:
            cols = ["day", "conversions", "daily_revenue"]
            return pd.DataFrame(data, columns=cols) if data else pd.DataFrame(columns=cols)
        return data

    def get_full_summary(self) -> Dict[str, Any]:
        """Retrieve consolidated analytics overview."""
        return {
            "funnel": self.get_conversion_funnel(),
            "channel_performance": self.get_channel_performance(),
            "top_campaigns": self.get_revenue_analysis(top_n=5),
            "top_customers": self.get_customer_analysis(limit=5),
            "acquisition_sources": self.get_acquisition_sources(),
            "monthly_trends": self.get_monthly_revenue_trends(),
        }
