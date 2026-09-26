"""Smoke test cho retrieval layer (rubric muc 4 & 5).

1. Build ChromaDB collection `papers-baseline` tu data/clean/papers_clean.json, kiem tra du so document.
2. Semantic search: moi paper, query bang title -> paper do co nam trong top-k khong.
3. Extractive QA (`answer_question`) cho 4 loai cau hoi: summary / authors / date / categories.
4. Agent (`build_agent`) tren tung LLM provider: mock + provider trong .env.

Chay: .venv\\Scripts\\python script/smoke_retrieval.py [--providers mock,gemini]
Ket qua: data/results/smoke_retrieval.json
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import time

import pandas as pd

from core.config import load_settings, normalized_provider
from core.utils import first_sentence, now_utc, write_json
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question

QA_TEMPLATES = {
    "summary": ("What is the main contribution of '{title}'?", lambda row: first_sentence(row["summary"])),
    "authors": ("Who authored '{title}'?", lambda row: row["authors_joined"]),
    "date": ("When was '{title}' published?", lambda row: row["published"]),
    "categories": ("What categories does '{title}' belong to?", lambda row: row["categories_joined"]),
}


def check_index(df: pd.DataFrame, settings) -> tuple[LocalEmbeddingIndex, dict]:
    started = time.perf_counter()
    index = LocalEmbeddingIndex.build(df, settings)
    count = index.collection.count()
    sample = index.collection.get(limit=1, include=["metadatas"])["metadatas"][0]
    result = {
        "collection": index.collection_name,
        "embedding_model": settings.embedding_model,
        "expected_docs": len(df),
        "indexed_docs": count,
        "metadata_keys": sorted(sample),
        "build_seconds": round(time.perf_counter() - started, 1),
        "passed": count == len(df),
    }
    return index, result


def check_semantic_search(df: pd.DataFrame, index: LocalEmbeddingIndex, top_k: int) -> dict:
    ranks = []
    for row in df.to_dict(orient="records"):
        ids = [r.paper_id for r in index.search(row["title"], top_k=top_k)]
        ranks.append(ids.index(row["paper_id"]) + 1 if row["paper_id"] in ids else None)
    hits = [r for r in ranks if r]
    return {
        "queries": len(ranks),
        f"hit_rate@{top_k}": round(len(hits) / len(ranks), 4),
        "top1_rate": round(sum(r == 1 for r in hits) / len(ranks), 4),
        "misses": [pid for pid, r in zip(df["paper_id"], ranks) if r is None],
    }


def check_qa(df: pd.DataFrame, index: LocalEmbeddingIndex, settings) -> dict:
    cases = []
    for (qtype, (template, expected_fn)), row in zip(QA_TEMPLATES.items(), df.to_dict(orient="records")):
        question = template.format(title=row["title"])
        result = answer_question(question, settings=settings, index=index)
        cases.append(
            {
                "question_type": qtype,
                "question": question,
                "expected": expected_fn(row),
                "answer": result.answer,
                "correct": result.answer == expected_fn(row),
                "retrieval_hit": row["paper_id"] in result.retrieved_doc_ids,
                "retrieved_doc_ids": result.retrieved_doc_ids,
            }
        )
    return {"passed": all(c["correct"] and c["retrieval_hit"] for c in cases), "cases": cases}


def check_agents(df: pd.DataFrame, index: LocalEmbeddingIndex, settings, providers: list[str]) -> list[dict]:
    row = df.iloc[0]
    question = f"Who authored the paper titled '{row['title']}'? Answer with the author names only."
    results = []
    for provider in providers:
        provider_settings = replace(settings, llm_provider=provider)
        started = time.perf_counter()
        try:
            answer = run_agent_question(build_agent(provider_settings, index), question)
            answer = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)
            status = "ok"
        except Exception as error:  # ghi lai loi de biet provider nao chua dung duoc
            answer, status = f"{type(error).__name__}: {error}"[:300], "error"
        results.append(
            {
                "provider": normalized_provider(provider_settings),
                "model": provider_settings.model_name if provider != "mock" else "FakeListChatModel",
                "status": status,
                "question": question,
                "expected_authors": row["authors_joined"],
                "answer": answer,
                "mentions_all_authors": status == "ok" and all(a in answer for a in row["authors"]),
                "seconds": round(time.perf_counter() - started, 1),
            }
        )
    return results


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--providers", default=f"mock,{settings.llm_provider}", help="comma-separated LLM providers")
    args = parser.parse_args()
    providers = list(dict.fromkeys(p.strip() for p in args.providers.split(",") if p.strip()))

    df = pd.read_json(settings.paths.clean_json)
    index, index_result = check_index(df, settings)
    print(f"[index] {index_result['collection']}: {index_result['indexed_docs']}/{index_result['expected_docs']} docs")

    search_result = check_semantic_search(df, index, settings.top_k)
    print(f"[search] title -> paper hit_rate@{settings.top_k}={search_result[f'hit_rate@{settings.top_k}']}, "
          f"top1={search_result['top1_rate']}")

    qa_result = check_qa(df, index, settings)
    for case in qa_result["cases"]:
        print(f"[qa:{case['question_type']}] correct={case['correct']} hit={case['retrieval_hit']} -> {case['answer'][:70]}")

    agent_results = check_agents(df, index, settings, providers)
    for item in agent_results:
        print(f"[agent:{item['provider']}] {item['status']} ({item['seconds']}s) -> {item['answer'][:100]}")

    report = {
        "run_at": now_utc().isoformat(timespec="seconds"),
        "index": index_result,
        "semantic_search": search_result,
        "extractive_qa": qa_result,
        "agents": agent_results,
    }
    output = settings.paths.project_dir / "data" / "results" / "smoke_retrieval.json"
    write_json(output, report)
    print(f"Saved {output.relative_to(settings.paths.project_dir)}")


if __name__ == "__main__":
    main()
