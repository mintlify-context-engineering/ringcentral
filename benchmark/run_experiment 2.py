"""
Main experiment runner.

Runs each benchmark question through both agents and measures:
  1. Token cost (input + output tokens)
  2. Accuracy (judge LLM scores 0-2)
  3. Tool calls (proxy for steps / speed)

Usage:
    python run_experiment.py                        # All 20 questions
    python run_experiment.py --tier 1               # Tier 1 only
    python run_experiment.py --ids T1-01 T2-03      # Specific questions
    python run_experiment.py --dry-run              # Skip API calls, show plan
    python run_experiment.py --verbose              # Show tool calls in real time
    python run_experiment.py --model claude-haiku-4-5-20251001  # Override model
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent))
from agents import raw_agent, mintlify_agent
import judge as judge_module

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
RESULTS_DIR = Path(__file__).parent / "results"


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
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    client = anthropic.Anthropic()
    results = []
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"RingCentral Docs Quality Experiment")
    print(f"Model: {model}")
    print(f"Questions: {len(questions)}")
    print(f"{'='*60}\n")

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['id']} (Tier {q['tier']}) — {q['question'][:70]}...")

        if dry_run:
            print("  [DRY RUN — skipping API calls]")
            results.append({
                "id": q["id"],
                "tier": q["tier"],
                "category": q["category"],
                "question": q["question"],
                "raw": {"answer": "(dry run)", "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tool_calls": 0, "elapsed_s": 0},
                "mintlify": {"answer": "(dry run)", "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tool_calls": 0, "elapsed_s": 0},
                "scores": {"raw_score": 0, "mintlify_score": 0},
            })
            continue

        # Run raw agent
        t0 = time.time()
        try:
            raw_result = raw_agent.run(q["question"], model=model, verbose=verbose)
        except Exception as e:
            print(f"  [ERROR] raw_agent failed: {e}")
            raw_result = {"answer": f"ERROR: {e}", "input_tokens": 0, "output_tokens": 0, "tool_calls": 0}
        raw_elapsed = time.time() - t0

        # Run mintlify agent
        t0 = time.time()
        try:
            mintlify_result = mintlify_agent.run(q["question"], model=model, verbose=verbose)
        except Exception as e:
            print(f"  [ERROR] mintlify_agent failed: {e}")
            mintlify_result = {"answer": f"ERROR: {e}", "input_tokens": 0, "output_tokens": 0, "tool_calls": 0}
        mintlify_elapsed = time.time() - t0

        # Judge scores
        try:
            scores = judge_module.score(
                question=q["question"],
                ground_truth=q["ground_truth"],
                key_facts=q["key_facts"],
                answer_raw=raw_result["answer"],
                answer_mintlify=mintlify_result["answer"],
                client=client,
            )
        except Exception as e:
            print(f"  [ERROR] judge failed: {e}")
            scores = {"raw_score": 0, "mintlify_score": 0, "raw_reasoning": str(e), "mintlify_reasoning": str(e)}

        raw_tokens = raw_result["input_tokens"] + raw_result["output_tokens"]
        mintlify_tokens = mintlify_result["input_tokens"] + mintlify_result["output_tokens"]
        token_reduction = (1 - mintlify_tokens / raw_tokens) * 100 if raw_tokens > 0 else 0

        print(f"  Raw:      tokens={raw_tokens:5d}, tools={raw_result['tool_calls']:2d}, score={scores['raw_score']}/2, {raw_elapsed:.1f}s")
        print(f"  Mintlify: tokens={mintlify_tokens:5d}, tools={mintlify_result['tool_calls']:2d}, score={scores['mintlify_score']}/2, {mintlify_elapsed:.1f}s")
        print(f"  Token reduction: {token_reduction:+.0f}%  |  Score delta: {scores['mintlify_score'] - scores['raw_score']:+d}")
        print()

        results.append({
            "id": q["id"],
            "tier": q["tier"],
            "category": q["category"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "raw": {
                "answer": raw_result["answer"],
                "input_tokens": raw_result["input_tokens"],
                "output_tokens": raw_result["output_tokens"],
                "total_tokens": raw_tokens,
                "tool_calls": raw_result["tool_calls"],
                "elapsed_s": round(raw_elapsed, 2),
                "hit_limit": raw_result.get("hit_limit", False),
            },
            "mintlify": {
                "answer": mintlify_result["answer"],
                "input_tokens": mintlify_result["input_tokens"],
                "output_tokens": mintlify_result["output_tokens"],
                "total_tokens": mintlify_tokens,
                "tool_calls": mintlify_result["tool_calls"],
                "elapsed_s": round(mintlify_elapsed, 2),
                "hit_limit": mintlify_result.get("hit_limit", False),
            },
            "scores": scores,
        })

    total_elapsed = time.time() - start_time

    # Aggregate stats
    def agg(field: str, condition_key: str) -> dict:
        vals = [r[condition_key][field] for r in results]
        total = sum(vals)
        avg = total / len(vals) if vals else 0
        return {"total": total, "avg": round(avg, 1), "values": vals}

    summary = {
        "experiment_date": datetime.utcnow().isoformat(),
        "model": model,
        "n_questions": len(results),
        "total_elapsed_s": round(total_elapsed, 1),
        "raw": {
            "total_tokens": agg("total_tokens", "raw"),
            "tool_calls": agg("tool_calls", "raw"),
            "accuracy": {
                "avg_score": round(sum(r["scores"]["raw_score"] for r in results) / len(results), 2) if results else 0,
                "pct_correct": round(sum(1 for r in results if r["scores"]["raw_score"] == 2) / len(results) * 100, 1) if results else 0,
                "pct_partial": round(sum(1 for r in results if r["scores"]["raw_score"] == 1) / len(results) * 100, 1) if results else 0,
                "pct_wrong": round(sum(1 for r in results if r["scores"]["raw_score"] == 0) / len(results) * 100, 1) if results else 0,
            },
        },
        "mintlify": {
            "total_tokens": agg("total_tokens", "mintlify"),
            "tool_calls": agg("tool_calls", "mintlify"),
            "accuracy": {
                "avg_score": round(sum(r["scores"]["mintlify_score"] for r in results) / len(results), 2) if results else 0,
                "pct_correct": round(sum(1 for r in results if r["scores"]["mintlify_score"] == 2) / len(results) * 100, 1) if results else 0,
                "pct_partial": round(sum(1 for r in results if r["scores"]["mintlify_score"] == 1) / len(results) * 100, 1) if results else 0,
                "pct_wrong": round(sum(1 for r in results if r["scores"]["mintlify_score"] == 0) / len(results) * 100, 1) if results else 0,
            },
        },
    }

    raw_avg = summary["raw"]["total_tokens"]["avg"]
    mint_avg = summary["mintlify"]["total_tokens"]["avg"]
    if raw_avg > 0:
        summary["token_reduction_pct"] = round((1 - mint_avg / raw_avg) * 100, 1)
    summary["score_improvement"] = round(
        summary["mintlify"]["accuracy"]["avg_score"] - summary["raw"]["accuracy"]["avg_score"], 2
    )
    summary["tool_call_reduction_pct"] = round(
        (1 - summary["mintlify"]["tool_calls"]["avg"] / summary["raw"]["tool_calls"]["avg"]) * 100, 1
    ) if summary["raw"]["tool_calls"]["avg"] > 0 else 0

    output = {"summary": summary, "results": results}

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"experiment_{ts}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Token reduction:   {summary.get('token_reduction_pct', 'N/A')}%")
    print(f"Score improvement: {summary['score_improvement']:+.2f}/2.0")
    print(f"Tool call reduction: {summary.get('tool_call_reduction_pct', 'N/A')}%")
    print(f"\nRaw:      avg_tokens={raw_avg:.0f}, avg_score={summary['raw']['accuracy']['avg_score']}, avg_tools={summary['raw']['tool_calls']['avg']}")
    print(f"Mintlify: avg_tokens={mint_avg:.0f}, avg_score={summary['mintlify']['accuracy']['avg_score']}, avg_tools={summary['mintlify']['tool_calls']['avg']}")
    print(f"\nResults saved to: {output_path}")

    return output


def main():
    parser = argparse.ArgumentParser(description="RingCentral docs quality benchmark")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], help="Only run questions of this tier")
    parser.add_argument("--ids", nargs="+", help="Specific question IDs to run")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001", help="Claude model to use")
    parser.add_argument("--verbose", action="store_true", help="Print tool calls in real time")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls, just show plan")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY") and not args.dry_run:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    questions = load_questions(tier=args.tier, ids=args.ids)
    if not questions:
        print("No questions matched the filters")
        sys.exit(1)

    run_experiment(
        questions=questions,
        model=args.model,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
