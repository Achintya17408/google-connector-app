"""Lazy tokenizer access with a conservative, no-network-safe fallback."""

from functools import lru_cache


@lru_cache(maxsize=1)
def exact_tokenizer():
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Import-time network/cache failures must never take down API or workers.
        return None


def exact_tokenizer_available() -> bool:
    return exact_tokenizer() is not None


def token_count(text: str) -> int:
    value = str(text)
    tokenizer = exact_tokenizer()
    if tokenizer is not None:
        return len(tokenizer.encode(value))
    # UTF-8 bytes are a conservative upper bound for supported BPE token counts.
    return max(1, len(value.encode("utf-8")))


def truncate_tokens(text: str, max_tokens: int) -> str:
    value = str(text)
    tokenizer = exact_tokenizer()
    if tokenizer is not None:
        return tokenizer.decode(tokenizer.encode(value)[:max_tokens])
    return value.encode("utf-8")[:max_tokens].decode("utf-8", errors="ignore")


def token_windows(text: str, size: int, overlap: int) -> list[str]:
    value = " ".join(str(text).split())
    if not value:
        return []
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Token window requires size>0 and 0<=overlap<size")
    tokenizer = exact_tokenizer()
    if tokenizer is None:
        # Conservative byte windows preserve availability but are not eligible as
        # exact-tokenizer experimental evidence.
        raw = value.encode("utf-8")
        output = []
        start = 0
        while start < len(raw):
            end = min(len(raw), start + size)
            output.append(raw[start:end].decode("utf-8", errors="ignore").strip())
            if end >= len(raw):
                break
            start = end - overlap
        return [item for item in output if item]
    tokens = tokenizer.encode(value)
    output = []
    start = 0
    while start < len(tokens):
        end = min(len(tokens), start + size)
        output.append(tokenizer.decode(tokens[start:end]).strip())
        if end >= len(tokens):
            break
        start = end - overlap
    return output
