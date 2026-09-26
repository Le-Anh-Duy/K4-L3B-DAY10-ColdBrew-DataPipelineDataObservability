from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


QUESTION_TYPES = (
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "authors",
)
REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
}


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic ten-question benchmark from cleaned paper data."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(sorted(missing))}")

    papers = df.sort_values(["published", "paper_id"], ascending=[False, True]).to_dict("records")
    if len(papers) < len(QUESTION_TYPES):
        raise ValueError(f"At least {len(QUESTION_TYPES)} cleaned papers are required to build the test set.")

    # Spread the preferred papers over the full publication range, then use
    # remaining papers when a preferred one lacks a field needed by its question.
    count = len(papers)
    sampled_indices = [round(i * (count - 1) / (len(QUESTION_TYPES) - 1)) for i in range(len(QUESTION_TYPES))]
    candidate_indices = sampled_indices + [i for i in range(count) if i not in sampled_indices]
    used_ids: set[str] = set()
    test_set: list[dict[str, Any]] = []

    for question_type in QUESTION_TYPES:
        answer_column = {
            "summary": "summary",
            "authors": "authors_joined",
            "date": "published",
            "categories": "categories_joined",
        }[question_type]
        selected = None
        for index in candidate_indices:
            paper = papers[index]
            paper_id = paper["paper_id"]
            title = paper["title"]
            answer = paper[answer_column]
            if (
                isinstance(paper_id, str)
                and paper_id.strip()
                and paper_id not in used_ids
                and isinstance(title, str)
                and title.strip()
                and "'" not in title
                and isinstance(answer, str)
                and answer.strip()
            ):
                selected = paper
                break
        if selected is None:
            raise ValueError(f"Not enough distinct cleaned papers with valid {answer_column} values.")

        paper_id = selected["paper_id"]
        title = selected["title"]
        answer = selected[answer_column]
        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            answer = first_sentence(answer)
        elif question_type == "authors":
            question = f"Who authored '{title}'?"
        elif question_type == "date":
            question = f"When was '{title}' published?"
        else:
            question = f"What categories is '{title}' listed under?"

        test_set.append(
            {
                "id": f"q{len(test_set) + 1:02d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": answer,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        used_ids.add(paper_id)

    write_json(output_path, test_set)
    return test_set
