# Phase 1 Report — Baseline

## Source summary

| Field | Value |
| --- | --- |
| source_api | Crossref REST API |
| source_query | agentic retrieval augmented generation large language model |
| source_filter | from-pub-date:2026-03-30,has-abstract:true |
| raw_records_count | 24 |
| clean_rows_count | 24 |


## Evaluation metrics

| Metric | Value |
| --- | ---: |
| samples | 10 |
| retrieval_hit_rate | 1.0 |
| mean_token_f1 | 1.0 |
| judge_accuracy | 1.0 |
| mean_judge_score | 5 |

Ragas: {"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."}

## Data quality

### Baseline checks

Overall quality: **PASS**  
GX checks: **PASS**  
Rows: **24**

| Check | Column | Status | Observed |
| --- | --- | --- | --- |
| expect_table_row_count_to_be_between | N/A | PASS | 24 |
| expect_column_values_to_not_be_null | paper_id | PASS | 0 unexpected / 24 rows |
| expect_column_values_to_be_unique | paper_id | PASS | 0 unexpected / 24 rows |
| expect_column_value_lengths_to_be_between | paper_id | PASS | 0 unexpected / 24 rows |
| expect_column_values_to_not_be_null | title | PASS | 0 unexpected / 24 rows |
| expect_column_value_lengths_to_be_between | title | PASS | 0 unexpected / 24 rows |
| expect_column_values_to_not_be_null | summary | PASS | 0 unexpected / 24 rows |
| expect_column_value_lengths_to_be_between | summary | PASS | 0 unexpected / 24 rows |

## Freshness

### Baseline freshness

| Signal | Value |
| --- | --- |
| Status | PASS |
| Latest published | 2026-07-22 |
| Oldest published | 2026-03-28 |
| Stale rows | 1 |
| Total rows | 24 |
| Stale ratio | 0.041666666666666664 |
| Age threshold (days) | 180 |
| Maximum stale ratio | 0.25 |
