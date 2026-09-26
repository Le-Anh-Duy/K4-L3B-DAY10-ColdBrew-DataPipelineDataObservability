from __future__ import annotations

import json
from math import isfinite
from numbers import Real
from typing import Any

from core.utils import write_text


METRIC_NAMES = (
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)


def _cell(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, Real) and not isinstance(value, bool) and not isfinite(float(value)):
        return "N/A"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _status(value: Any) -> str:
    if value is None:
        return "N/A"
    return "PASS" if value is True else "FAIL" if value is False else _cell(value)


def _metric_delta(before: Any, after: Any) -> str:
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in (before, after)):
        return "N/A"
    difference = float(after) - float(before)
    return f"{difference:+.4f}" if isfinite(difference) else "N/A"


def _check_rows(quality: dict[str, Any]) -> list[str]:
    rows = []
    for check in quality.get("checks", []):
        detail = check.get("result") or {}
        if "missing_columns" in check:
            observed = ", ".join(check["missing_columns"])
        elif "observed_value" in detail:
            observed = detail["observed_value"]
        elif "unexpected_count" in detail:
            observed = f"{detail['unexpected_count']} unexpected / {detail.get('element_count', 'N/A')} rows"
        else:
            observed = detail or None
        rows.append(
            f"| {_cell(check.get('name'))} | {_cell(check.get('column'))} | "
            f"{_status(check.get('success'))} | {_cell(observed)} |"
        )
    return rows or ["| N/A | N/A | N/A | No check results supplied |"]


def _quality_section(heading: str, quality: dict[str, Any]) -> list[str]:
    return [
        f"### {heading}",
        "",
        f"Overall quality: **{_status(quality.get('success'))}**  ",
        f"GX checks: **{_status(quality.get('gx_success'))}**  ",
        f"Rows: **{_cell(quality.get('row_count'))}**",
        "",
        "| Check | Column | Status | Observed |",
        "| --- | --- | --- | --- |",
        *_check_rows(quality),
        "",
    ]


def _freshness_section(heading: str, freshness: dict[str, Any]) -> list[str]:
    fields = (
        ("Status", _status(freshness.get("is_fresh"))),
        ("Latest published", freshness.get("latest_published")),
        ("Oldest published", freshness.get("oldest_published")),
        ("Stale rows", freshness.get("stale_rows")),
        ("Total rows", freshness.get("total_rows")),
        ("Stale ratio", freshness.get("stale_ratio")),
        ("Age threshold (days)", freshness.get("threshold_days")),
        ("Maximum stale ratio", freshness.get("max_stale_ratio")),
    )
    return [
        f"### {heading}",
        "",
        "| Signal | Value |",
        "| --- | --- |",
        *(f"| {label} | {_cell(value)} |" for label, value in fields),
        "",
    ]

def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline report from measured pipeline artifacts."""
    lines = [
        "# Phase 1 Report — Baseline",
        "",
        "## Source summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        *(f"| {_cell(key)} | {_cell(value)} |" for key, value in source_summary.items()),
        "" if source_summary else "| N/A | No source summary supplied |",
        "",
        "## Evaluation metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| samples | {_cell(metrics.get('samples'))} |",
        *(f"| {name} | {_cell(metrics.get(name))} |" for name in METRIC_NAMES),
        "",
        f"Ragas: {_cell(metrics.get('ragas'))}",
        "",
        "## Data quality",
        "",
        *_quality_section("Baseline checks", quality),
        "## Freshness",
        "",
        *_freshness_section("Baseline freshness", freshness),
    ]
    write_text(report_path, "\n".join(lines).rstrip() + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Compare the three measured evaluation states without inventing missing signals."""
    lines = [
        "# Corruption Report — Baseline vs Corrupted vs Repaired",
        "",
        "## Evaluation metrics",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corrupted - Baseline | Repaired - Corrupted |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        f"| samples | {_cell(baseline_metrics.get('samples'))} | "
        f"{_cell(corrupted_metrics.get('samples'))} | {_cell(repaired_metrics.get('samples'))} | N/A | N/A |",
    ]
    for name in METRIC_NAMES:
        baseline = baseline_metrics.get(name)
        corrupted = corrupted_metrics.get(name)
        repaired = repaired_metrics.get(name)
        lines.append(
            f"| {name} | {_cell(baseline)} | {_cell(corrupted)} | {_cell(repaired)} | "
            f"{_metric_delta(baseline, corrupted)} | {_metric_delta(corrupted, repaired)} |"
        )

    sample_counts = [metrics.get("samples") for metrics in (baseline_metrics, corrupted_metrics, repaired_metrics)]
    if all(isinstance(count, int) and not isinstance(count, bool) for count in sample_counts):
        if len(set(sample_counts)) != 1:
            lines.extend(["", "Warning: sample counts differ; verify that all three runs used the same test set."])

    lines.extend(
        [
            "",
            "| Signal | Baseline | Corrupted | Repaired |",
            "| --- | --- | --- | --- |",
            f"| Quality status | N/A | {_status(corrupted_quality.get('success'))} | "
            f"{_status(repaired_quality.get('success'))} |",
            f"| Freshness status | N/A | {_status(corrupted_freshness.get('is_fresh'))} | "
            f"{_status(repaired_freshness.get('is_fresh'))} |",
            f"| Stale rows | N/A | {_cell(corrupted_freshness.get('stale_rows'))} | "
            f"{_cell(repaired_freshness.get('stale_rows'))} |",
            f"| Stale ratio | N/A | {_cell(corrupted_freshness.get('stale_ratio'))} | "
            f"{_cell(repaired_freshness.get('stale_ratio'))} |",
            "",
            "Baseline quality and freshness are N/A because they are not inputs to this report function.",
            "",
            "## Data quality details",
            "",
            *_quality_section("Corrupted checks", corrupted_quality),
            *_quality_section("Repaired checks", repaired_quality),
            "## Freshness details",
            "",
            *_freshness_section("Corrupted freshness", corrupted_freshness),
            *_freshness_section("Repaired freshness", repaired_freshness),
        ]
    )
    write_text(report_path, "\n".join(lines).rstrip() + "\n")
