from __future__ import annotations

from math import ceil
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


REQUIRED_COLUMNS = {"paper_id", "title", "summary", "published", "age_days"}
MAX_STALE_RATIO = 0.25


def _freshness_stats(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    total_rows = len(df)
    dates = pd.to_datetime(
        df.get("published", pd.Series(index=df.index, dtype=object)), errors="coerce", utc=True
    )
    ages = pd.to_numeric(
        df.get("age_days", pd.Series(index=df.index, dtype=object)), errors="coerce"
    )
    stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else None
    valid_dates_and_ages = bool(
        total_rows and dates.notna().all() and ages.notna().all() and ages.ge(0).all()
    )

    return {
        "latest_published": dates.max().date().isoformat() if dates.notna().any() else None,
        "oldest_published": dates.min().date().isoformat() if dates.notna().any() else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": MAX_STALE_RATIO,
        "is_fresh": bool(valid_dates_and_ages and stale_ratio <= MAX_STALE_RATIO),
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate cleaned papers with GX 1.x and include the freshness gate."""
    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    freshness = _freshness_stats(df, settings)
    checks: list[dict[str, Any]] = []
    gx_success = False

    if missing_columns:
        checks.append({
            "name": "required_columns",
            "success": False,
            "missing_columns": missing_columns,
        })
    else:
        context = gx.get_context(mode="ephemeral")
        source = context.data_sources.add_pandas(name="papers_source")
        asset = source.add_dataframe_asset(name="papers_asset")
        batch_definition = asset.add_batch_definition_whole_dataframe("papers_batch")
        batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

        suite = gx.ExpectationSuite(name="papers_quality_suite")
        suite.add_expectation(
            gx.expectations.ExpectTableRowCountToBeBetween(
                min_value=max(1, ceil(settings.max_results * 0.85)),
                max_value=settings.max_results,
            )
        )
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"))
        suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(column="paper_id", min_value=1))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="title"))
        suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="summary"))
        suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20))

        validation = batch.validate(suite).to_json_dict()
        gx_success = bool(validation["success"])
        checks = [
            {
                "name": result["expectation_config"]["type"],
                "column": result["expectation_config"]["kwargs"].get("column"),
                "success": bool(result["success"]),
                "result": result["result"],
            }
            for result in validation["results"]
        ]

    report = {
        "report_name": report_name,
        "success": bool(gx_success and freshness["is_fresh"]),
        "gx_success": gx_success,
        "row_count": len(df),
        "checks": checks,
        "freshness": freshness,
    }
    report_path = settings.paths.quality_dir / f"{safe_slug(report_name)}_quality_report.json"
    write_json(report_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Write a freshness summary for the provided paper dataframe."""
    report = _freshness_stats(df, settings)
    write_json(report_path, report)
    return report
