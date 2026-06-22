from __future__ import annotations

"""
Main experiment runner.

Runs each benchmark question through all benchmark conditions and measures:
  1. Time to answer (elapsed seconds)
  2. Accuracy (judge LLM scores 0-2)
  3. Response length (characters — proxy for conciseness)

Usage:
    python run_experiment.py                                       # All questions
    python run_experiment.py --tier 1                              # Tier 1 only
    python run_experiment.py --ids T1-01 T2-03                     # Specific questions
    python run_experiment.py --dry-run                             # Skip API calls, show plan
    python run_experiment.py --verbose                             # Show agent progress
    python run_experiment.py --provider cursor --model composer-2.5
    python run_experiment.py --provider openrouter --model "~openai/gpt-latest"
    python run_experiment.py --mintlify-model auto                 # Override only the docs agent's model

Environment variables (loaded from benchmark/.env if present):
    CURSOR_API_KEY      — required for --provider cursor.
    OPENROUTER_API_KEY  — required for --provider openrouter.
    MINTLIFY_MCP_URL    — optional. Mintlify-hosted RingCentral docs MCP server.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Load benchmark/.env so CURSOR_API_KEY (and MINTLIFY_MCP_URL) are available
# without the user having to export them manually.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from agents import (
    raw_agent,
    no_markdown_agent,
    mintlify_agent,
    raw_mintlify_agent,
    context_metrics,
    openrouter_agent,
)
import judge as judge_module

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
RESULTS_DIR = Path(__file__).parent / "results"

# Order is intentional: least docs → more docs → structured docs → combined access.
# Raw (no Markdown) first, then Raw + Markdown, then Mintlify MCP, then hybrid.
# "raw" (Raw + Markdown) remains the delta baseline regardless of position.
CONDITIONS = [
    {
        "key": "no_markdown",
        "label": "Raw without Markdown",
        "description": "Cursor SDK + source files with docs/ and Markdown removed",
        "agent": no_markdown_agent,
        "model_arg": "model",
    },
    {
        "key": "raw",
        "label": "Raw + Markdown",
        "description": "Cursor SDK + sanitized source files including Markdown",
        "agent": raw_agent,
        "model_arg": "model",
    },
    {
        "key": "mintlify",
        "label": "Mintlify MCP",
        "description": "Cursor SDK + Mintlify docs MCP",
        "agent": mintlify_agent,
        "model_arg": "mintlify_model",
    },
    {
        "key": "raw_mintlify",
        "label": "Raw + Markdown + MCP",
        "description": "Cursor SDK + sanitized source files including Markdown + Mintlify docs MCP",
        "agent": raw_mintlify_agent,
        "model_arg": "model",
    },
]


def condition_description(condition: dict, provider: str) -> str:
    description = condition["description"]
    if provider == "openrouter":
        if condition["key"] == "mintlify":
            return "OpenRouter + live Mintlify docs MCP"
        if condition["key"] == "raw_mintlify":
            return "OpenRouter + sanitized source files including Markdown + live Mintlify docs MCP"
        return description.replace("Cursor SDK", "OpenRouter")
    return description


def load_questions(tier=None, ids=None):
    with open(QUESTIONS_FILE) as f:
        all_q = json.load(f)["questions"]

    if ids:
        all_q = [q for q in all_q if q["id"] in ids]
    elif tier is not None:
        all_q = [q for q in all_q if q["tier"] == tier]

    return all_q


def run_experiment(
    questions,
    model: str,
    mintlify_model: str | None = None,
    provider: str = "cursor",
    judge_model: str | None = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    # All conditions default to the same provider/model so the main variable is
    # the information layer: local Markdown, no Markdown, or live Mintlify MCP.
    mintlify_model = mintlify_model or model
    judge_model = judge_model or model
    model_by_arg = {"model": model, "mintlify_model": mintlify_model}
    results: list[dict] = []
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"RingCentral Markdown Layer Experiment")
    print(f"Provider: {provider}")
    for condition in CONDITIONS:
        condition_model = model_by_arg[condition["model_arg"]]
        description = condition_description(condition, provider)
        print(f"{condition['label']:<22} {condition_model} ({description})")
    print(f"Questions: {len(questions)}")
    print(f"{'='*60}\n")

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['id']} (Tier {q['tier']}) — {q['question'][:65]}...")

        if dry_run:
            print("  [DRY RUN — skipping API calls]")
            row = {
                "id": q["id"],
                "tier": q["tier"],
                "category": q["category"],
                "question": q["question"],
                "scores": None,
                "valid": False,
                "status": "dry_run",
            }
            for condition in CONDITIONS:
                row[condition["key"]] = {
                    "answer": "(dry run)",
                    "elapsed_s": 0,
                    "response_length": 0,
                    "ok": True,
                    "error": None,
                    **context_metrics.empty_metrics(),
                }
            results.append(row)
            continue

        condition_results = {}
        condition_ok = {}
        for condition in CONDITIONS:
            key = condition["key"]
            condition_model = model_by_arg[condition["model_arg"]]
            try:
                condition_results[key] = condition["agent"].run(
                    q["question"],
                    model=condition_model,
                    verbose=verbose,
                    provider=provider,
                )
            except Exception as e:
                print(f"  [ERROR] {key}: {e}")
                condition_results[key] = {
                    "answer": f"ERROR: {e}",
                    "elapsed_s": 0,
                    "response_length": 0,
                    "ok": False,
                    "error": str(e),
                    **context_metrics.empty_metrics(),
                }
            result = condition_results[key]
            condition_ok[key] = result.get("ok", not str(result.get("answer", "")).startswith("ERROR"))

        valid = all(condition_ok.values())
        status = "ok" if valid else "agent_failed"
        scores = None

        if valid:
            try:
                scores = judge_module.score_conditions(
                    question=q["question"],
                    ground_truth=q["ground_truth"],
                    key_facts=q["key_facts"],
                    answers={key: result["answer"] for key, result in condition_results.items()},
                    provider=provider,
                    model=judge_model,
                )
            except Exception as e:
                print(f"  [ERROR] judge: {e}")
                valid = False
                status = "judge_failed"
                scores = {}
                for condition in CONDITIONS:
                    scores[f"{condition['key']}_score"] = None
                    scores[f"{condition['key']}_reasoning"] = str(e)

        if valid:
            for condition in CONDITIONS:
                key = condition["key"]
                result = condition_results[key]
                token_prefix = "" if result.get("token_count_is_estimate") is False else "~"
                print(
                    f"  {condition['label']:<20} "
                    f"{result['elapsed_s']:5.1f}s, {result['response_length']:5d} chars, "
                    f"{token_prefix}{result.get('total_tokens', result.get('total_tokens_est', 0)):6d} tok, "
                    f"score={scores[f'{key}_score']}/2"
                )
                if provider == "openrouter":
                    print(
                        f"  {'':<20} "
                        f"OpenRouter cost={result.get('openrouter_cost', 0):.6f} credits, "
                        f"generations={len(result.get('openrouter_generation_ids', []))}"
                    )
            raw_score = scores["raw_score"]
            deltas = []
            for condition in CONDITIONS:
                key = condition["key"]
                if key == "raw":
                    continue
                deltas.append(f"{condition['label']} {scores[f'{key}_score'] - raw_score:+d}")
            print(f"  Score deltas vs Raw + Markdown: {'  |  '.join(deltas)}")
        else:
            for condition in CONDITIONS:
                key = condition["key"]
                result = condition_results[key]
                print(
                    f"  {condition['label']:<20} "
                    f"{result['elapsed_s']:5.1f}s, {result['response_length']:5d} chars, "
                    f"ok={condition_ok[key]}"
                )
            print(f"  INVALID: {status} — excluded from accuracy and timing summaries")
        print()

        row = {
            "id": q["id"],
            "tier": q["tier"],
            "category": q["category"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "scores": scores,
            "valid": valid,
            "status": status,
        }
        for condition in CONDITIONS:
            key = condition["key"]
            result = condition_results[key]
            token_prefix = "" if result.get("token_count_is_estimate") is False else "~"
            row[key] = {
                "answer": result["answer"],
                "elapsed_s": result["elapsed_s"],
                "response_length": result["response_length"],
                "ok": condition_ok[key],
                "error": result.get("error"),
                "tool_result_bytes": result.get("tool_result_bytes", 0),
                "tool_calls": result.get("tool_calls", 0),
                "tool_breakdown": result.get("tool_breakdown", {}),
                "context_tokens_est": result.get("context_tokens_est", 0),
                "output_tokens_est": result.get("output_tokens_est", 0),
                "total_tokens_est": result.get("total_tokens_est", 0),
                "prompt_tokens": result.get("prompt_tokens", result.get("context_tokens_est", 0)),
                "completion_tokens": result.get("completion_tokens", result.get("output_tokens_est", 0)),
                "total_tokens": result.get("total_tokens", result.get("total_tokens_est", 0)),
                "token_source": result.get("token_source", "estimate"),
                "token_count_is_estimate": result.get("token_count_is_estimate", True),
                "openrouter_prompt_tokens": result.get("openrouter_prompt_tokens", 0),
                "openrouter_completion_tokens": result.get("openrouter_completion_tokens", 0),
                "openrouter_total_tokens": result.get("openrouter_total_tokens", 0),
                "openrouter_cost": result.get("openrouter_cost", 0),
                "openrouter_generation_ids": result.get("openrouter_generation_ids", []),
                "token_display_prefix": token_prefix,
            }
        results.append(row)

    total_elapsed = time.time() - start_time
    valid_results = [r for r in results if r.get("valid")]
    dry_run_results = [r for r in results if r.get("status") == "dry_run"]
    invalid_results = [r for r in results if not r.get("valid") and r.get("status") != "dry_run"]

    def avg(key: str, condition_key: str):
        vals = [r[condition_key][key] for r in valid_results if r[condition_key][key] > 0]
        return round(sum(vals) / len(vals), 2) if vals else 0

    def accuracy(condition_key: str) -> dict:
        score_key = f"{condition_key}_score"
        scores = [r["scores"][score_key] for r in valid_results]
        return {
            "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "pct_correct": round(sum(1 for s in scores if s == 2) / len(scores) * 100, 1) if scores else 0,
        }

    summary = {
        "experiment_date": datetime.utcnow().isoformat(),
        "provider": provider,
        "model": model,
        "mintlify_model": mintlify_model,
        "judge_model": judge_model,
        "conditions": [
            {
                "key": condition["key"],
                "label": condition["label"],
                "description": condition_description(condition, provider),
                "model": model_by_arg[condition["model_arg"]],
            }
            for condition in CONDITIONS
        ],
        "n_questions": len(results),
        "n_scored": len(valid_results),
        "n_invalid": len(invalid_results),
        "n_dry_run": len(dry_run_results),
        "total_elapsed_s": round(total_elapsed, 1),
    }

    for condition in CONDITIONS:
        key = condition["key"]
        summary[key] = {
            "avg_elapsed_s": avg("elapsed_s", key),
            "avg_response_length": avg("response_length", key),
            "avg_tool_result_bytes": avg("tool_result_bytes", key),
            "avg_tool_calls": avg("tool_calls", key),
            "avg_context_tokens_est": avg("context_tokens_est", key),
            "avg_output_tokens_est": avg("output_tokens_est", key),
            "avg_total_tokens_est": avg("total_tokens_est", key),
            "total_tokens_est": sum(r[key]["total_tokens_est"] for r in valid_results),
            "avg_prompt_tokens": avg("prompt_tokens", key),
            "avg_completion_tokens": avg("completion_tokens", key),
            "avg_total_tokens": avg("total_tokens", key),
            "total_tokens": sum(r[key]["total_tokens"] for r in valid_results),
            "token_source": (
                "openrouter_native_usage"
                if provider == "openrouter"
                else "cursor_tool_result_estimate"
            ),
            "openrouter_cost": round(sum(r[key].get("openrouter_cost", 0) for r in valid_results), 8),
            "accuracy": accuracy(key),
        }

    raw_t = summary["raw"]["avg_elapsed_s"]
    if raw_t > 0:
        for condition in CONDITIONS:
            key = condition["key"]
            summary[key]["time_delta_vs_raw_pct"] = round((1 - summary[key]["avg_elapsed_s"] / raw_t) * 100, 1)

    raw_score = summary["raw"]["accuracy"]["avg_score"]
    for condition in CONDITIONS:
        key = condition["key"]
        summary[key]["score_delta_vs_raw"] = round(summary[key]["accuracy"]["avg_score"] - raw_score, 2)

    token_avg_key = "avg_total_tokens" if provider == "openrouter" else "avg_total_tokens_est"
    raw_tokens = summary["raw"][token_avg_key]
    if raw_tokens > 0:
        for condition in CONDITIONS:
            key = condition["key"]
            summary[key]["token_delta_vs_raw_pct"] = round(
                (1 - summary[key][token_avg_key] / raw_tokens) * 100, 1
            )

    output = {"summary": summary, "results": results}

    if provider == "openrouter":
        judge_usages = [
            r.get("scores", {}).get("judge_openrouter_usage")
            for r in valid_results
            if r.get("scores", {}).get("judge_openrouter_usage")
        ]
        summary["judge_openrouter"] = {
            "model": judge_model,
            "prompt_tokens": sum(u.get("prompt_tokens", 0) for u in judge_usages),
            "completion_tokens": sum(u.get("completion_tokens", 0) for u in judge_usages),
            "total_tokens": sum(u.get("total_tokens", 0) for u in judge_usages),
            "cost": round(sum(u.get("cost", 0) for u in judge_usages), 8),
            "generations": sum(len(u.get("generation_ids", [])) for u in judge_usages),
        }

    print(f"{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    if dry_run:
        print(f"Dry-run questions: {summary['n_dry_run']}")
    else:
        print(f"Scored questions: {summary['n_scored']}/{summary['n_questions']}  (invalid: {summary['n_invalid']})")
    if provider == "openrouter":
        token_headers = ("Prompt", "Completion", "Total")
    else:
        token_headers = ("Ctx tok", "Out tok", "Tot tok")
    print(f"{'Condition':<24} {'Score':>8} {'Correct':>10} {'Time':>9} {token_headers[0]:>9} {token_headers[1]:>11} {token_headers[2]:>9} {'Δ tok':>8} {'Δ Score':>9}")
    print(f"{'-'*102}")
    for condition in CONDITIONS:
        key = condition["key"]
        acc = summary[key]["accuracy"]
        prompt_or_context = summary[key]["avg_prompt_tokens"] if provider == "openrouter" else summary[key]["avg_context_tokens_est"]
        completion_or_output = summary[key]["avg_completion_tokens"] if provider == "openrouter" else summary[key]["avg_output_tokens_est"]
        total_tokens = summary[key]["avg_total_tokens"] if provider == "openrouter" else summary[key]["avg_total_tokens_est"]
        print(
            f"{condition['label']:<24} "
            f"{acc['avg_score']:>8.2f} "
            f"{acc['pct_correct']:>9.1f}% "
            f"{summary[key]['avg_elapsed_s']:>8.1f}s "
            f"{prompt_or_context:>9,.0f} "
            f"{completion_or_output:>11,.0f} "
            f"{total_tokens:>9,.0f} "
            f"{summary[key].get('token_delta_vs_raw_pct', 0):>+7.0f}% "
            f"{summary[key]['score_delta_vs_raw']:>+9.2f}"
        )
    if provider == "openrouter":
        print("\nOpenRouter token counts are native usage totals aggregated across each tool loop.")
        print("Cost is saved in the JSON under each condition's openrouter_cost field.")
        print(
            f"Judge OpenRouter cost: {summary['judge_openrouter']['cost']:.6f} credits "
            f"({summary['judge_openrouter']['total_tokens']:,} tokens)"
        )
    else:
        print(f"\nToken counts are estimates: context tokens ≈ tool-result bytes / {context_metrics.CHARS_PER_TOKEN}")
        print(f"(file reads, grep, MCP search results fed back to the model), output tokens ≈ answer chars / {context_metrics.CHARS_PER_TOKEN}.")
        print(f"'Δ tok' = total-token change vs the Raw + Markdown baseline. Negative = fewer tokens.")

    if dry_run:
        print("\nDry run complete. No results file was written.")
    else:
        RESULTS_DIR.mkdir(exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        prefix = "experiment" if summary["n_invalid"] == 0 else "failed_experiment"
        output_path = RESULTS_DIR / f"{prefix}_{ts}.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        output["output_path"] = str(output_path)
        if summary["n_invalid"]:
            print(f"\nInvalid run saved for debugging: {output_path}")
            print("This file is excluded from normal experiment_*.json result naming.")
        else:
            print(f"\nResults saved to: {output_path}")

    return output


def main():
    parser = argparse.ArgumentParser(description="RingCentral docs quality benchmark")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--provider", choices=["cursor", "openrouter"], default="cursor")
    parser.add_argument("--model", default=None, help="Model for the selected provider")
    parser.add_argument(
        "--mintlify-model",
        default=None,
        help="Cursor model for the Mintlify docs agent (defaults to --model)",
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="Judge model for the selected provider (defaults to --model)",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.model is None:
        args.model = "composer-2.5" if args.provider == "cursor" else openrouter_agent.default_model()
    if args.judge_model is None and args.provider == "openrouter":
        args.judge_model = openrouter_agent.default_judge_model()

    if not args.dry_run and args.provider == "cursor" and not os.environ.get("CURSOR_API_KEY"):
        print("Error: CURSOR_API_KEY not set.")
        print("Add it to benchmark/.env (see .env.example) or export it:")
        print("  export CURSOR_API_KEY=crsr_...")
        sys.exit(1)
    if not args.dry_run and args.provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY not set.")
        print("Add it to benchmark/.env (see .env.example) or export it:")
        print("  export OPENROUTER_API_KEY=sk-or-...")
        sys.exit(1)

    questions = load_questions(tier=args.tier, ids=args.ids)
    if not questions:
        print("No questions matched the filters")
        sys.exit(1)

    output = run_experiment(
        questions=questions,
        model=args.model,
        mintlify_model=args.mintlify_model,
        provider=args.provider,
        judge_model=args.judge_model,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    if not args.dry_run and output["summary"]["n_invalid"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
