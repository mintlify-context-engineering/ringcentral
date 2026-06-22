"""
autoresearch_loop.py — Karpathy-style optimization of doc structure.

Inspired by github.com/karpathy/autoresearch:
  - Fixed evaluation metric (composite_score)
  - Iterative experiments: modify doc config → run benchmark → keep if better
  - Runs autonomously, logs all variants and scores

The variable we optimize: how much context each search result returns.
Configs tested:
  - chunk_size: how many chars of doc content to return per search result
  - include_examples: whether to include code examples in search results
  - max_results: how many search results to show per query

Composite score (higher = better):
  score = accuracy * efficiency
  where efficiency = baseline_avg_tokens / condition_avg_tokens

Usage:
    python autoresearch_loop.py
    python autoresearch_loop.py --questions T1-01 T1-02 T2-01 T2-04 T3-01
    python autoresearch_loop.py --rounds 5
"""

import argparse
import json
import re
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent))
import judge as judge_module
from agents.mintlify_agent import TOOLS, TOOL_FUNCTIONS as BASE_TOOL_FUNCTIONS, SYSTEM_PROMPT, MAX_TOOL_CALLS, DOCS_ROOT

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
RESULTS_DIR = Path(__file__).parent / "results"

# Questions to use for the autoresearch loop (a representative subset)
DEFAULT_QUESTION_IDS = ["T1-02", "T1-06", "T2-01", "T2-02", "T2-04", "T3-01", "T3-04"]

# Configs to evaluate (each is one "experiment")
CONFIGS = [
    {
        "name": "minimal",
        "description": "Small chunks, no code examples in search results",
        "chunk_size": 800,
        "include_examples": False,
        "max_search_results": 2,
    },
    {
        "name": "standard",
        "description": "Medium chunks with examples — baseline Mintlify config",
        "chunk_size": 2000,
        "include_examples": True,
        "max_search_results": 3,
    },
    {
        "name": "full",
        "description": "Full doc content, max results",
        "chunk_size": 99999,
        "include_examples": True,
        "max_search_results": 5,
    },
    {
        "name": "summary-first",
        "description": "Summary only in search, no auto-read",
        "chunk_size": 400,
        "include_examples": False,
        "max_search_results": 5,
    },
]


def _strip_code_examples(content: str) -> str:
    """Remove fenced code blocks from markdown content."""
    return re.sub(r"```.*?```", "[code example omitted]", content, flags=re.DOTALL)


def make_search_fn(chunk_size: int, include_examples: bool, max_results: int):
    """Create a search_docs function with the given config."""
    from agents.mintlify_agent import _load_index, _score_doc

    def search_docs(query: str, max_results: int = max_results) -> str:
        docs = _load_index()
        scored = [(doc, _score_doc(doc, query)) for doc in docs]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, score in scored[:max_results]:
            file_path = DOCS_ROOT / doc["file"]
            content = file_path.read_text() if file_path.exists() else ""

            if not include_examples:
                content = _strip_code_examples(content)

            if len(content) > chunk_size:
                content = content[:chunk_size] + "\n\n[... content truncated — use read_doc for full content ...]"

            results.append(
                f"**{doc['title']}** (doc_id: {doc['id']}, relevance: {score:.0f})\n\n"
                f"{content}"
            )

        if not results:
            for doc in docs[:max_results]:
                results.append(f"**{doc['title']}** (doc_id: {doc['id']})\n{doc['summary']}")

        return "\n\n---\n\n".join(results)

    return search_docs


def run_mintlify_with_config(question: str, config: dict, model: str, client: anthropic.Anthropic) -> dict:
    """Run the Mintlify agent with a specific doc structure config."""
    from agents.mintlify_agent import TOOLS as BASE_TOOLS

    search_fn = make_search_fn(
        chunk_size=config["chunk_size"],
        include_examples=config["include_examples"],
        max_results=config["max_search_results"],
    )

    tool_functions = {
        "search_docs": search_fn,
        "read_doc": BASE_TOOL_FUNCTIONS["read_doc"],
    }

    messages = [{"role": "user", "content": question}]
    total_input = 0
    total_output = 0
    tool_call_count = 0

    for _ in range(MAX_TOOL_CALLS + 1):
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=BASE_TOOLS,
            messages=messages,
        )

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            answer = "".join(b.text for b in response.content if hasattr(b, "text"))
            return {
                "answer": answer.strip(),
                "input_tokens": total_input,
                "output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "tool_calls": tool_call_count,
            }

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_call_count += 1
            fn = tool_functions.get(block.name)
            result = fn(**block.input) if fn else f"Unknown tool: {block.name}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

        if tool_call_count >= MAX_TOOL_CALLS:
            messages.append({"role": "user", "content": "Please provide your final answer now."})
            final = client.messages.create(model=model, max_tokens=800, system=SYSTEM_PROMPT, messages=messages)
            total_input += final.usage.input_tokens
            total_output += final.usage.output_tokens
            answer = "".join(b.text for b in final.content if hasattr(b, "text"))
            return {
                "answer": answer.strip(),
                "input_tokens": total_input,
                "output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "tool_calls": tool_call_count,
                "hit_limit": True,
            }

    return {"answer": "", "input_tokens": total_input, "output_tokens": total_output, "total_tokens": total_input + total_output, "tool_calls": tool_call_count}


