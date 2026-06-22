"""
Shared context / token measurement helpers.

Token spend is dominated by the bytes of tool results (file reads, grep, MCP
search results) that get fed back into the model as input. The Cursor SDK does
not expose a usage/token object on its run result, so we measure those bytes
directly off the run's conversation and convert to an estimated token count.

This is the single source of truth for both the regular benchmark
(run_experiment.py) and the standalone context audit (measure_context.py).
"""

import json

# Rough chars-per-token ratio for English + code. Used only for human-readable
# token *estimates* — the underlying measurement is exact bytes.
CHARS_PER_TOKEN = 4


def estimate_tokens(n_chars: int) -> int:
    """Estimate model tokens from a character/byte count (~4 chars/token)."""
    return round(n_chars / CHARS_PER_TOKEN)


def collect_tool_result_bytes(run) -> dict:
    """Walk run.conversation() and sum the byte size of every tool result.

    Must be called while the agent connection is still open (i.e. inside the
    `with Agent.create(...)` block). Returns:
        {"total": int, "by_type": {tool_type: bytes}, "calls": [{type, bytes}]}
    """
    from cursor_sdk import ToolCallConversationStep

    tool_bytes: dict[str, int] = {}
    tool_calls: list[dict] = []

    try:
        conv = run.conversation()
    except Exception:
        return {"total": 0, "by_type": {}, "calls": []}

    for turn in conv:
        t = turn.turn
        if not hasattr(t, "steps"):
            continue
        for step in t.steps:
            if not isinstance(step, ToolCallConversationStep):
                continue
            msg = step.message
            tool_type = msg.get("type", "unknown")
            result = msg.get("result", {})
            result_bytes = len(json.dumps(result, default=str))
            tool_bytes[tool_type] = tool_bytes.get(tool_type, 0) + result_bytes
            tool_calls.append({"type": tool_type, "bytes": result_bytes})

    return {
        "total": sum(tool_bytes.values()),
        "by_type": tool_bytes,
        "calls": tool_calls,
    }


def metrics_from_run(run, answer: str) -> dict:
    """Build the standard per-agent context/token metric block.

    `answer` is the agent's final text (output side). Tool-result bytes are the
    input-context side. Both are reported as exact counts plus token estimates.
    """
    tool_data = collect_tool_result_bytes(run)
    context_bytes = tool_data["total"]
    output_chars = len(answer)
    context_tokens = estimate_tokens(context_bytes)
    output_tokens = estimate_tokens(output_chars)
    return {
        "tool_result_bytes": context_bytes,
        "tool_calls": len(tool_data["calls"]),
        "tool_breakdown": tool_data["by_type"],
        "context_tokens_est": context_tokens,
        "output_tokens_est": output_tokens,
        "total_tokens_est": context_tokens + output_tokens,
    }


def empty_metrics() -> dict:
    """Zeroed metric block for error / dry-run paths."""
    return {
        "tool_result_bytes": 0,
        "tool_calls": 0,
        "tool_breakdown": {},
        "context_tokens_est": 0,
        "output_tokens_est": 0,
        "total_tokens_est": 0,
    }
