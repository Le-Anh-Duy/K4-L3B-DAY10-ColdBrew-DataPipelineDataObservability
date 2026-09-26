from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import ensure_parent, now_utc, read_json, write_csv, write_json, write_text
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)


def _fallback_quality_checks(
    df: pd.DataFrame, settings: Settings, report_name: str, output_path: Path
) -> dict[str, Any]:
    total_rows = len(df)
    null_ids = int(df["paper_id"].isna().sum()) if "paper_id" in df else 0
    unique_ids = int(df["paper_id"].nunique()) if "paper_id" in df else 0
    null_titles = int(df["title"].isna().sum()) if "title" in df else 0
    short_titles = (
        int((df["title"].fillna("").astype(str).str.len() < 8).sum())
        if "title" in df
        else 0
    )
    null_summaries = int(df["summary"].isna().sum()) if "summary" in df else 0
    short_summaries = (
        int((df["summary"].fillna("").astype(str).str.len() < 20).sum())
        if "summary" in df
        else 0
    )
    stale_count = (
        int((df["age_days"] > settings.freshness_threshold_days).sum())
        if "age_days" in df
        else 0
    )

    success = (
        (null_ids == 0)
        and (unique_ids == total_rows)
        and (null_titles == 0)
        and (short_titles == 0)
        and (null_summaries == 0)
        and (short_summaries == 0)
    )

    report = {
        "report_name": report_name,
        "success": success,
        "total_rows": total_rows,
        "unique_paper_ids": unique_ids,
        "null_paper_ids": null_ids,
        "null_titles": null_titles,
        "short_titles": short_titles,
        "null_summaries": null_summaries,
        "short_summaries": short_summaries,
        "stale_rows": stale_count,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "expectations": [
            {
                "expectation": "ExpectTableRowCountToBeBetween",
                "success": 20 <= total_rows <= 30,
                "observed": total_rows,
            },
            {
                "expectation": "ExpectColumnValuesToNotBeNull(paper_id)",
                "success": null_ids == 0,
                "observed_nulls": null_ids,
            },
            {
                "expectation": "ExpectColumnValuesToBeUnique(paper_id)",
                "success": unique_ids == total_rows,
                "observed_unique": unique_ids,
            },
            {
                "expectation": "ExpectColumnValueLengthsToBeBetween(title)",
                "success": short_titles == 0,
                "observed_short": short_titles,
            },
            {
                "expectation": "ExpectColumnValuesToNotBeNull(summary)",
                "success": null_summaries == 0,
                "observed_nulls": null_summaries,
            },
        ],
    }
    ensure_parent(output_path)
    write_json(output_path, report)
    return report


def _fallback_freshness_report(
    df: pd.DataFrame, settings: Settings, output_path: Path
) -> dict[str, Any]:
    total_rows = len(df)
    stale_rows = (
        int((df["age_days"] > settings.freshness_threshold_days).sum())
        if "age_days" in df
        else 0
    )
    stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0
    is_fresh = stale_ratio <= 0.25
    latest_published = (
        str(df["published"].max()) if "published" in df and not df.empty else "N/A"
    )
    oldest_published = (
        str(df["published"].min()) if "published" in df and not df.empty else "N/A"
    )

    report = {
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
    }
    ensure_parent(output_path)
    write_json(output_path, report)
    return report


