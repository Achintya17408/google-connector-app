"""Preflight and compact agent messages before a provider call."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import BaseMessage, ToolMessage

from app.agents.errors import ModelContextLengthFailure
from app.tools.result_projection import estimate_tokens


@dataclass(frozen=True)
class ContextBudgetReport:
    estimated_input_tokens: int
    message_tokens: int
    tool_schema_tokens: int
    context_limit: int
    reserved_completion_tokens: int
    safety_tokens: int
    compaction_count: int

    def as_dict(self) -> dict[str, int]:
        return self.__dict__.copy()


def _message_tokens(messages: list[BaseMessage]) -> int:
    total = 0
    for message in messages:
        total += 8
        total += estimate_tokens(getattr(message, "content", "") or "")
        calls = getattr(message, "tool_calls", None) or []
        if calls:
            total += estimate_tokens(calls)
    return total


def _schema_tokens(tools: list[Any]) -> int:
    schemas = []
    for tool in tools:
        schemas.append({
            "name": tool.name,
            "description": tool.description,
            "arguments": getattr(tool, "args", {}),
        })
    return estimate_tokens(json.dumps(schemas, sort_keys=True, default=str))


def fit_messages_to_budget(
    messages: list[BaseMessage], tools: list[Any], *, context_limit: int,
    reserved_completion_tokens: int, safety_tokens: int,
) -> tuple[list[BaseMessage], ContextBudgetReport]:
    """Compact oldest tool payloads; never alter authority/user intent/tool IDs."""
    fitted = list(messages)
    schema_tokens = _schema_tokens(tools)
    compactions = 0

    def report() -> ContextBudgetReport:
        message_tokens = _message_tokens(fitted)
        return ContextBudgetReport(
            estimated_input_tokens=message_tokens + schema_tokens,
            message_tokens=message_tokens,
            tool_schema_tokens=schema_tokens,
            context_limit=context_limit,
            reserved_completion_tokens=reserved_completion_tokens,
            safety_tokens=safety_tokens,
            compaction_count=compactions,
        )

    current = report()
    allowance = context_limit - reserved_completion_tokens - safety_tokens
    if current.estimated_input_tokens <= allowance:
        return fitted, current

    tool_indexes = [
        index for index, value in enumerate(fitted[:-1])
        if isinstance(value, ToolMessage)
    ]
    for index in tool_indexes:
        value = fitted[index]
        replacement = value.model_copy(update={
            "content": json.dumps({
                "compacted": True,
                "reason": "earlier tool result removed to preserve context budget",
            })
        })
        fitted[index] = replacement
        compactions += 1
        current = report()
        if current.estimated_input_tokens <= allowance:
            return fitted, current

    raise ModelContextLengthFailure(
        "The executor stopped before the model call because the bounded request still "
        "exceeded the configured context budget.",
        boundary="context_preflight",
        evidence=current.as_dict(),
    )
