"""Offline, no-network structural comparison of source-aware chunking policies."""

import math
import re
import time

from app.rag.chunking import ChunkingPolicy, chunks_for_source, token_count
from app.rag.evaluation import retrieval_metrics


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def _lexical_rank(query: str, chunks: list) -> list[int]:
    query_terms = _terms(query)
    scored = []
    for chunk in chunks:
        terms = _terms(chunk.content)
        score = len(query_terms & terms) / math.sqrt(max(1, len(terms)))
        scored.append((score, -chunk.index, chunk.index))
    return [index for score, _, index in sorted(scored, reverse=True) if score > 0]


def _materialize_item(case: dict) -> dict:
    """Expand compact deterministic fixture sections without storing huge test files."""
    item = dict(case["item"])
    generated = item.pop("generated_sections", None)
    if generated:
        item["content"] = "\n".join(
            f"# {section['heading']}\n" + " ".join(
                [section["sentence"]] * int(section["repeat"])
            )
            for section in generated
        )
    return item


def evaluate_chunk_policy(cases: list[dict], policy: ChunkingPolicy, k: int = 3) -> dict:
    started = time.perf_counter()
    retrieval_rows = []
    chunk_counts = []
    token_sizes = []
    duplicate_ratios = []
    lineage_failures = 0
    evidence_failures = 0
    case_results = []
    for case in cases:
        chunks = chunks_for_source(case["source_type"], _materialize_item(case), policy)
        chunk_counts.append(len(chunks))
        token_sizes.extend(token_count(chunk.content) for chunk in chunks)
        normalized = [" ".join(chunk.content.casefold().split()) for chunk in chunks]
        duplicate_ratios.append(
            1 - len(set(normalized)) / len(normalized) if normalized else 0.0
        )
        if any(chunk.index != index for index, chunk in enumerate(chunks)):
            lineage_failures += 1
        for query in case["queries"]:
            relevant = {
                str(chunk.index) for chunk in chunks
                if all(term.casefold() in chunk.content.casefold()
                       for term in query["required_terms"])
            }
            if not relevant:
                evidence_failures += 1
            ranked = [str(index) for index in _lexical_rank(query["query"], chunks)]
            metrics = retrieval_metrics(ranked, relevant, k)
            retrieval_rows.append(metrics)
            case_results.append({
                "case": case["id"], "query": query["query"],
                "relevant_chunks": len(relevant), **metrics,
            })
    aggregate = {
        key: round(sum(row[key] for row in retrieval_rows) / len(retrieval_rows), 6)
        for key in retrieval_rows[0]
    } if retrieval_rows else {}
    return {
        "policy": policy.name,
        "target_tokens": policy.target_tokens,
        "overlap_tokens": policy.overlap_tokens,
        "cases": len(cases),
        "queries": len(retrieval_rows),
        "chunk_count": sum(chunk_counts),
        "mean_chunks_per_source": round(sum(chunk_counts) / len(chunk_counts), 3),
        "mean_chunk_tokens": round(sum(token_sizes) / len(token_sizes), 3) if token_sizes else 0,
        "max_chunk_tokens": max(token_sizes, default=0),
        "duplicate_context_ratio": round(
            sum(duplicate_ratios) / len(duplicate_ratios), 6
        ) if duplicate_ratios else 0,
        "lineage_failures": lineage_failures,
        "evidence_failures": evidence_failures,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "retrieval": aggregate,
        "case_results": case_results,
    }
