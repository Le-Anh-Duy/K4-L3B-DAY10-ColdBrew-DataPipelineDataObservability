from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd

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


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Any) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: str | Path) -> pd.DataFrame:
    """Simulate 6 realistic data corruption scenarios on a cleaned DataFrame.

    Scenarios:
    1. Drop latest records: Drop ~20% of newest published records (loss in transit / crawler drop).
    2. Blank summary: Erase summaries on selected records (scraping / extraction nulls).
    3. Inject noise: Inject garbage corrupt tokens into summaries (OCR / encoding corruption).
    4. Truncate title: Truncate titles to < 8 chars (violates min length constraint and breaks title lookup).
    5. Stale date: Shift publication dates back by 500 days (violates Freshness SLA: > 25% records older than 180 days).
    6. Duplicate rows: Clone records to produce duplicate paper_ids (violates primary key uniqueness).
    7. Rebuild text_for_embedding: Recompute text representation for ChromaDB vector re-indexing.
    8. Write corruption log: Persist comprehensive audit metadata into output_log_path.
    """
    corrupted = df.copy(deep=True)
    initial_count = len(corrupted)
    log_entries: list[dict[str, Any]] = []

    # Ensure chronological order (newest first) before dropping
    if "published" in corrupted.columns:
        corrupted = corrupted.sort_values(
            ["published", "paper_id"], ascending=[False, True]
        ).reset_index(drop=True)

    # 1. Drop latest records (~20% newest records)
    drop_count = max(1, round(initial_count * 0.20))
    dropped_subset = corrupted.iloc[:drop_count]
    dropped_ids = dropped_subset["paper_id"].tolist()
    corrupted = corrupted.iloc[drop_count:].copy().reset_index(drop=True)

    log_entries.append({
        "scenario": "drop_latest_records",
        "description": "Dropped ~20% of the newest records to simulate ingestion pipeline drop / network partition.",
        "affected_count": len(dropped_ids),
        "affected_paper_ids": dropped_ids,
        "parameters": {"drop_ratio": 0.20, "dropped_count": drop_count},
    })

    # 2. Blank summary (erase summary on selected rows)
    blank_indices = [idx for idx in [2, 5] if idx < len(corrupted)]
    blanked_ids: list[str] = []
    for idx in blank_indices:
        paper_id = str(corrupted.at[idx, "paper_id"])
        blanked_ids.append(paper_id)
        corrupted.at[idx, "summary"] = ""
        corrupted.at[idx, "summary_chars"] = 0

    log_entries.append({
        "scenario": "blank_summary",
        "description": "Erased summaries to simulate text extraction failures; triggers non-null and min-length data quality violations.",
        "affected_count": len(blanked_ids),
        "affected_paper_ids": blanked_ids,
        "parameters": {"target_indices": blank_indices},
    })

    # 3. Inject noise (insert garbage characters into summaries)
    noise_indices = [idx for idx in [3, 7] if idx < len(corrupted)]
    noise_ids: list[str] = []
    noise_payload = " [CORRUPTED_STREAM_#$!@%*&_0xDEADBEEF_GARBAGE] "
    for idx in noise_indices:
        paper_id = str(corrupted.at[idx, "paper_id"])
        noise_ids.append(paper_id)
        original_summary = str(corrupted.at[idx, "summary"])
        corrupted.at[idx, "summary"] = noise_payload * 2 + original_summary[:40] + noise_payload
        corrupted.at[idx, "summary_chars"] = len(corrupted.at[idx, "summary"])

    log_entries.append({
        "scenario": "inject_noise",
        "description": "Injected synthetic corrupt tokens into summaries to disrupt vector embeddings and degrade semantic retrieval.",
        "affected_count": len(noise_ids),
        "affected_paper_ids": noise_ids,
        "parameters": {"target_indices": noise_indices, "noise_marker": "0xDEADBEEF"},
    })

    # 4. Truncate title (< 8 characters)
    truncate_indices = [idx for idx in [1, 6] if idx < len(corrupted)]
    truncated_ids: list[str] = []
    for idx in truncate_indices:
        paper_id = str(corrupted.at[idx, "paper_id"])
        truncated_ids.append(paper_id)
        original_title = str(corrupted.at[idx, "title"])
        corrupted.at[idx, "title"] = original_title[:5] if len(original_title) >= 5 else "Err"

    log_entries.append({
        "scenario": "truncate_title",
        "description": "Truncated titles to < 8 chars; violates title length constraints and breaks exact title search lookups.",
        "affected_count": len(truncated_ids),
        "affected_paper_ids": truncated_ids,
        "parameters": {"target_indices": truncate_indices, "max_length": 5},
    })

    # 5. Stale date (shift published dates back by 500 days)
    stale_count = max(4, round(len(corrupted) * 0.45))
    stale_indices = list(range(0, min(len(corrupted), stale_count)))
    stale_ids: list[str] = []
    days_back = 500
    for idx in stale_indices:
        paper_id = str(corrupted.at[idx, "paper_id"])
        stale_ids.append(paper_id)
        try:
            curr_date = pd.to_datetime(corrupted.at[idx, "published"])
            new_date = curr_date - pd.Timedelta(days=days_back)
            corrupted.at[idx, "published"] = new_date.strftime("%Y-%m-%d")
        except Exception:
            corrupted.at[idx, "published"] = "2024-01-01"
        corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + days_back

    log_entries.append({
        "scenario": "stale_date",
        "description": "Subtracted 500 days from published date so age_days > 180, forcing Freshness SLA failure (> 25% stale rows).",
        "affected_count": len(stale_ids),
        "affected_paper_ids": stale_ids,
        "parameters": {"days_subtracted": days_back, "target_indices": stale_indices},
    })

    # 6. Duplicate rows (clone records to violate uniqueness)
    dup_count = min(2, len(corrupted))
    duplicated_subset = corrupted.iloc[:dup_count].copy()
    duplicated_ids = duplicated_subset["paper_id"].tolist()
    corrupted = pd.concat([corrupted, duplicated_subset], ignore_index=True)

    log_entries.append({
        "scenario": "duplicate_rows",
        "description": "Duplicated rows to introduce duplicate paper_id values and violate primary key uniqueness.",
        "affected_count": len(duplicated_ids),
        "duplicated_paper_ids": duplicated_ids,
        "parameters": {"duplicate_count": dup_count},
    })

    # 7. Rebuild text_for_embedding
    corrupted["summary_chars"] = corrupted["summary"].fillna("").astype(str).str.len().astype(int)
    corrupted["text_for_embedding"] = corrupted.apply(build_text_for_embedding, axis=1)

    # 8. Write corruption log into output_log_path
    log_path = Path(output_log_path)
    _ensure_parent(log_path)
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_rows": initial_count,
        "corrupted_rows": len(corrupted),
        "total_scenarios": len(log_entries),
        "scenarios": log_entries,
        "summary": {
            "dropped_count": len(dropped_ids),
            "blanked_count": len(blanked_ids),
            "noise_injected_count": len(noise_ids),
            "title_truncated_count": len(truncated_ids),
            "stale_date_count": len(stale_ids),
            "duplicate_added_count": len(duplicated_ids),
        },
    }
    _write_json(log_path, log_payload)

    return corrupted[CLEAN_COLUMNS]
