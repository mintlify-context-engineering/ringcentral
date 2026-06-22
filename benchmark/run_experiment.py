"""
Main experiment runner.

Runs each benchmark question through both agents and measures:
  1. Time to answer (elapsed seconds)
  2. Accuracy (judge LLM scores 0-2)
  3. Response length (characters — proxy for conciseness)

Usage:
    python run_experiment.py                                       # All 20 questions
    python run_experiment.py --tier 1                              # Tier 1 only
    python run_experiment.py --ids T1-01 T2-03                     # Specific questions
    python run_experiment.py --dry-run                             # Skip API calls, show plan
    python run_experiment.py --verbose                             # Show agent progress
    python run_experiment.py --model composer-2.5                  # Override Cursor model (raw agent)
    python run_experiment.py --mintlify-model claude-haiku-4-5-20251001  # Override Claude model (mintlify agent)

Environment variables:
    CURSOR_API_KEY      — required for the raw monorepo agent (Cursor SDK)
    ANTHROPIC_API_KEY   — required for the Mintlify MCP agent (Anthropic SDK)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

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
    mintlify_model: str = "claude-haiku-4-5-20251001",
    verbose: bool = False,
    dry_run: bool = False,
) -> dict:
    results = []
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"RingCentral Docs Quality Experiment")
    print(f"Raw agent model:      {model} (Cursor SDK)")
    print(f"Mintlify agent model: {mintlify_model} (Anthropic SDK + Mintlify MCP)")
    print(f"Questions: {len(questions)}")
    print(f"{'='*60}\n")

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['id']} (Tier {q['tier']}) — {q['question'][:65]}...")

        if dry_run:
            print("  [DRY RUN — skipping API calls]")
            results.append({
                "id": q["id"],
                "tier": q["tier"],
                "category": q["category"],
                "question": q["question"],
                "raw": {"answer": "(dry run)", "elapsed_s": 0, "response_length": 0},
                "mintlify": {"answer": "(dry run)", "elapsed_s": 0, "response_length": 0},
                "scores": {"raw_score": 0, "mintlify_score": 0},
            })
            continue

        # Run raw agent
        try:
            raw_result = raw_agent.run(q["question"], model=model, verbose=verbose)
        except Exception as e:
            print(f"  [ERROR] raw_agent: {e}")
            raw_result = {"answer": f"ERROR: {e}", "elapsed_s": 0, "response_length": 0}

        # Run Mintlify agent (uses live Mintlify MCP server + Anthropic SDK)
        try:
            mintlify_result = mintlify_agent.run(q["question"], model=mintlify_model, verbose=verbose)
        except Exception as e:
            print(f"  [ERROR] mintlify_agent: {e}")
            mintlify_result = {"answer": f"ERROR: {e}", "elapsed_s": 0, "response_length": 0}

        # Judge scores
        try:
            scores = judge_module.score(
                question=q["question"],
                ground_truth=q["ground_truth"],
                key_facts=q["key_facts"],
                answer_raw=raw_result["answer"],
                answer_mintlify=mintlify_result["answer"],
            )
        except Exception as e:
            print(f"  [ERROR] judge: {e}")
            scores = {"raw_score": 0, "mintlify_score": 0, "raw_reasoning": str(e), "mintlify_reasoning": str(e)}

        time_delta_pct = (
            (raw_result["elapsed_s"] - mintlify_result["elapsed_s"]) / raw_result["elapsed_s"] * 100
            if raw_result["elapsed_s"] > 0 else 0
        )
        len_delta_pct = (
            (raw_result["response_length"] - mintlify_result["response_length"]) / raw_result["response_length"] * 100
            if raw_result["response_length"] > 0 else 0
        )

        print(f"  Raw:      {raw_result['elapsed_s']:5.1f}s, {raw_result['response_length']:5d} chars, score={scores['raw_score']}/2")
        print(f"  Mintlify: {mintlify_result['elapsed_s']:5.1f}s, {mintlify_result['response_length']:5d} chars, score={scores['mintlify_score']}/2")
        print(f"  Time delta: {time_delta_pct:+.0f}%  |  Length delta: {len_delta_pct:+.0f}%  |  Score delta: {scores['mintlify_score'] - scores['raw_score']:+d}")
        print()

        results.append({
            "id": q["id"],
            "tier": q["tier"],
            "category": q["category"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "raw": {
                "answer": raw_result["answer"],
                "elapsed_s": raw_result["elapsed_s"],
                "response_length": raw_result["response_length"],
            },
            "mintlify": {
                "answer": mintlify_result["answer"],
                "elapsed_s": mintlify_result["elapsed_s"],
                "response_length": mintlify_result["response_length"],
            },
            "scores": scores,
        })

    total_elapsed = time.time() - start_time

    def avg(key: str, condition_key: str):
        vals = [r[condition_key][key] for r in results if r[condition_key][key] > 0]
        return round(sum(vals) / len(vals), 2) if vals else 0

    summary = {
        "experiment_date": datetime.utcnow().isoformat(),
        "model": model,
        "n_questions": len(results),
        "total_elapsed_s": round(total_elapsed, 1),
        "raw": {
            "avg_elapsed_s": avg("elapsed_s", "raw"),
            "avg_response_length": avg("response_length", "raw"),
            "accuracy": {
                "avg_score": round(sum(r["scores"]["raw_score"] for r in results) / len(results), 2) if results else 0,
                "pct_correct": round(sum(1 for r in results if r["scores"]["raw_score"] == 2) / len(results) * 100, 1) if results else 0,
            },
        },
        "mintlify": {
            "avg_elapsed_s": avg("elapsed_s", "mintlify"),
            "avg_response_length": avg("response_length", "mintlify"),
            "accuracy": {
                "avg_score": round(sum(r["scores"]["mintlify_score"] for r in results) / len(results), 2) if results else 0,
                "pct_correct": round(sum(1 for r in results if r["scores"]["mintlify_score"] == 2) / len(results) * 100, 1) if results else 0,
            },
        },
    }

    raw_t = summary["raw"]["avg_elapsed_s"]
    mint_t = summary["mintlify"]["avg_elapsed_s"]
    if raw_t > 0:
        summary["time_reduction_pct"] = round((1 - mint_t / raw_t) * 100, 1)
    summary["score_improvement"] = round(
        summary["mintlify"]["accuracy"]["avg_score"] - summary["raw"]["accuracy"]["avg_score"], 2
    )

    output = {"summary": summary, "results": results}

    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"experiment_{ts}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Time reduction:    {summary.get('time_reduction_pct', 'N/A')}%")
    print(f"Score improvement: {summary['score_improvement']:+.2f}/2.0")
    print(f"\nRaw:      avg_time={raw_t}s, avg_score={summary['raw']['accuracy']['avg_score']}")
    print(f"Mintlify: avg_time={mint_t}s, avg_score={summary['mintlify']['accuracy']['avg_score']}")
    print(f"\nResults saved to: {output_path}")

    return output


def main():
    parser = argparse.ArgumentParser(description="RingCentral docs quality benchmark")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3])
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--model", default="composer-2.5", help="Cursor model for raw agent")
    parser.add_argument(
        "--mintlify-model",
        default="claude-haiku-4-5-20251001",
        help="Claude model for Mintlify MCP agent",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.dry_run:
        missing = []
        if not os.environ.get("CURSOR_API_KEY"):
            missing.append("CURSOR_API_KEY (required for raw monorepo agent)")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            missing.append("ANTHROPIC_API_KEY (required for Mintlify MCP agent)")
        if missing:
            for m in missing:
                print(f"Error: {m} not set")
            sys.exit(1)

    questions = load_questions(tier=args.tier, ids=args.ids)
    if not questions:
        print("No questions matched the filters")
        sys.exit(1)

    run_experiment(
        questions=questions,
        model=args.model,
        mintlify_model=args.mintlify_model,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
