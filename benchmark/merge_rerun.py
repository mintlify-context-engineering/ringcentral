from __future__ import annotations

"""Merge rerun rows into an experiment JSON and recompute the summary.

Usage:
    python merge_rerun.py \
      --base results/failed_experiment_20260623_090301.json \
      --rerun results/experiment_20260623_105721.json \
      --out results/experiment_20260623_090301_complete.json
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_experiment import CONDITIONS, summarize_results


BENCHMARK_DIR = Path(__file__).parent


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if candidate.exists() or candidate.is_absolute():
        return candidate
    return BENCHMARK_DIR / candidate


def _read_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _condition_keys(data: dict) -> list[str]:
    return [condition["key"] for condition in data["summary"]["conditions"]]


def merge(base: dict, rerun: dict, *, only_ids: set[str] | None = None) -> tuple[dict, list[str]]:
    base_keys = _condition_keys(base)
    rerun_keys = _condition_keys(rerun)
    if base_keys != rerun_keys:
        raise ValueError(f"Condition mismatch: base={base_keys}, rerun={rerun_keys}")

    rerun_by_id = {row["id"]: row for row in rerun["results"]}
    if only_ids:
        rerun_by_id = {row_id: row for row_id, row in rerun_by_id.items() if row_id in only_ids}

    replaced_ids = []
    merged_results = []
    for row in base["results"]:
        row_id = row["id"]
        if row_id in rerun_by_id:
            merged_results.append(rerun_by_id[row_id])
            replaced_ids.append(row_id)
        else:
            merged_results.append(row)

    missing_ids = sorted(set(rerun_by_id) - {row["id"] for row in base["results"]})
    if missing_ids:
        raise ValueError(f"Rerun contains ids not present in base: {missing_ids}")
    return {"results": merged_results}, replaced_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge benchmark rerun rows into a prior experiment.")
    parser.add_argument("--base", required=True, help="Base experiment JSON, often failed_experiment_*.json.")
    parser.add_argument("--rerun", required=True, help="Experiment JSON containing replacement rows.")
    parser.add_argument("--out", required=True, help="Output path for the merged experiment JSON.")
    parser.add_argument("--ids", nargs="+", help="Optional row ids to replace. Defaults to all rows present in rerun.")
    args = parser.parse_args()

    base_path = _resolve(args.base)
    rerun_path = _resolve(args.rerun)
    out_path = _resolve(args.out)
    base = _read_json(base_path)
    rerun = _read_json(rerun_path)

    merged, replaced_ids = merge(base, rerun, only_ids=set(args.ids) if args.ids else None)
    base_summary = base["summary"]
    rerun_summary = rerun["summary"]
    total_elapsed = (base_summary.get("total_elapsed_s") or 0) + (rerun_summary.get("total_elapsed_s") or 0)
    merge_metadata = {
        "merged_at": datetime.utcnow().isoformat(),
        "base_file": str(base_path),
        "rerun_file": str(rerun_path),
        "base_sha256": _sha256(base_path),
        "rerun_sha256": _sha256(rerun_path),
        "replaced_ids": replaced_ids,
        "n_replaced": len(replaced_ids),
        "base_experiment_date": base_summary.get("experiment_date"),
        "rerun_experiment_date": rerun_summary.get("experiment_date"),
    }

    summary = summarize_results(
        merged["results"],
        provider=base_summary.get("provider", "cursor"),
        model=base_summary.get("model"),
        mintlify_model=base_summary.get("mintlify_model") or base_summary.get("model"),
        judge_model=base_summary.get("judge_model") or base_summary.get("model"),
        conditions=base_summary.get("conditions") or CONDITIONS,
        total_elapsed_s=total_elapsed,
        merge_metadata=merge_metadata,
    )
    output = {"summary": summary, "results": merged["results"]}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Merged -> {out_path}")
    print(
        f"Scored: {summary['n_scored']}/{summary['n_questions']} "
        f"(invalid: {summary['n_invalid']}, partial: {summary['n_partial']}, replaced: {len(replaced_ids)})"
    )
    print(f"{'Condition':<24}{'Score':>7}{'Correct':>10}{'Scored':>9}{'Failed':>9}{'Time':>9}{'ΔScore':>8}")
    for condition in summary["conditions"]:
        key = condition["key"]
        metric = summary[key]
        accuracy = metric["accuracy"]
        print(
            f"{condition['label']:<24}{accuracy['avg_score']:>7.2f}"
            f"{accuracy['pct_correct']:>9.1f}%{metric['n_scored']:>9}"
            f"{metric['n_failed']:>9}{metric['avg_elapsed_s']:>8.1f}s"
            f"{metric['score_delta_vs_raw']:>+8.2f}"
        )


if __name__ == "__main__":
    main()
