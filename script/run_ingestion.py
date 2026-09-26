from __future__ import annotations

from core.config import load_settings
from core.utils import ensure_parent, now_utc, write_csv
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records


def main() -> None:
    """Raw ingestion + cleaning: ghi data/raw/*.json va data/clean/papers_clean.{csv,json}."""
    settings = load_settings()
    records = fetch_source_records(settings)
    df = build_clean_dataframe(records, now_utc())

    write_csv(df, settings.paths.clean_csv)
    ensure_parent(settings.paths.clean_json)
    df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)

    stale = int((df["age_days"] > settings.freshness_threshold_days).sum())
    print(f"Raw records: {len(records)} -> {settings.paths.raw_records_json.name}")
    print(f"Clean rows: {len(df)} -> {settings.paths.clean_csv.name}, {settings.paths.clean_json.name}")
    print(f"age_days > {settings.freshness_threshold_days}: {stale}/{len(df)}")


if __name__ == "__main__":
    main()
