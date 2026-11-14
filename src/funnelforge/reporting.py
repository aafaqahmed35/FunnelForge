"""Automated Reporting Engine for FunnelForge.

Combines P2 data-quality metrics and P3 analytical insights into:
1. Data Quality Report
2. Marketing Performance Report
3. Executive Summary
4. Multi-format exports: CSV, JSON, and formatted TXT.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from psycopg.rows import dict_row

from funnelforge.analytics_service import AnalyticsService
from funnelforge.config import AppConfig, DatabaseConfig, PROJECT_ROOT
from funnelforge.database import get_connection
from funnelforge.logging import get_logger
from funnelforge.quality import QualityReport

logger = get_logger("reporting")


def json_serializer(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json encoder."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, pd.Series):
        return obj.to_list()
    raise TypeError(f"Type {type(obj)} not serializable to JSON")


class ReportGenerator:
    """Generates analytical reports and exports them to CSV, JSON, and TXT formats."""

    def __init__(
        self,
        service: Optional[AnalyticsService] = None,
        config: Optional[DatabaseConfig] = None,
        quality_report: Optional[QualityReport] = None,
    ):
        self.config = config or DatabaseConfig.from_env()
        self.service = service or AnalyticsService(config=self.config)
        self.quality_report = quality_report

    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """Retrieve data quality metrics either from in-memory report or database."""
        if self.quality_report:
            return self.quality_report.to_dict()

        # Query database directly for quality audit metrics
        try:
            with get_connection(self.config) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("SELECT count(*) AS total_issues FROM data_quality_issues;")
                    total_issues = cur.fetchone()["total_issues"]

                    cur.execute("""
                        SELECT source_dataset, count(*) AS issue_count
                        FROM data_quality_issues
                        GROUP BY source_dataset;
                    """)
                    ds_issues = {r["source_dataset"]: r["issue_count"] for r in cur.fetchall()}

                    cur.execute("SELECT count(*) AS c FROM processed_campaigns;")
                    proc_camps = cur.fetchone()["c"]

                    cur.execute("SELECT count(*) AS c FROM processed_customers;")
                    proc_custs = cur.fetchone()["c"]

                    cur.execute("SELECT count(*) AS c FROM processed_events;")
                    proc_evts = cur.fetchone()["c"]

            total_accepted = proc_camps + proc_custs + proc_evts
            total_rejected = total_issues
            total_examined = total_accepted + total_rejected
            acc_rate = (total_accepted / total_examined * 100.0) if total_examined > 0 else 100.0
            rej_rate = (total_rejected / total_examined * 100.0) if total_examined > 0 else 0.0

            return {
                "total_examined": total_examined,
                "total_accepted": total_accepted,
                "total_rejected": total_rejected,
                "overall_acceptance_rate": round(acc_rate, 2),
                "overall_rejection_rate": round(rej_rate, 2),
                "issues_by_dataset": ds_issues,
                "issues_by_category": {},
                "top_rejection_reasons": [],
            }
        except Exception as err:
            logger.warning("Could not query data_quality_issues from DB: %s", err)
            return {
                "total_examined": 0,
                "total_accepted": 0,
                "total_rejected": 0,
                "overall_acceptance_rate": 0.0,
                "overall_rejection_rate": 0.0,
                "issues_by_dataset": {},
                "issues_by_category": {},
                "top_rejection_reasons": [],
            }

    def generate_marketing_performance_report(self) -> Dict[str, Any]:
        """Compile complete marketing performance analytics."""
        return {
            "funnel": self.service.get_conversion_funnel(),
            "channel_performance": self.service.get_channel_performance(),
            "campaign_performance": self.service.get_campaign_performance(),
            "top_revenue_campaigns": self.service.get_revenue_analysis(top_n=5),
            "top_customers": self.service.get_customer_analysis(limit=10),
            "acquisition_sources": self.service.get_acquisition_sources(),
            "monthly_trends": self.service.get_monthly_revenue_trends(),
        }

    def generate_executive_summary_text(self) -> str:
        """Construct readable executive summary text report."""
        dq = self.get_data_quality_metrics()
        funnel = self.service.get_conversion_funnel()
        channels = self.service.get_channel_performance()
        top_camps = self.service.get_revenue_analysis(top_n=1)
        campaigns = self.service.get_campaign_performance()

        total_campaigns = len(campaigns)
        total_customers = 0
        if self.quality_report and "customers" in self.quality_report.datasets:
            total_customers = self.quality_report.datasets["customers"].accepted
        else:
            try:
                with get_connection(self.config) as conn:
                    with conn.cursor(row_factory=dict_row) as cur:
                        cur.execute("SELECT count(*) AS c FROM processed_customers;")
                        row = cur.fetchone()
                        total_customers = row["c"] if row else 0
            except Exception:
                total_customers = 0

        total_events = (
            funnel.get("total_impressions", 0)
            + funnel.get("total_clicks", 0)
            + funnel.get("total_conversions", 0)
        )
        total_revenue = sum(float(c.get("total_revenue", 0.0)) for c in campaigns)
        overall_conv_rate = float(funnel.get("overall_conversion_pct", 0.0) or 0.0)

        best_channel_rev = channels[0] if channels else {}
        # Highest ROAS channel
        best_channel_roas = max(channels, key=lambda x: float(x.get("roas") or 0.0)) if channels else {}

        top_campaign = top_camps[0] if top_camps else {}

        lines = [
            "================================================================================",
            "                   FUNNELFORGE EXECUTIVE MARKETING SUMMARY",
            "================================================================================",
            f"Generated At: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "1. PORTFOLIO SCALE & TRAFFIC",
            f"  • Total Marketing Campaigns : {total_campaigns:>8,d}",
            f"  • Total Validated Customers : {total_customers:>8,d}",
            f"  • Total Validated Events    : {total_events:>8,d}",
            f"    - Impressions             : {funnel.get('total_impressions', 0):>8,d}",
            f"    - Clicks                  : {funnel.get('total_clicks', 0):>8,d}",
            f"    - Conversions             : {funnel.get('total_conversions', 0):>8,d}",
            "",
            "2. FINANCIAL & CONVERSION HIGHLIGHTS",
            f"  • Total Conversion Revenue  : ${total_revenue:>11,.2f}",
            f"  • Funnel Conversion Rate    : {overall_conv_rate:>7.2f}%",
            f"  • Highest Revenue Channel   : {best_channel_rev.get('channel', 'N/A')} (${float(best_channel_rev.get('total_revenue', 0.0)):,.2f})",
            f"  • Highest ROAS Channel      : {best_channel_roas.get('channel', 'N/A')} ({float(best_channel_roas.get('roas', 0.0)):.2f}x return)",
            f"  • Top Revenue Campaign      : {top_campaign.get('campaign_name', 'N/A')} (${float(top_campaign.get('campaign_revenue', 0.0)):,.2f})",
            "",
            "3. DATA QUALITY & GOVERNANCE OBSERVATIONS",
            f"  • Total Records Examined    : {dq.get('total_examined', 0):>8,d}",
            f"  • Validated & Accepted      : {dq.get('total_accepted', 0):>8,d} ({dq.get('overall_acceptance_rate', 100.0):.1f}%)",
            f"  • Quarantined / Rejected    : {dq.get('total_rejected', 0):>8,d} ({dq.get('overall_rejection_rate', 0.0):.1f}%)",
        ]

        ds_issues = dq.get("issues_by_dataset", {})
        if ds_issues:
            lines.append("  • Quarantined by Dataset:")
            for ds, count in sorted(ds_issues.items(), key=lambda x: -x[1]):
                lines.append(f"    - {ds:<14}: {count:>6,d} records")

        cat_issues = dq.get("issues_by_category", {})
        if cat_issues:
            lines.append("  • Primary Issue Categories:")
            for cat, count in sorted(cat_issues.items(), key=lambda x: -x[1]):
                lines.append(f"    - {cat:<24}: {count:>6,d}")

        lines.extend([
            "================================================================================",
            "End of Executive Summary.",
            "================================================================================",
        ])

        return "\n".join(lines)

    def export_all(self, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """Export all reports into CSV, JSON, and TXT files in output_dir."""
        target_dir = output_dir or (PROJECT_ROOT / "reports" / "generated")
        target_dir.mkdir(parents=True, exist_ok=True)
        generated_files: Dict[str, Path] = {}

        # 1. Export CSV reports
        camp_df = self.service.get_campaign_performance(as_df=True)
        chan_df = self.service.get_channel_performance(as_df=True)
        cust_df = self.service.get_customer_analysis(as_df=True)
        rev_df = self.service.get_revenue_analysis(as_df=True)

        camp_path = target_dir / "campaign_performance.csv"
        chan_path = target_dir / "channel_performance.csv"
        cust_path = target_dir / "customer_analysis.csv"
        rev_path = target_dir / "revenue_analysis.csv"

        camp_df.to_csv(camp_path, index=False)
        chan_df.to_csv(chan_path, index=False)
        cust_df.to_csv(cust_path, index=False)
        rev_df.to_csv(rev_path, index=False)

        generated_files["campaign_performance_csv"] = camp_path
        generated_files["channel_performance_csv"] = chan_path
        generated_files["customer_analysis_csv"] = cust_path
        generated_files["revenue_analysis_csv"] = rev_path

        # 2. Export Consolidated JSON report
        dq_metrics = self.get_data_quality_metrics()
        mkt_metrics = self.generate_marketing_performance_report()

        consolidated_json = {
            "metadata": {
                "system": "FunnelForge",
                "version": "0.4.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "data_quality_report": dq_metrics,
            "marketing_performance_report": mkt_metrics,
        }

        json_path = target_dir / "funnel_report.json"
        json_path.write_text(
            json.dumps(consolidated_json, indent=2, default=json_serializer),
            encoding="utf-8",
        )
        generated_files["funnel_report_json"] = json_path

        # 3. Export Executive Summary TXT
        txt_content = self.generate_executive_summary_text()
        txt_path = target_dir / "executive_summary.txt"
        txt_path.write_text(txt_content, encoding="utf-8")
        generated_files["executive_summary_txt"] = txt_path

        logger.info(
            "Successfully exported %d reports to %s",
            len(generated_files),
            target_dir,
        )
        return generated_files
