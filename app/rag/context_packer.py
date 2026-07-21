import re
from dataclasses import dataclass

from app.utils.tokenizer import exact_tokenizer_available, token_count


PROMPT_INJECTION_LINE = re.compile(
    r"(?i)((ignore|override|disregard).{0,40}(instruction|system|developer)|"
    r"(reveal|print|return).{0,30}(secret|token|password|system prompt)|"
    r"(send|upload|share).{0,40}(all files|credentials|tokens))"
)


@dataclass(frozen=True)
class PackingDecision:
    documents: list[dict]
    strategy: str
    estimated_tokens: int
    estimated_value: float


def _document_cost(document: dict) -> int:
    return token_count(str(document.get("content", "")))


def _document_value(document: dict) -> float:
    relevance = float(document.get("ranking_score", document.get("score", 0)) or 0)
    citation = 0.05 if document.get("citation") else 0.0
    recency = float(document.get("recency_bonus", 0) or 0)
    return max(0.0001, relevance + citation + recency)


def select_context_documents(
    documents: list[dict], max_tokens: int, *, strategy: str = "greedy",
    quantum: int = 32, max_candidates: int = 50,
) -> PackingDecision:
    """Select whole evidence items; DP is quantized knapsack, never live RL."""
    candidates = documents[:max_candidates]
    if strategy != "dp" or not candidates or not exact_tokenizer_available():
        selected = []
        used = 0
        value = 0.0
        for item in sorted(candidates, key=_document_value, reverse=True):
            cost = _document_cost(item)
            if used + cost > max_tokens:
                continue
            selected.append(item)
            used += cost
            value += _document_value(item)
        fallback = "greedy_no_exact_tokenizer" if strategy == "dp" else "greedy"
        return PackingDecision(selected, fallback, used, value)
    capacity = max(1, max_tokens // quantum)
    # State maps quantized cost to (value, selected indexes). This sparse form
    # avoids a large multi-dimensional table and remains bounded at 50 candidates.
    states: dict[int, tuple[float, tuple[int, ...]]] = {0: (0.0, ())}
    for index, item in enumerate(candidates):
        cost = max(1, (_document_cost(item) + quantum - 1) // quantum)
        value = _document_value(item)
        updated = dict(states)
        for used, (total_value, indexes) in states.items():
            next_cost = used + cost
            if next_cost > capacity:
                continue
            current = updated.get(next_cost)
            candidate_value = total_value + value
            if current is None or candidate_value > current[0]:
                updated[next_cost] = (candidate_value, (*indexes, index))
        states = updated
    used_units, (value, indexes) = max(
        states.items(), key=lambda item: (item[1][0], -item[0]),
    )
    selected = [candidates[index] for index in indexes]
    return PackingDecision(
        selected, "dp", sum(_document_cost(item) for item in selected), value,
    )


def sanitize_untrusted_content(value: str) -> tuple[str, int]:
    safe = []
    removed = 0
    for line in str(value).replace("<", "‹").replace(">", "›").splitlines():
        if PROMPT_INJECTION_LINE.search(line):
            safe.append("[potential prompt-injection instruction removed]")
            removed += 1
        else:
            safe.append(line)
    return "\n".join(safe), removed


def pack_context(
    documents: list[dict], max_tokens: int = 3000, *, strategy: str = "greedy",
) -> str:
    selection = select_context_documents(documents, max_tokens, strategy=strategy)
    remaining = max_tokens * 4
    chunks = []
    selected = selection.documents or (
        sorted(documents, key=_document_value, reverse=True)[:1] if documents else []
    )
    for doc in selected:
        content, removed = sanitize_untrusted_content(doc.get("content", ""))
        warning = f" [removed_instructions={removed}]" if removed else ""
        chunk = f"[{doc.get('source','unknown')}{warning}] {content}\n"
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
        chunks.append(chunk)
        remaining -= len(chunk)
        if remaining <= 0:
            break
    return "\n".join(chunks)
