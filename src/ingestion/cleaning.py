from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd

from core.utils import compact_join
from ingestion.crossref import PaperRecord, clean_summary, clean_text, unique_ordered

CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "abs_url",
    "pdf_url",
    "comment",
    "text_for_embedding",
]


def build_text_for_embedding(row: pd.Series) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Categories: {row['categories_joined']}",
            f"Published: {row['published']}",
            f"Summary: {row['summary']}",
        ]
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    df = pd.DataFrame([asdict(record) for record in records])
    if df.empty:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    # 1. Normalize text / list fields.
    df["paper_id"] = df["paper_id"].fillna("").astype(str).str.strip().str.lower()
    for column in ["title", "primary_category", "abs_url", "pdf_url", "comment"]:
        df[column] = df[column].map(clean_text)
    df["summary"] = df["summary"].map(clean_summary)
    for column in ["authors", "categories"]:
        df[column] = df[column].map(lambda items: unique_ordered([clean_text(i) for i in items or []]))
    df["primary_category"] = df["primary_category"].where(
        df["primary_category"] != "", df["categories"].map(lambda c: c[0] if c else "")
    )

    # 2. Parse dates; invalid published -> drop, missing updated -> published.
    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    updated = pd.to_datetime(df["updated"], errors="coerce", utc=True).fillna(published)
    df = df[published.notna()].copy()
    published, updated = published[df.index], updated[df.index]
    df["published"] = published.dt.strftime("%Y-%m-%d")
    df["updated"] = updated.dt.strftime("%Y-%m-%d")

    # 3. age_days (future dates clipped to 0).
    run_ts = pd.Timestamp(run_date if run_date.tzinfo else run_date.replace(tzinfo=timezone.utc)).normalize()
    df["age_days"] = (run_ts - published.dt.normalize()).dt.days.clip(lower=0).astype(int)

    # 5. Filter bad rows and dedupe by paper_id, keeping the most recently updated record.
    df = df[(df["paper_id"] != "") & (df["title"] != "") & (df["summary"] != "")]
    df = df.assign(_updated=updated[df.index]).sort_values(["_updated", "paper_id"], ascending=[False, True])
    df = df.drop_duplicates(subset="paper_id", keep="first").drop(columns="_updated")

    # 4. Helper columns.
    df["authors_joined"] = df["authors"].map(compact_join)
    df["categories_joined"] = df["categories"].map(compact_join)
    df["summary_chars"] = df["summary"].str.len().astype(int)
    df["text_for_embedding"] = df.apply(build_text_for_embedding, axis=1) if len(df) else ""

    # 6. Deterministic order: newest first.
    df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df[CLEAN_COLUMNS]
