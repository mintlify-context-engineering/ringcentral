"""
measure_context.py

Measures the actual bytes of tool-result context consumed per question for:
  1. Raw source with Markdown files
  2. Raw source with the Markdown layer removed
  3. Mintlify MCP

Tool-result context = the content returned by file reads, grep, and MCP
search calls that get fed back into the model as input. This is the primary
driver of input token cost differences between the conditions.

No LLM judge — just measures context size. Run with:
    python measure_context.py              # all questions
    python measure_context.py --ids T1-01 T2-06 T3-02
    python measure_context.py --tier 1
"""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
REPO_ROOT = Path(__file__).parent.parent
MCP_URL = os.environ.get("MINTLIFY_MCP_URL", "https://ringcentral.mintlify.app/mcp")
API_KEY = os.environ.get("CURSOR_API_KEY", "")

RAW_SOURCE_ENTRIES = (
    "docs",
    "sdks",
    "chatbots",
    "embeddable",
    "integrations",
    "crm",
    "video",
    "voice",
    "infrastructure",
    "README.md",
)

NO_MARKDOWN_SOURCE_ENTRIES = (
    "sdks",
    "chatbots",
    "embeddable",
    "integrations",
    "crm",
    "video",
    "voice",
    "infrastructure",
)

MARKDOWN_SUFFIXES = {".md", ".mdx", ".markdown"}
SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "benchmark",
    "results",
    "build",
    "coverage",
    "dist",
    ".next",
    "storybook-static",
}

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

NO_MARKDOWN_PREFIX = (
    "You are navigating the RingCentral open-source monorepo to answer a developer question. "
    "The Markdown documentation layer has been removed: docs/ is unavailable, and README.md, "
    "*.md, *.mdx, and other Markdown files are absent. You still have access to source code, "
    "examples, package metadata, configs, tests, and inline code comments. Use the files "
    "available to you to answer accurately and concisely.\n\nQuestion: "
)


def _is_markdown_file(path: Path) -> bool:
    return path.suffix.lower() in MARKDOWN_SUFFIXES


def populate_raw_workspace(workspace: Path) -> None:
    for entry in RAW_SOURCE_ENTRIES:
        source_root = REPO_ROOT / entry
        if not source_root.exists():
            continue
        if source_root.is_file():
            os.symlink(source_root, workspace / entry)
            continue

        dest_root = workspace / entry
        dest_root.mkdir(parents=True, exist_ok=True)
        for current_root, dirs, files in os.walk(source_root):
            current = Path(current_root)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            rel_dir = current.relative_to(source_root)
            dest_dir = dest_root / rel_dir
            dest_dir.mkdir(parents=True, exist_ok=True)
            for filename in files:
                os.symlink(current / filename, dest_dir / filename)


def populate_no_markdown_workspace(workspace: Path) -> None:
    for entry in NO_MARKDOWN_SOURCE_ENTRIES:
        source_root = REPO_ROOT / entry
        if not source_root.exists():
            continue
        if source_root.is_file():
            if not _is_markdown_file(source_root):
                os.symlink(source_root, workspace / entry)
            continue

        dest_root = workspace / entry
        dest_root.mkdir(parents=True, exist_ok=True)
        for current_root, dirs, files in os.walk(source_root):
            current = Path(current_root)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            rel_dir = current.relative_to(source_root)
            dest_dir = dest_root / rel_dir
            dest_dir.mkdir(parents=True, exist_ok=True)
            for filename in files:
                source_file = current / filename
                if _is_markdown_file(source_file):
                    continue
                os.symlink(source_file, dest_dir / filename)


# Single source of truth for tool-result byte measurement — shared with the
# regular benchmark (run_experiment.py) so both report identical numbers.
from agents.context_metrics import collect_tool_result_bytes