def _fallback_generate_phase1_report(
    report_path: Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Báo Cáo Pha 1 — Baseline Data Pipeline & Observability",
        "",
        f"> **Thời gian sinh báo cáo:** {now_str}  ",
        f"> **Nguồn dữ liệu:** {source_summary.get('source_api', 'Crossref REST API')}  ",
        f"> **Trạng thái Quality Gate:** {'PASSED (success=True)' if quality.get('success') else 'FAILED (success=False)'}  ",
        f"> **Trạng thái Freshness SLA:** {'FRESH (is_fresh=True)' if freshness.get('is_fresh') else 'STALE (is_fresh=False)'}",
        "",
        "---",
        "",
        "## 1. Tổng quan Ingestion & Data Lineage",
        "",
        f"- **API Endpoint / Query:** `{source_summary.get('source_query', '')}`",
        f"- **Filter:** `{source_summary.get('source_filter', '')}`",
        f"- **Số lượng Raw Records:** {source_summary.get('raw_records_count', 'N/A')}",
        f"- **Số lượng Clean Rows sau khử trùng & lọc:** {source_summary.get('clean_rows_count', 'N/A')}",
        "",
        "## 2. Kết quả Đánh Giá Baseline (RAG Evaluation)",
        "",
        "| Metric | Giá trị | Ngưỡng kỳ vọng | Đánh giá |",
        "|---|---:|---:|---|",
        f"| `retrieval_hit_rate` | {metrics.get('retrieval_hit_rate', 0.0):.4f} | >= 0.80 | {'Đạt chuẩn' if metrics.get('retrieval_hit_rate', 0.0) >= 0.80 else 'Chưa đạt'} |",
        f"| `mean_token_f1` | {metrics.get('mean_token_f1', 0.0):.4f} | >= 0.70 | {'Đạt chuẩn' if metrics.get('mean_token_f1', 0.0) >= 0.70 else 'Cần tối ưu'} |",
        f"| `judge_accuracy` | {metrics.get('judge_accuracy', 0.0):.4f} | >= 0.80 | {'Chính xác cao' if metrics.get('judge_accuracy', 0.0) >= 0.80 else 'Trung bình'} |",
        f"| `mean_judge_score` | {metrics.get('mean_judge_score', 0.0):.2f} / 5.0 | >= 4.0 | {'Tốt' if metrics.get('mean_judge_score', 0.0) >= 4.0 else 'Khá'} |",
        "",
        "## 3. Data Observability & Freshness SLA",
        "",
        "- **Great Expectations Quality Check:**",
        f"  - Tổng số bản ghi kiểm tra: `{quality.get('total_rows', 'N/A')}`",
        f"  - Bản ghi unique `paper_id`: `{quality.get('unique_paper_ids', 'N/A')}`",
        f"  - Số lượng title bị null / quá ngắn: `{quality.get('short_titles', 0)}`",
        f"  - Số lượng summary bị null / rỗng: `{quality.get('short_summaries', 0)}`",
        f"  - Kết luận: **{'PASS' if quality.get('success') else 'FAIL'}**",
        "",
        "- **Freshness SLA Analysis:**",
        f"  - Ngưỡng thời gian tối đa: `{freshness.get('freshness_threshold_days', 180)}` ngày",
        f"  - Số bài báo quá hạn (`age_days > 180`): `{freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)}` ({freshness.get('stale_ratio', 0.0) * 100:.1f}%)",
        f"  - Giới hạn SLA cho phép: `<= 25%`",
        f"  - Kết luận SLA: **{'FRESH - Đạt SLA' if freshness.get('is_fresh') else 'STALE - Vi phạm SLA'}**",
        "",
        "## 4. Danh mục Artifacts đã tạo",
        "",
        "- `data/clean/papers_clean.csv` & `papers_clean.json`",
        "- `data/embeddings/papers_embeddings.json` (ChromaDB collection `papers-baseline`)",
        "- `data/eval/test_set.json` (Bộ benchmark 10 câu hỏi)",
        "- `data/results/baseline_metrics.json` & `baseline_answers.json`",
        "- `data/quality/baseline_quality_report.json` & `freshness_report.json`",
        "- `data/reports/phase1_report.md`",
        "",
    ]
    ensure_parent(report_path)
    write_text(report_path, "\n".join(lines))