def evaluate_config(config: dict, questions: list[dict], model: str, client: anthropic.Anthropic) -> dict:
    """Run all questions with a config and return aggregate metrics."""
    question_results = []

    for q in questions:
        result = run_mintlify_with_config(q["question"], config, model, client)
        # Simple judge call
        scores = judge_module.score(
            question=q["question"],
            ground_truth=q["ground_truth"],
            key_facts=q["key_facts"],
            answer_raw="",  # Not comparing to raw here
            answer_mintlify=result["answer"],
            client=client,
        )
        question_results.append({
            "id": q["id"],
            "total_tokens": result["total_tokens"],
            "tool_calls": result["tool_calls"],
            "mintlify_score": scores["mintlify_score"],
        })

    avg_tokens = sum(r["total_tokens"] for r in question_results) / len(question_results)
    avg_score = sum(r["mintlify_score"] for r in question_results) / len(question_results)
    avg_tools = sum(r["tool_calls"] for r in question_results) / len(question_results)

    # Composite: accuracy (0-1 range) * efficiency factor
    # We normalize score to 0-1 (max score is 2) and reward token efficiency
    accuracy = avg_score / 2.0
    # Efficiency: 1.0 at 1000 tokens, decreasing as tokens grow (log scale)
    import math
    efficiency = 1000 / (avg_tokens + 500)  # Reward lower token usage
    composite = accuracy * (1 + efficiency)  # accuracy weighted, bonus for efficiency

    return {
        "config_name": config["name"],
        "config": config,
        "avg_tokens": round(avg_tokens, 1),
        "avg_score": round(avg_score, 2),
        "avg_tool_calls": round(avg_tools, 1),
        "composite_score": round(composite, 4),
        "question_results": question_results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", nargs="+", default=DEFAULT_QUESTION_IDS)
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--rounds", type=int, default=1, help="How many times to cycle through configs")
    args = parser.parse_args()

    if not __import__("os").environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    with open(QUESTIONS_FILE) as f:
        all_q = json.load(f)["questions"]
    questions = [q for q in all_q if q["id"] in args.questions]

    if not questions:
        print(f"No questions matched: {args.questions}")
        sys.exit(1)

    client = anthropic.Anthropic()
    print(f"\nautoresearch_loop — optimizing doc structure config")
    print(f"Questions: {[q['id'] for q in questions]}")
    print(f"Configs to evaluate: {[c['name'] for c in CONFIGS]}")
    print(f"Model: {args.model}\n")

    all_runs = []
    best_config = None
    best_score = -1

    for round_num in range(1, args.rounds + 1):
        print(f"{'='*50}")
        print(f"Round {round_num}/{args.rounds}")
        print(f"{'='*50}")

        for config in CONFIGS:
            print(f"\nEvaluating config: {config['name']} — {config['description']}")
            t0 = time.time()
            result = evaluate_config(config, questions, args.model, client)
            elapsed = time.time() - t0

            print(f"  avg_tokens={result['avg_tokens']:.0f}, avg_score={result['avg_score']:.2f}/2, "
                  f"avg_tools={result['avg_tool_calls']:.1f}, composite={result['composite_score']:.4f} ({elapsed:.1f}s)")

            all_runs.append(result)

            if result["composite_score"] > best_score:
                best_score = result["composite_score"]
                best_config = config
                print(f"  *** New best config! ***")

    # Final report
    print(f"\n{'='*50}")
    print(f"AUTORESEARCH RESULTS")
    print(f"{'='*50}")
    print(f"\nConfig rankings (by composite score):")
    sorted_runs = sorted(all_runs, key=lambda x: x["composite_score"], reverse=True)
    for i, r in enumerate(sorted_runs, 1):
        marker = " <-- WINNER" if r["config_name"] == best_config["name"] else ""
        print(f"  {i}. {r['config_name']:15s}  composite={r['composite_score']:.4f}  "
              f"tokens={r['avg_tokens']:.0f}  score={r['avg_score']:.2f}{marker}")

    print(f"\nOptimal config: {best_config['name']}")
    print(f"  chunk_size={best_config['chunk_size']}, include_examples={best_config['include_examples']}, "
          f"max_results={best_config['max_search_results']}")

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"autoresearch_{ts}.json"
    with open(out_path, "w") as f:
        json.dump({"best_config": best_config, "all_runs": all_runs}, f, indent=2)
    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
