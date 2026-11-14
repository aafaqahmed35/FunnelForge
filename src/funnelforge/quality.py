"""Data quality metrics and report generation for FunnelForge."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class DatasetMetrics:
    """Metrics for an individual dataset."""
    name: str
    examined: int
    accepted: int
    rejected: int

    @property
    def acceptance_rate(self) -> float:
        return (self.accepted / self.examined * 100.0) if self.examined > 0 else 0.0

    @property
    def rejection_rate(self) -> float:
        return (self.rejected / self.examined * 100.0) if self.examined > 0 else 0.0


@dataclass
class QualityReport:
    """Consolidated data quality summary across all datasets."""
    datasets: Dict[str, DatasetMetrics]
    issues_by_category: Dict[str, int] = field(default_factory=dict)
    issues_by_dataset: Dict[str, int] = field(default_factory=dict)
    rejection_reasons_counter: Counter = field(default_factory=Counter)

    @property
    def total_examined(self) -> int:
        return sum(d.examined for d in self.datasets.values())

    @property
    def total_accepted(self) -> int:
        return sum(d.accepted for d in self.datasets.values())

    @property
    def total_rejected(self) -> int:
        return sum(d.rejected for d in self.datasets.values())

    @property
    def overall_acceptance_rate(self) -> float:
        return (
            (self.total_accepted / self.total_examined * 100.0)
            if self.total_examined > 0
            else 0.0
        )

    @property
    def overall_rejection_rate(self) -> float:
        return (
            (self.total_rejected / self.total_examined * 100.0)
            if self.total_examined > 0
            else 0.0
        )

    def print_report(self) -> None:
        """Print formatted quality report to console."""
        print("\n" + "=" * 70)
        print("                     DATA QUALITY REPORT")
        print("=" * 70)
        print(f"{'Dataset':<16} {'Examined':>10} {'Accepted':>10} {'Rejected':>10} {'Acceptance Rate':>18}")
        print("-" * 70)

        for name, m in self.datasets.items():
            print(
                f"{name.capitalize():<16} "
                f"{m.examined:>10,d} "
                f"{m.accepted:>10,d} "
                f"{m.rejected:>10,d} "
                f"{m.acceptance_rate:>17.1f}%"
            )

        print("-" * 70)
        print(
            f"{'Total':<16} "
            f"{self.total_examined:>10,d} "
            f"{self.total_accepted:>10,d} "
            f"{self.total_rejected:>10,d} "
            f"{self.overall_acceptance_rate:>17.1f}%"
        )
        print("=" * 70)
        print(f"Overall acceptance rate: {self.overall_acceptance_rate:.1f}%")
        print(f"Overall rejection rate:  {self.overall_rejection_rate:.1f}%\n")

        if self.issues_by_category:
            print("Issue Counts by Category:")
            for cat, count in sorted(self.issues_by_category.items(), key=lambda x: -x[1]):
                print(f"  • {cat:<26}: {count:>5,d}")
            print()

        if self.issues_by_dataset:
            print("Issue Counts by Source Dataset:")
            for ds, count in sorted(self.issues_by_dataset.items(), key=lambda x: -x[1]):
                print(f"  • {ds:<26}: {count:>5,d}")
            print()

        if self.rejection_reasons_counter:
            print("Top Rejection Reasons:")
            for reason, count in self.rejection_reasons_counter.most_common(5):
                print(f"  • [{count}x] {reason}")
            print("=" * 70 + "\n")

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON/logging."""
        return {
            "total_examined": self.total_examined,
            "total_accepted": self.total_accepted,
            "total_rejected": self.total_rejected,
            "overall_acceptance_rate": round(self.overall_acceptance_rate, 2),
            "overall_rejection_rate": round(self.overall_rejection_rate, 2),
            "datasets": {
                name: {
                    "examined": m.examined,
                    "accepted": m.accepted,
                    "rejected": m.rejected,
                    "acceptance_rate": round(m.acceptance_rate, 2),
                    "rejection_rate": round(m.rejection_rate, 2),
                }
                for name, m in self.datasets.items()
            },
            "issues_by_category": self.issues_by_category,
            "issues_by_dataset": self.issues_by_dataset,
            "top_rejection_reasons": self.rejection_reasons_counter.most_common(10),
        }