def main() -> None:
    """Execute the Phase 1 Baseline Pipeline end-to-end.

    1. Load settings.
    2. Load or fetch raw records.
    3. Clean data and construct text_for_embedding.
    4. Save cleaned CSV and JSON artifacts.
    5. Build ChromaDB baseline vector index.
    6. Build or load evaluation test set.
    7. Evaluate baseline RAG retrieval and answer metrics.
    8. Run Great Expectations quality checks and Freshness SLA analysis.
    9. Generate Phase 1 markdown report.
    10. Optionally run agent demo on sample questions.
    """
    print("=" * 60)
    print("STARTING PHASE 1: BASELINE PIPELINE END-TO-END")
    print("=" * 60)

    # 1. Load settings
    settings = load_settings()
    print(f"[1/10] Loaded settings. LLM Provider: {settings.llm_provider} ({settings.model_name})")

    # 2. Load or fetch raw records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print(f"[2/10] Fetching source records from {settings.source_api}...")
        records = fetch_source_records(settings)
    else:
        print(f"[2/10] Loading raw records from {settings.paths.raw_records_json.name}...")
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"       Loaded {len(records)} raw records.")

    # 3. Clean data
    run_date = now_utc()
    clean_df = build_clean_dataframe(records, run_date)
    print(f"[3/10] Cleaned data: {len(clean_df)} valid, deduplicated records.")

    # 4. Save clean CSV/JSON
    write_csv(clean_df, settings.paths.clean_csv)
    ensure_parent(settings.paths.clean_json)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)
    print(f"[4/10] Saved clean artifacts to {settings.paths.clean_csv.name} and {settings.paths.clean_json.name}.")

    # 5. Build Chroma index
    print(f"[5/10] Indexing {len(clean_df)} documents into ChromaDB collection '{settings.baseline_collection_name}'...")
    index = LocalEmbeddingIndex.build(
        df=clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"       Indexed {len(index.documents)} documents successfully.")

    # 6. Build or load evaluation set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("[6/10] Building fresh evaluation test set...")
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        print(f"[6/10] Loading existing evaluation test set from {settings.paths.eval_testset.name}...")
        test_set = read_json(settings.paths.eval_testset)
    print(f"       Evaluation test set has {len(test_set)} questions.")

    # 7. Evaluate
    print("[7/10] Evaluating baseline retrieval and QA performance...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    baseline_metrics = bundle.summary
    print(f"       Baseline Hit Rate: {baseline_metrics.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"       Baseline Mean Token F1: {baseline_metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"       Baseline Judge Accuracy: {baseline_metrics.get('judge_accuracy', 0.0):.4f}")
    print(f"       Baseline Mean Judge Score: {baseline_metrics.get('mean_judge_score', 0.0):.2f}/5.0")

    # 8. Run quality checks and freshness report
    print("[8/10] Running Data Quality Gate and Freshness SLA...")
    quality_result: dict[str, Any]
    freshness_result: dict[str, Any]
    try:
        from observability.quality import build_freshness_report, run_data_quality_checks

        quality_result = run_data_quality_checks(clean_df, settings, "baseline")
        freshness_result = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    except (NotImplementedError, ImportError, AttributeError):
        quality_result = _fallback_quality_checks(
            clean_df, settings, "baseline", settings.paths.baseline_quality_report
        )
        freshness_result = _fallback_freshness_report(
            clean_df, settings, settings.paths.freshness_report
        )
    print(f"       Quality Gate: {'PASSED' if quality_result.get('success') else 'FAILED'}")
    print(f"       Freshness SLA: {'FRESH' if freshness_result.get('is_fresh') else 'STALE'} "
          f"({freshness_result.get('stale_rows', 0)}/{freshness_result.get('total_rows', 0)} stale)")

    # 9. Create markdown report
    print(f"[9/10] Generating baseline report at {settings.paths.baseline_report.name}...")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_records_count": len(records),
        "clean_rows_count": len(clean_df),
    }
    try:
        from observability.reporting import generate_phase1_report

        generate_phase1_report(
            report_path=settings.paths.baseline_report,
            source_summary=source_summary,
            metrics=baseline_metrics,
            quality=quality_result,
            freshness=freshness_result,
        )
    except (NotImplementedError, ImportError, AttributeError):
        _fallback_generate_phase1_report(
            report_path=settings.paths.baseline_report,
            source_summary=source_summary,
            metrics=baseline_metrics,
            quality=quality_result,
            freshness=freshness_result,
        )
    print(f"       Phase 1 report saved to {settings.paths.baseline_report}.")

    # 10. Demo agent on sample questions
    print("[10/10] Running Agent QA demo on sample questions...")
    demo_results = []
    try:
        from retrieval.agent import build_agent, run_agent_question

        agent = build_agent(settings, index)
        sample_questions = [
            "What is the summary of the paper 'Continuous Benchmark Evaluation for Enterprise Retrieval Pipelines'?",
            "Who authored 'Synthetic Corruption Testing: Stress-Testing Vector Search Robustness'?",
        ]
        for q in sample_questions:
            try:
                ans = run_agent_question(agent, q)
                demo_results.append({"question": q, "answer": ans})
                print(f"       Q: {q[:50]}... -> Answered ({len(ans)} chars)")
            except Exception as exc:
                demo_results.append({"question": q, "error": str(exc)})
        if demo_results:
            ensure_parent(settings.paths.demo_answers)
            write_json(settings.paths.demo_answers, demo_results)
    except Exception as exc:
        print(f"       Agent demo skipped or encountered error: {exc}")

    print("=" * 60)
    print("PHASE 1 COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
