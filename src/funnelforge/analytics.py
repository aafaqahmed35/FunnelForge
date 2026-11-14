"""Analytics reporting coordinator and formatted executive dashboard for FunnelForge."""

from __future__ import annotations

from typing import Optional

from funnelforge.analytics_service import AnalyticsService
from funnelforge.config import DatabaseConfig


class MarketingAnalytics:
    """Coordinates analytical reporting and renders concise terminal dashboards."""

    def __init__(self, service: Optional[AnalyticsService] = None, config: Optional[DatabaseConfig] = None):
        self.service = service or AnalyticsService(config=config)

    def report_campaign_performance(self) -> None:
        """Display campaign performance report."""
        campaigns = self.service.get_campaign_performance()
        print("\n" + "=" * 90)
        print("                        CAMPAIGN PERFORMANCE ANALYSIS")
        print("=" * 90)
        print(f"{'Campaign ID':<12} {'Campaign Name':<28} {'Channel':<14} {'Budget':>10} {'Conv':>6} {'Revenue':>12} {'CTR':>8} {'ROAS':>6}")
        print("-" * 90)

        for c in campaigns:
            name = (c["campaign_name"][:25] + "...") if len(c["campaign_name"]) > 28 else c["campaign_name"]
            budget_str = f"${float(c['budget']):,.2f}"
            rev_str = f"${float(c['total_revenue']):,.2f}"
            ctr_str = f"{float(c['ctr_pct'] or 0):.1f}%"
            roas_str = f"{float(c['roas'] or 0):.2f}"

            print(
                f"{c['campaign_id']:<12} "
                f"{name:<28} "
                f"{c['channel']:<14} "
                f"{budget_str:>10} "
                f"{c['conversions']:>6,d} "
                f"{rev_str:>12} "
                f"{ctr_str:>8} "
                f"{roas_str:>6}"
            )
        print("=" * 90 + "\n")

    def report_channel_performance(self) -> None:
        """Display cross-channel comparison and ranking report."""
        channels = self.service.get_channel_performance()
        print("\n" + "=" * 95)
        print("                         CHANNEL PERFORMANCE & EFFICIENCY")
        print("=" * 95)
        print(f"{'Channel':<15} {'Camps':>6} {'Budget':>12} {'Impressions':>12} {'Clicks':>8} {'Conv':>6} {'Revenue':>12} {'ROAS':>6} {'Rank':>6}")
        print("-" * 95)

        for ch in channels:
            budget_str = f"${float(ch['total_budget']):,.2f}"
            rev_str = f"${float(ch['total_revenue']):,.2f}"
            roas_str = f"{float(ch['roas'] or 0):.2f}"

            print(
                f"{ch['channel']:<15} "
                f"{ch['total_campaigns']:>6,d} "
                f"{budget_str:>12} "
                f"{ch['impressions']:>12,d} "
                f"{ch['clicks']:>8,d} "
                f"{ch['conversions']:>6,d} "
                f"{rev_str:>12} "
                f"{roas_str:>6} "
                f"#{ch['rank_revenue']:>5}"
            )
        print("=" * 95 + "\n")

    def report_conversion_funnel(self) -> None:
        """Display macro conversion funnel analysis."""
        funnel = self.service.get_conversion_funnel()
        imp = funnel.get("total_impressions", 0)
        clk = funnel.get("total_clicks", 0)
        cnv = funnel.get("total_conversions", 0)
        i_to_c = float(funnel.get("impression_to_click_pct", 0) or 0)
        c_to_v = float(funnel.get("click_to_conversion_pct", 0) or 0)
        ovr = float(funnel.get("overall_conversion_pct", 0) or 0)

        print("\n" + "=" * 60)
        print("                   CONVERSION FUNNEL")
        print("=" * 60)
        print(f"  [1] Impressions  : {imp:>9,d}")
        print(f"         ↓  (Click-Through: {i_to_c:.2f}%)")
        print(f"  [2] Clicks       : {clk:>9,d}")
        print(f"         ↓  (Conversion Efficiency: {c_to_v:.2f}%)")
        print(f"  [3] Conversions  : {cnv:>9,d}")
        print("-" * 60)
        print(f"  Overall Impression-to-Conversion Rate: {ovr:.2f}%")
        print("  * Note: Event-level progression volume.")
        print("=" * 60 + "\n")

    def report_customer_analysis(self, limit: int = 10) -> None:
        """Display customer value and acquisition source report."""
        customers = self.service.get_customer_analysis(limit=limit)
        sources = self.service.get_acquisition_sources()

        print("\n" + "=" * 85)
        print("                     TOP CUSTOMERS BY REVENUE & VALUE")
        print("=" * 85)
        print(f"{'Customer ID':<12} {'Customer Name':<22} {'Acquisition':<16} {'Conv':>6} {'Revenue':>12} {'Repeat?':>8}")
        print("-" * 85)

        for c in customers:
            rev_str = f"${float(c['total_revenue']):,.2f}"
            repeat_str = "Yes" if c.get("is_repeat_converter") else "No"
            print(
                f"{c['customer_id']:<12} "
                f"{c['customer_name'][:20]:<22} "
                f"{c['acquisition_source']:<16} "
                f"{c['total_conversions']:>6,d} "
                f"{rev_str:>12} "
                f"{repeat_str:>8}"
            )
        print("-" * 85)
        print("Acquisition Source Performance:")
        for s in sources:
            s_rev = f"${float(s['total_revenue']):,.2f}"
            rev_per_cust = f"${float(s['revenue_per_customer'] or 0):,.2f}"
            print(
                f"  • {s['acquisition_source']:<16}: {s['total_customers']:>4,d} customers, "
                f"{s['total_conversions']:>4,d} conversions, {s_rev:>10} total rev ({rev_per_cust}/cust)"
            )
        print("=" * 85 + "\n")

    def report_revenue_analysis(self, top_n: int = 5) -> None:
        """Display revenue contribution and progression report."""
        top_camps = self.service.get_revenue_analysis(top_n=top_n)
        monthly = self.service.get_monthly_revenue_trends()

        print("\n" + "=" * 85)
        print(f"                TOP {top_n} REVENUE GENERATING CAMPAIGNS")
        print("=" * 85)
        print(f"{'Rank':<6} {'Campaign Name':<28} {'Channel':<14} {'Revenue':>12} {'Share %':>10} {'Cumulative':>12}")
        print("-" * 85)

        for c in top_camps:
            name = (c["campaign_name"][:25] + "...") if len(c["campaign_name"]) > 28 else c["campaign_name"]
            rev_str = f"${float(c['campaign_revenue']):,.2f}"
            cum_str = f"${float(c['cumulative_revenue']):,.2f}"
            share_str = f"{float(c['revenue_contribution_pct']):.2f}%"

            print(
                f"#{c['revenue_rank']:<5} "
                f"{name:<28} "
                f"{c['channel']:<14} "
                f"{rev_str:>12} "
                f"{share_str:>10} "
                f"{cum_str:>12}"
            )
        print("-" * 85)
        print("Monthly Revenue Progression:")
        for m in monthly:
            m_rev = f"${float(m['monthly_revenue']):,.2f}"
            m_aov = f"${float(m['avg_conversion_value'] or 0):,.2f}"
            print(f"  • {str(m['month']):<10}: {m_rev:>11} across {m['conversions']:>3,d} conversions (AOV: {m_aov})")
        print("=" * 85 + "\n")

    def report_all(self) -> None:
        """Run and display the full marketing analytics suite."""
        print("\n" + "#" * 90)
        print("                FUNNELFORGE MARKETING BUSINESS INTELLIGENCE DASHBOARD")
        print("#" * 90)
        self.report_conversion_funnel()
        self.report_channel_performance()
        self.report_campaign_performance()
        self.report_revenue_analysis(top_n=5)
        self.report_customer_analysis(limit=8)
        print("#" * 90)
        print("                     END OF MARKETING ANALYTICS DASHBOARD")
        print("#" * 90 + "\n")
