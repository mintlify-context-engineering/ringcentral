"""
measure_context.py

Measures the actual bytes of tool-result context consumed per question
for both the raw monorepo agent and the Mintlify MCP agent.

Tool-result context = the content returned by file reads, grep, and MCP
search calls that get fed back into the model as input. This is the primary
driver of input token cost differences between the two conditions.

No LLM judge — just measures context size. Run with:
    python measure_context.py              # all 20 questions
    python measure_context.py --ids T1-01 T2-06 T3-02
    python measure_context.py --tier 1
"""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
MONOREPO_ROOT = str(Path(__file__).parent.parent)
MCP_URL = os.environ.get("MINTLIFY_MCP_URL", "https://ringcentral.mintlify.app/mcp")
API_KEY = os.environ.get("CURSOR_API_KEY", "")

RAW_PREFIX = (
    "You are navigating the RingCentral open-source monorepo to answer a developer question. "
    "The monorepo contains 40+ sub-repositories across docs/, sdks/, chatbots/, embeddable/, "
    "integrations/, crm/, video/, and voice/ directories. "
    "Use the files available to you to answer accurately and concisely.\n\nQuestion: "
)

MINTLIFY_PREFIX = (
    "You are using the RingCentral documentation portal (powered by Mintlify). "
    "Use the search tools available to find documentation and answer the following question "
    "accurately. Include specific package names, install commands, and exact values (URLs, "
    "error codes, header names) when they are relevant to the answer.\n\nQuestion: "
)


def collect_tool_result_bytes(run) -> dict:
    """
    Walk run.conversation() and sum the byte size of every tool result.
    Returns a breakdown by tool type.
    """
    from cursor_sdk import ToolCallConversationStep

    tool_bytes = {}
    tool_calls = []

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


def run_raw(question: str) -> dict:
    from cursor_sdk import Agent, LocalAgentOptions

    t0 = time.time()
    try:
        with Agent.create(
            model="composer-2.5",
            api_key=API_KEY,
            local=LocalAgentOptions(cwd=MONOREPO_ROOT),
        ) as agent:
            run = agent.send(RAW_PREFIX + question)
            answer = run.text()
            tool_data = collect_tool_result_bytes(run)
    except Exception as e:
        answer = f"ERROR: {e}"
        tool_data = {"total": 0, "by_type": {}, "calls": []}

    return {
        "answer": answer.strip(),
        "elapsed_s": round(time.time() - t0, 2),
        "tool_result_bytes": tool_data["total"],
        "tool_breakdown": tool_data["by_type"],
        "tool_calls": len(tool_data["calls"]),
    }


def run_mintlify(question: str) -> dict:
    from cursor_sdk import Agent, AgentOptions, HttpMcpServerConfig, LocalAgentOptions

    t0 = time.time()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            with Agent.create(
                AgentOptions(
                    model="composer-2.5",
                    api_key=API_KEY,
                    local=LocalAgentOptions(cwd=tmpdir, setting_sources=[]),
                    mcp_servers={"ringcentral-docs": HttpMcpServerConfig(url=MCP_URL)},
                )
            ) as agent:
                run = agent.send(MINTLIFY_PREFIX + question)
                answer = run.text()
                tool_data = collect_tool_result_bytes(run)
    except Exception as e:
        answer = f"ERROR: {e}"
        tool_data = {"total": 0, "by_type": {}, "calls": []}

    return {
        "answer": answer.strip(),
        "elapsed_s": round(time.time() - t0, 2),
        "tool_result_bytes": tool_data["total"],
        "tool_breakdown": tool_data["by_type"],
        "tool_calls": len(tool_data["calls"]),
    }


def load_questions(ids=None, tier=None):
    with open(QUESTIONS_FILE) as f:
        data = json.load(f)
    qs = data["questions"]
    if ids:
        qs = [q for q in qs if q["id"] in ids]
    elif tier:
        qs = [q for q in qs if q["tier"] == tier]
    return qs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--tier", type=int)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    questions = load_questions(ids=args.ids, tier=args.tier)

    print(f"\n{'='*65}")
    print("Tool-Result Context Measurement: Raw Monorepo vs Mintlify MCP")
    print(f"Questions: {len(questions)}")
    print(f"{'='*65}\n")

    results = []
    total_raw = 0
    total_mint = 0

    for i, q in enumerate(questions, 1):
        qtext = q["question"][:60] + "..." if len(q["question"]) > 60 else q["question"]
        print(f"[{i}/{len(questions)}] {q['id']} — {qtext}")

        raw = run_raw(q["question"])
        mint = run_mintlify(q["question"])

        total_raw += raw["tool_result_bytes"]
        total_mint += mint["tool_result_bytes"]

        reduction = 0
        if raw["tool_result_bytes"] > 0:
            reduction = (1 - mint["tool_result_bytes"] / raw["tool_result_bytes"]) * 100

        print(f"  Raw:      {raw['tool_result_bytes']:>8,} bytes  ({raw['tool_calls']} tool calls)  {raw['elapsed_s']:.1f}s")
        print(f"  Mintlify: {mint['tool_result_bytes']:>8,} bytes  ({mint['tool_calls']} tool calls)  {mint['elapsed_s']:.1f}s")
        print(f"  Reduction: {reduction:+.0f}%")

        if args.verbose:
            print(f"  Raw breakdown:      {raw['tool_breakdown']}")
            print(f"  Mintlify breakdown: {mint['tool_breakdown']}")

        results.append({
            "id": q["id"],
            "tier": q["tier"],
            "raw_bytes": raw["tool_result_bytes"],
            "mint_bytes": mint["tool_result_bytes"],
            "raw_calls": raw["tool_calls"],
            "mint_calls": mint["tool_calls"],
            "reduction_pct": round(reduction, 1),
        })
        print()

    # Summary
    avg_reduction = (1 - total_mint / total_raw) * 100 if total_raw > 0 else 0
    avg_raw = total_raw // len(results) if results else 0
    avg_mint = total_mint // len(results) if results else 0

    print(f"\n{'='*65}")
    print("SUMMARY — Tool-Result Context Bytes")
    print(f"{'='*65}")
    print(f"{'Metric':<40} {'Raw':>10} {'Mintlify':>12}")
    print(f"{'-'*65}")
    print(f"{'Total bytes (all questions)':<40} {total_raw:>10,} {total_mint:>12,}")
    print(f"{'Avg bytes per question':<40} {avg_raw:>10,} {avg_mint:>12,}")
    print(f"{'Context reduction':<40} {'':>10} {avg_reduction:>11.1f}%")
    print()
    print("Context bytes = bytes of tool results (file reads, search results)")
    print("fed back to the model as input. Primary driver of input token cost.")

    # Save
    out_path = Path(__file__).parent / "results" / "context_measurement.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "questions": len(results),
            "total_raw_bytes": total_raw,
            "total_mint_bytes": total_mint,
            "avg_raw_bytes": avg_raw,
            "avg_mint_bytes": avg_mint,
            "context_reduction_pct": round(avg_reduction, 1),
            "per_question": results,
        }, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
