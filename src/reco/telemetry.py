"""Bounded in-memory Prometheus counters/histograms; no profile IDs in labels/logs."""

import threading
from collections import defaultdict


class Telemetry:
    buckets = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0)

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.counts: dict[tuple[str, str], int] = defaultdict(int)
        self.timings: dict[str, list[float]] = {}
        self.returned = 0

    def count(self, name: str, label: str) -> None:
        with self.lock:
            self.counts[(name, label)] += 1

    def observe(self, stage: str, seconds: float) -> None:
        with self.lock:
            histogram = self.timings.setdefault(stage, [0.0] * (len(self.buckets) + 2))
            for index, bound in enumerate(self.buckets):
                histogram[index] += seconds <= bound
            histogram[-2] += 1
            histogram[-1] += seconds

    def record_returned(self, count: int) -> None:
        with self.lock:
            self.returned += count

    def render(self, variant: str) -> str:
        with self.lock:
            lines = [
                f'reco_active_variant_info{{variant="{variant}"}} 1',
                f"reco_returned_items_total {self.returned}",
            ]
            for (name, label), count in sorted(self.counts.items()):
                lines.append(f'reco_{name}_total{{reason="{label}"}} {count}')
            lines.append("# TYPE reco_duration_seconds histogram")
            for stage, histogram in sorted(self.timings.items()):
                for index, bound in enumerate(self.buckets):
                    lines.append(
                        f'reco_duration_seconds_bucket{{stage="{stage}",le="{bound}"}} '
                        f"{histogram[index]}"
                    )
                lines.extend(
                    [
                        f'reco_duration_seconds_bucket{{stage="{stage}",le="+Inf"}} '
                        f"{histogram[-2]}",
                        f'reco_duration_seconds_count{{stage="{stage}"}} {histogram[-2]}',
                        f'reco_duration_seconds_sum{{stage="{stage}"}} {histogram[-1]}',
                    ]
                )
            return "\n".join(lines) + "\n"
