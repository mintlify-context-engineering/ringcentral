"""
Generate an HTML dashboard from experiment results.

Usage:
    python report.py results/experiment_20240101_120000.json
    python report.py results/experiment_20240101_120000.json --open
"""

import argparse
import json
import sys
from pathlib import Path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mintlify Context Engineering Benchmark</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f13; color: #e1e1e6; min-height: 100vh; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 40px 48px 32px; border-bottom: 1px solid #2a2a3e; }}
  .header h1 {{ font-size: 26px; font-weight: 700; color: #fff; margin-bottom: 6px; }}
  .header .subtitle {{ color: #8b8b9e; font-size: 14px; }}
  .header .badge {{ display: inline-block; background: #3b82f6; color: #fff; padding: 2px 10px; border-radius: 20px; font-size: 12px; margin-left: 10px; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 32px 48px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }}
  .kpi {{ background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 12px; padding: 24px; text-align: center; }}
  .kpi .value {{ font-size: 42px; font-weight: 800; margin-bottom: 4px; }}
  .kpi .label {{ font-size: 13px; color: #8b8b9e; text-transform: uppercase; letter-spacing: 0.5px; }}
  .kpi .sublabel {{ font-size: 11px; color: #5a5a6e; margin-top: 4px; }}
  .green {{ color: #10b981; }}
  .blue {{ color: #3b82f6; }}
  .purple {{ color: #8b5cf6; }}
  .section {{ margin-bottom: 40px; }}
  .section h2 {{ font-size: 17px; font-weight: 600; color: #fff; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #2a2a3e; }}
  .comparison-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 32px; }}
  .metric-card {{ background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 10px; padding: 20px; }}
  .metric-card h3 {{ font-size: 13px; color: #8b8b9e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16px; }}
  .bar-container {{ margin-bottom: 10px; }}
  .bar-label {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }}
  .bar-label .name {{ color: #c1c1ce; }}
  .bar-label .val {{ color: #fff; font-weight: 600; }}
  .bar-track {{ height: 10px; background: #2a2a3e; border-radius: 5px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 5px; transition: width 0.3s; }}
  .bar-raw {{ background: linear-gradient(90deg, #ef4444, #f97316); }}
  .bar-mintlify {{ background: linear-gradient(90deg, #10b981, #3b82f6); }}
  table {{ width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 10px; overflow: hidden; border: 1px solid #2a2a3e; }}
  th {{ background: #13131f; padding: 12px 16px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #8b8b9e; border-bottom: 1px solid #2a2a3e; }}
  td {{ padding: 12px 16px; font-size: 13px; border-bottom: 1px solid #1e1e2e; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #1e1e2e; }}
  .tier-badge {{ display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .tier-1 {{ background: #1e3a5f; color: #60a5fa; }}
  .tier-2 {{ background: #1e3a2f; color: #34d399; }}
  .tier-3 {{ background: #3b1f5e; color: #a78bfa; }}
  .score {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 13px; }}
  .score-2 {{ background: #064e3b; color: #10b981; }}
  .score-1 {{ background: #78350f; color: #fbbf24; }}
  .score-0 {{ background: #7f1d1d; color: #f87171; }}
  .delta-pos {{ color: #10b981; font-weight: 600; }}
  .delta-neg {{ color: #ef4444; font-weight: 600; }}
  .delta-zero {{ color: #8b8b9e; }}
  .note {{ background: #1a1a2e; border: 1px solid #2a2a3e; border-left: 3px solid #3b82f6; border-radius: 6px; padding: 14px 18px; margin-bottom: 32px; font-size: 13px; color: #9b9bae; line-height: 1.6; }}
  .footer {{ text-align: center; padding: 32px; color: #4a4a5e; font-size: 12px; border-top: 1px solid #2a2a3e; margin-top: 20px; }}
</style>
</head>
<body>

<div class="header">
  <h1>Mintlify Context Engineering Benchmark <span class="badge">RingCentral</span></h1>
  <div class="subtitle">Raw Monorepo vs. Structured Docs Portal — {date} &nbsp;·&nbsp; Model: {model} &nbsp;·&nbsp; {n_questions} questions</div>
</div>

<div class="container">

  <div class="note">
    <strong>Experiment design:</strong> The same Cursor AI agent answers each question twice.
    <strong>Condition A (Raw):</strong> Agent navigates the full RingCentral monorepo (40+ sub-repos, 300+ markdown files).
    <strong>Condition B (Mintlify):</strong> Agent navigates 5 clean, cross-linked documentation pages.
    Both conditions use the same model. Scores reflect answer accuracy judged against ground truth.
  </div>

  <div class="kpi-grid">
    <div class="kpi">
      <div class="value green">{time_reduction}%</div>
      <div class="label">Faster to Answer</div>
      <div class="sublabel">{raw_avg_time}s → {mint_avg_time}s avg response time</div>
    </div>
    <div class="kpi">
      <div class="value blue">{score_improvement}</div>
      <div class="label">Accuracy Improvement</div>
      <div class="sublabel">{raw_accuracy} → {mint_accuracy} avg score (out of 2.0)</div>
    </div>
    <div class="kpi">
      <div class="value purple">{correct_pct}%</div>
      <div class="label">Correct (Mintlify)</div>
      <div class="sublabel">vs {raw_correct_pct}% for Raw Monorepo</div>
    </div>
  </div>

  <div class="comparison-grid">
    <div class="metric-card">
      <h3>Response Time (seconds) by Tier</h3>
      {time_bars}
    </div>
    <div class="metric-card">
      <h3>Accuracy (avg score/2) by Tier</h3>
      {accuracy_bars}
    </div>
  </div>

  <div class="section">
    <h2>Per-Question Results</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Question</th>
          <th>Raw Time</th>
          <th>Mint Time</th>
          <th>Δ Time</th>
          <th>Raw Score</th>
          <th>Mint Score</th>
          <th>Δ Score</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>

</div>

<div class="footer">
  Generated by Mintlify Context Engineering Benchmark &nbsp;·&nbsp; mintlify.com
</div>

</body>
</html>"""


def score_class(s):
    return f"score-{s}"


def delta_class(d):
    if d > 0:
        return "delta-pos"
    if d < 0:
        return "delta-neg"
    return "delta-zero"


def build_bars_time(results_by_tier: dict) -> str:
    max_val = max((max(v["raw"], v["mintlify"]) for v in results_by_tier.values()), default=1)
    html = ""
    for tier in [1, 2, 3]:
        if tier not in results_by_tier:
            continue
        v = results_by_tier[tier]
        raw_pct = v["raw"] / max_val * 100 if max_val > 0 else 0
        mint_pct = v["mintlify"] / max_val * 100 if max_val > 0 else 0
        html += f"""
        <div class="bar-container">
          <div class="bar-label"><span class="name">Tier {tier} — Raw</span><span class="val">{v['raw']:.1f}s</span></div>
          <div class="bar-track"><div class="bar-fill bar-raw" style="width:{raw_pct:.1f}%"></div></div>
        </div>
        <div class="bar-container">
          <div class="bar-label"><span class="name">Tier {tier} — Mintlify</span><span class="val">{v['mintlify']:.1f}s</span></div>
          <div class="bar-track"><div class="bar-fill bar-mintlify" style="width:{mint_pct:.1f}%"></div></div>
        </div>
        """
    return html


def build_bars_accuracy(results_by_tier: dict) -> str:
    html = ""
    for tier in [1, 2, 3]:
        if tier not in results_by_tier:
            continue
        v = results_by_tier[tier]
        raw_pct = v["raw_score"] / 2.0 * 100
        mint_pct = v["mintlify_score"] / 2.0 * 100
        html += f"""
        <div class="bar-container">
          <div class="bar-label"><span class="name">Tier {tier} — Raw</span><span class="val">{v['raw_score']:.2f}/2</span></div>
          <div class="bar-track"><div class="bar-fill bar-raw" style="width:{raw_pct:.1f}%"></div></div>
        </div>
        <div class="bar-container">
          <div class="bar-label"><span class="name">Tier {tier} — Mintlify</span><span class="val">{v['mintlify_score']:.2f}/2</span></div>
          <div class="bar-track"><div class="bar-fill bar-mintlify" style="width:{mint_pct:.1f}%"></div></div>
        </div>
        """
    return html


def generate_report(data: dict, output_path: Path):
    summary = data["summary"]
    results = data["results"]

    from collections import defaultdict
    tier_data = defaultdict(lambda: {"raw_t": [], "mint_t": [], "raw_scores": [], "mint_scores": []})
    for r in results:
        t = r["tier"]
        tier_data[t]["raw_t"].append(r["raw"]["elapsed_s"])
        tier_data[t]["mint_t"].append(r["mintlify"]["elapsed_s"])
        tier_data[t]["raw_scores"].append(r["scores"].get("raw_score", 0))
        tier_data[t]["mint_scores"].append(r["scores"].get("mintlify_score", 0))

    results_by_tier = {}
    for t, d in tier_data.items():
        n = len(d["raw_t"])
        results_by_tier[t] = {
            "raw": sum(d["raw_t"]) / n,
            "mintlify": sum(d["mint_t"]) / n,
            "raw_score": sum(d["raw_scores"]) / n,
            "mintlify_score": sum(d["mint_scores"]) / n,
        }

    rows_html = ""
    for r in results:
        raw_t = r["raw"]["elapsed_s"]
        mint_t = r["mintlify"]["elapsed_s"]
        t_delta = raw_t - mint_t
        t_delta_pct = f"-{t_delta/raw_t*100:.0f}%" if raw_t > 0 and t_delta > 0 else (f"+{abs(t_delta)/raw_t*100:.0f}%" if t_delta < 0 else "0%")
        raw_score = r["scores"].get("raw_score", 0)
        mint_score = r["scores"].get("mintlify_score", 0)
        score_delta = mint_score - raw_score

        rows_html += f"""
        <tr>
          <td><span class="tier-badge tier-{r['tier']}">T{r['tier']}</span> {r['id']}</td>
          <td title="{r['question']}">{r['question'][:65]}...</td>
          <td>{raw_t:.1f}s</td>
          <td>{mint_t:.1f}s</td>
          <td class="{delta_class(t_delta)}">{t_delta_pct}</td>
          <td><span class="score {score_class(raw_score)}">{raw_score}/2</span></td>
          <td><span class="score {score_class(mint_score)}">{mint_score}/2</span></td>
          <td class="{delta_class(score_delta)}">{'+' if score_delta > 0 else ''}{score_delta}</td>
        </tr>
        """

    raw_t = summary["raw"]["avg_elapsed_s"]
    mint_t = summary["mintlify"]["avg_elapsed_s"]
    time_red = summary.get("time_reduction_pct", 0)
    score_imp = summary.get("score_improvement", 0)

    html = HTML_TEMPLATE.format(
        date=summary["experiment_date"][:10],
        model=summary["model"],
        n_questions=summary["n_questions"],
        time_reduction=f"{time_red:+.0f}" if time_red != 0 else "0",
        raw_avg_time=f"{raw_t:.1f}",
        mint_avg_time=f"{mint_t:.1f}",
        score_improvement=f"{score_imp:+.2f}",
        raw_accuracy=summary["raw"]["accuracy"]["avg_score"],
        mint_accuracy=summary["mintlify"]["accuracy"]["avg_score"],
        correct_pct=summary["mintlify"]["accuracy"]["pct_correct"],
        raw_correct_pct=summary["raw"]["accuracy"]["pct_correct"],
        time_bars=build_bars_time(results_by_tier),
        accuracy_bars=build_bars_accuracy(results_by_tier),
        rows=rows_html,
    )

    output_path.write_text(html)
    print(f"Report generated: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results_file")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"Error: {results_path} not found")
        sys.exit(1)

    with open(results_path) as f:
        data = json.load(f)

    output_path = results_path.with_suffix(".html")
    generate_report(data, output_path)

    if args.open:
        import subprocess
        subprocess.run(["open", str(output_path)])


if __name__ == "__main__":
    main()
