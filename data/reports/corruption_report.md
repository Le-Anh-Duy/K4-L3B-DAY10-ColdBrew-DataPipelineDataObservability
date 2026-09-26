# Corruption Report — Baseline vs Corrupted vs Repaired

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired | Corrupted - Baseline | Repaired - Corrupted |
| --- | ---: | ---: | ---: | ---: | ---: |
| samples | 10 | 10 | 10 | N/A | N/A |
| retrieval_hit_rate | 1.0 | 0.8 | 1.0 | -0.2000 | +0.2000 |
| mean_token_f1 | 1.0 | 0.674074074074074 | 1.0 | -0.3259 | +0.3259 |
| judge_accuracy | 1.0 | 0.7 | 1.0 | -0.3000 | +0.3000 |
| mean_judge_score | 5 | 3.8 | 5 | -1.2000 | +1.2000 |

| Signal | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Quality status | N/A | FAIL | PASS |
| Freshness status | N/A | FAIL | PASS |
| Stale rows | N/A | 12 | 1 |
| Stale ratio | N/A | 0.5714285714285714 | 0.041666666666666664 |

Baseline quality and freshness are N/A because they are not inputs to this report function.

## Data quality details

### Corrupted checks

Overall quality: **FAIL**  
GX checks: **FAIL**  
Rows: **21**

| Check | Column | Status | Observed |
| --- | --- | --- | --- |
| expect_table_row_count_to_be_between | N/A | PASS | 21 |
| expect_column_values_to_not_be_null | paper_id | PASS | 0 unexpected / 21 rows |
| expect_column_values_to_be_unique | paper_id | FAIL | 4 unexpected / 21 rows |
| expect_column_value_lengths_to_be_between | paper_id | PASS | 0 unexpected / 21 rows |
| expect_column_values_to_not_be_null | title | PASS | 0 unexpected / 21 rows |
| expect_column_value_lengths_to_be_between | title | FAIL | 3 unexpected / 21 rows |
| expect_column_values_to_not_be_null | summary | PASS | 0 unexpected / 21 rows |
| expect_column_value_lengths_to_be_between | summary | FAIL | 2 unexpected / 21 rows |

### Repaired checks

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

## Freshness details

### Corrupted freshness

| Signal | Value |
| --- | --- |
| Status | FAIL |
| Latest published | 2026-06-04 |
| Oldest published | 2025-01-21 |
| Stale rows | 12 |
| Total rows | 21 |
| Stale ratio | 0.5714285714285714 |
| Age threshold (days) | 180 |
| Maximum stale ratio | 0.25 |

### Repaired freshness

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