def run_raw(question: str) -> dict:
    from cursor_sdk import Agent, LocalAgentOptions

    t0 = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="rc-context-raw-") as tmpdir:
            workspace = Path(tmpdir)
            populate_raw_workspace(workspace)
            with Agent.create(
                model="composer-2.5",
                api_key=API_KEY,
                local=LocalAgentOptions(cwd=str(workspace), setting_sources=[]),
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


def run_no_markdown(question: str) -> dict:
    from cursor_sdk import Agent, LocalAgentOptions

    t0 = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="rc-context-no-markdown-") as tmpdir:
            workspace = Path(tmpdir)
            populate_no_markdown_workspace(workspace)
            with Agent.create(
                model="composer-2.5",
                api_key=API_KEY,
                local=LocalAgentOptions(cwd=str(workspace), setting_sources=[]),
            ) as agent:
                run = agent.send(NO_MARKDOWN_PREFIX + question)
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
    print("Tool-Result Context Measurement: Markdown vs No Markdown vs Mintlify MCP")
    print(f"Questions: {len(questions)}")
    print(f"{'='*65}\n")

    results = []
    total_raw = 0
    total_no_markdown = 0
    total_mint = 0

    for i, q in enumerate(questions, 1):
        qtext = q["question"][:60] + "..." if len(q["question"]) > 60 else q["question"]
        print(f"[{i}/{len(questions)}] {q['id']} — {qtext}")

        raw = run_raw(q["question"])
        no_markdown = run_no_markdown(q["question"])
        mint = run_mintlify(q["question"])

        total_raw += raw["tool_result_bytes"]
        total_no_markdown += no_markdown["tool_result_bytes"]
        total_mint += mint["tool_result_bytes"]

        no_markdown_delta = 0
        mint_reduction = 0
        if raw["tool_result_bytes"] > 0:
            no_markdown_delta = (1 - no_markdown["tool_result_bytes"] / raw["tool_result_bytes"]) * 100
            mint_reduction = (1 - mint["tool_result_bytes"] / raw["tool_result_bytes"]) * 100

        print(f"  Raw + Markdown:     {raw['tool_result_bytes']:>8,} bytes  ({raw['tool_calls']} tool calls)  {raw['elapsed_s']:.1f}s")
        print(f"  No Markdown:        {no_markdown['tool_result_bytes']:>8,} bytes  ({no_markdown['tool_calls']} tool calls)  {no_markdown['elapsed_s']:.1f}s")
        print(f"  Mintlify MCP:       {mint['tool_result_bytes']:>8,} bytes  ({mint['tool_calls']} tool calls)  {mint['elapsed_s']:.1f}s")
        print(f"  Delta vs Markdown:  no-Markdown {no_markdown_delta:+.0f}%  |  Mintlify {mint_reduction:+.0f}%")

        if args.verbose:
            print(f"  Raw breakdown:         {raw['tool_breakdown']}")
            print(f"  No-Markdown breakdown: {no_markdown['tool_breakdown']}")
            print(f"  Mintlify breakdown:    {mint['tool_breakdown']}")

        results.append({
            "id": q["id"],
            "tier": q["tier"],
            "raw_bytes": raw["tool_result_bytes"],
            "no_markdown_bytes": no_markdown["tool_result_bytes"],
            "mint_bytes": mint["tool_result_bytes"],
            "raw_calls": raw["tool_calls"],
            "no_markdown_calls": no_markdown["tool_calls"],
            "mint_calls": mint["tool_calls"],
            "no_markdown_delta_pct": round(no_markdown_delta, 1),
            "mint_reduction_pct": round(mint_reduction, 1),
        })
        print()

    # Summary
    avg_no_markdown_delta = (1 - total_no_markdown / total_raw) * 100 if total_raw > 0 else 0
    avg_mint_reduction = (1 - total_mint / total_raw) * 100 if total_raw > 0 else 0
    avg_raw = total_raw // len(results) if results else 0
    avg_no_markdown = total_no_markdown // len(results) if results else 0
    avg_mint = total_mint // len(results) if results else 0

    print(f"\n{'='*65}")
    print("SUMMARY — Tool-Result Context Bytes")
    print(f"{'='*65}")
    print(f"{'Metric':<34} {'Markdown':>12} {'No Markdown':>14} {'Mintlify':>12}")
    print(f"{'-'*78}")
    print(f"{'Total bytes (all questions)':<34} {total_raw:>12,} {total_no_markdown:>14,} {total_mint:>12,}")
    print(f"{'Avg bytes per question':<34} {avg_raw:>12,} {avg_no_markdown:>14,} {avg_mint:>12,}")
    print(f"{'Delta vs Markdown':<34} {'':>12} {avg_no_markdown_delta:>13.1f}% {avg_mint_reduction:>11.1f}%")
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
            "total_no_markdown_bytes": total_no_markdown,
            "total_mint_bytes": total_mint,
            "avg_raw_bytes": avg_raw,
            "avg_no_markdown_bytes": avg_no_markdown,
            "avg_mint_bytes": avg_mint,
            "no_markdown_delta_pct": round(avg_no_markdown_delta, 1),
            "mint_context_reduction_pct": round(avg_mint_reduction, 1),
            "per_question": results,
        }, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
