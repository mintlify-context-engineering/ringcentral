"""
Generate an HTML dashboard from experiment results.

Usage:
    python report.py results/experiment_20240101_120000.json
    python report.py results/experiment_20240101_120000.json --open
"""

import argparse
import html
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
  .tier-4 {{ background: #4a1f2f; color: #fb7185; }}
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
  <div class="subtitle">Raw Source vs. Docs MCP — {date} &nbsp;·&nbsp; Model: {model} &nbsp;·&nbsp; {n_questions} questions</div>
</div>

<div class="container">

  <div class="note">
    <strong>Experiment design:</strong> The same model answers each question across benchmark access layers.
    <strong>Condition A (Raw):</strong> Agent navigates a sanitized source workspace that excludes benchmark files and prior results.
    <strong>Condition B (Mintlify):</strong> Agent navigates the live RingCentral docs MCP from an empty workspace.
    Scores reflect blind-judged answer accuracy against ground truth. Invalid rows are excluded from aggregates.
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
      <div class="sublabel">{raw_accuracy} → {mint_accuracy} avg score ({n_scored} scored)</div>
    </div>
    <div class="kpi">
      <div class="value purple">{correct_pct}%</div>
      <div class="label">Correct (Mintlify)</div>
      <div class="sublabel">vs {raw_correct_pct}% for Raw Source</div>
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
          <th>Status</th>
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
    if s is None:
        return "score-0"
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
    for tier in sorted(results_by_tier):
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
    for tier in sorted(results_by_tier):
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


def _condition_palette(index: int) -> str:
    return ["#0684bc", "#ff7a00", "#5aa0ce", "#9ca8b6", "#7c3aed"][index % 5]


# Canonical condition display order: least docs → more docs → structured docs.
CONDITION_ORDER = ["no_markdown", "raw", "mintlify", "raw_mintlify"]

# RingCentral-branded, executive-friendly labels + consistent colors per condition key.
KEY_LABEL = {
    "no_markdown": "Code only",
    "raw": "Code + Markdown",
    "mintlify": "Mintlify docs (MCP)",
    "raw_mintlify": "Everything combined",
}
KEY_SHORT = {
    "no_markdown": "Code only",
    "raw": "Code + Markdown",
    "mintlify": "Mintlify (MCP)",
    "raw_mintlify": "Everything",
}
KEY_COLOR = {
    "no_markdown": "#9ca8b6",
    "raw": "#5aa0ce",
    "mintlify": "#ff7a00",
    "raw_mintlify": "#0684bc",
}

# Difficulty-tier labels (easy → hard).
TIER_NAME = {1: "Quick facts", 2: "How-to &amp; code", 3: "Reasoning &amp; comparison", 4: "Not in the docs"}
TIER_SUB = {1: "single-fact lookups", 2: "task-oriented with code", 3: "judgment across products", 4: "not in the docs"}
TIER_CHIP = {1: "#0684bc", 2: "#0a8f5b", 3: "#7c3aed", 4: "#d23b3b"}
TIER_BADGE = {
    1: ("#eaf5fb", "#0684bc"),
    2: ("#e8f6ef", "#0a8f5b"),
    3: ("#f1ebfb", "#7c3aed"),
    4: ("#fdecec", "#d23b3b"),
}


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0


def _cond_style(condition: dict, index: int):
    """Return (label, short_label, color) for a condition, honoring overrides."""
    key = condition["key"]
    label = condition.get("label_friendly") or KEY_LABEL.get(key) or condition.get("label") or key
    short = condition.get("short_friendly") or KEY_SHORT.get(key) or label
    color = condition.get("color") or KEY_COLOR.get(key) or _condition_palette(index)
    return label, short, color


def _score_chip(score) -> str:
    if score is None:
        return '<span class="score s0">n/a</span>'
    return f'<span class="score s{score}">{score}/2</span>'


REPORT_CSS = """
  :root{
    --rc-blue:#0684BC;--rc-blue-dark:#045d85;--rc-navy:#062b45;--rc-orange:#ff7a00;
    --ink:#0b2238;--muted:#5b6b7b;--line:#e3e9ef;--line-soft:#eef2f6;--bg:#f4f7fa;--card:#ffffff;
    --good:#0a8f5b;--warn:#c9820a;--bad:#d23b3b;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.55;-webkit-font-smoothing:antialiased;}
  .header{background:linear-gradient(120deg,var(--rc-navy) 0%,var(--rc-blue-dark) 55%,var(--rc-blue) 100%);color:#fff;padding:40px 0 36px;}
  .header .inner{max-width:1120px;margin:0 auto;padding:0 32px;}
  .brand{display:flex;align-items:center;gap:12px;margin-bottom:22px;}
  .brand .logo{display:inline-flex;align-items:center;gap:9px;font-weight:800;letter-spacing:-.2px;font-size:17px;}
  .brand .dot{width:13px;height:13px;border-radius:50%;background:var(--rc-orange);box-shadow:0 0 0 4px rgba(255,122,0,.25);}
  .brand .sep{opacity:.45;font-weight:400;}
  .brand .tag{margin-left:auto;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.25);padding:5px 13px;border-radius:999px;font-size:12px;font-weight:600;letter-spacing:.3px;}
  .header h1{font-size:34px;line-height:1.18;font-weight:800;max-width:880px;letter-spacing:-.5px;}
  .header h1 .accent{color:#ffd9b3;}
  .runmeta{margin-top:22px;display:flex;flex-wrap:wrap;gap:8px;}
  .runmeta span{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.18);border-radius:7px;padding:6px 11px;font-size:12.5px;color:#eaf3f9;}
  .runmeta b{color:#fff;font-weight:700;}
  .container{max-width:1120px;margin:0 auto;padding:0 32px;}
  section{margin:48px auto;}
  .eyebrow{font-size:12px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;color:var(--rc-blue);margin-bottom:8px;}
  h2.title{font-size:24px;font-weight:800;letter-spacing:-.3px;margin-bottom:6px;}
  .section-sub{color:var(--muted);font-size:15px;max-width:760px;margin-bottom:24px;}
  .takeaway{margin-top:-30px;position:relative;z-index:2;}
  .takeaway .card{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 18px 40px -24px rgba(6,43,69,.35);padding:28px 30px;}
  .stat-row{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;}
  .stat{border:1px solid var(--line);border-radius:12px;padding:18px 20px;background:linear-gradient(180deg,#fbfdff,#f5f9fc);}
  .stat .big{font-size:36px;font-weight:800;letter-spacing:-1px;color:var(--rc-navy);line-height:1;}
  .stat .big .arrow{color:var(--rc-orange);}
  .stat .cap{margin-top:9px;font-size:13.5px;color:var(--muted);}
  .grid-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;}
  .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:22px;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;}
  .panel{padding:22px 24px;}
  .panel h3{font-size:15px;font-weight:800;margin-bottom:14px;letter-spacing:-.2px;}
  .layer{padding:20px;border-radius:14px;border:1px solid var(--line);background:var(--card);position:relative;overflow:hidden;}
  .layer::before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--lc);}
  .layer .step{font-size:11px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;color:var(--muted);}
  .layer .name{font-size:16px;font-weight:800;margin:4px 0 8px;display:flex;align-items:center;gap:8px;}
  .layer .swatch{width:11px;height:11px;border-radius:3px;background:var(--lc);flex:none;}
  .layer .meta{margin-top:12px;font-size:12.5px;color:var(--ink);font-weight:600;}
  .layer.is-winner{box-shadow:0 0 0 2px var(--rc-blue) inset;}
  .pill{display:inline-block;font-size:10.5px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;padding:2px 8px;border-radius:999px;background:#eaf5fb;color:var(--rc-blue);margin-left:6px;vertical-align:middle;}
  .pill.orange{background:#fff0e3;color:#c85e00;}
  .tcard{padding:18px 20px;border-radius:14px;border:1px solid var(--line);background:var(--card);}
  .tcard .badge{display:inline-block;font-size:12px;font-weight:800;padding:3px 10px;border-radius:7px;margin-bottom:10px;}
  .tcard .name{font-weight:800;font-size:15px;margin-bottom:6px;}
  .tcard .count{margin-top:10px;font-size:12px;color:var(--muted);}
  .tcard .count b{color:var(--ink);}
  .bar{margin-bottom:13px;}
  .bar:last-child{margin-bottom:0;}
  .bar .lab{display:flex;justify-content:space-between;gap:14px;font-size:13px;margin-bottom:5px;}
  .bar .lab .n{color:var(--ink);display:flex;align-items:center;gap:7px;}
  .bar .lab .n .sw{width:10px;height:10px;border-radius:3px;flex:none;}
  .bar .lab .v{font-weight:700;color:var(--ink);}
  .track{height:11px;background:#eef2f6;border-radius:6px;overflow:hidden;}
  .fill{height:100%;border-radius:6px;}
  .legend{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:8px;}
  .legend .item{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--ink);}
  .legend .sw{width:12px;height:12px;border-radius:3px;}
  .tier-head{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:6px;}
  .tier-head .chip{font-size:13px;font-weight:800;color:#fff;padding:5px 12px;border-radius:8px;}
  .tier-head h3{font-size:20px;font-weight:800;letter-spacing:-.3px;}
  .tier-head .qn{font-size:13px;color:var(--muted);margin-left:auto;}
  .tier-block{margin-bottom:40px;}
  .mini-grid{display:grid;grid-template-columns:1.1fr 1.4fr;gap:20px;margin-bottom:18px;}
  table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;}
  th{background:#f7fafc;text-align:left;font-size:11.5px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);padding:11px 13px;border-bottom:1px solid var(--line);font-weight:800;}
  th .csw{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;vertical-align:middle;}
  td{padding:11px 13px;font-size:13px;border-bottom:1px solid var(--line-soft);vertical-align:top;color:var(--ink);}
  tr:last-child td{border-bottom:none;}
  tbody tr:hover td{background:#fafcfe;}
  td.q{color:var(--ink);font-weight:600;max-width:320px;}
  .qid{font-size:11px;font-weight:800;color:var(--muted);letter-spacing:.3px;}
  .cell .t{font-size:12px;color:var(--muted);}
  .cell .tok{font-size:11.5px;color:#8593a1;}
  .score{display:inline-block;margin-top:5px;padding:2px 9px;border-radius:6px;font-weight:800;font-size:12px;}
  .s2{background:#e4f6ee;color:var(--good);}
  .s1{background:#fdf2dc;color:var(--warn);}
  .s0{background:#fbe6e6;color:var(--bad);}
  .footer{border-top:1px solid var(--line);margin-top:56px;padding:28px 0 40px;}
  .footer .inner{max-width:1120px;margin:0 auto;padding:0 32px;color:var(--muted);font-size:12.5px;}
  .footer .legal{margin-top:8px;font-size:11px;color:#9aa7b3;}
  @media (max-width:900px){.header h1{font-size:26px;}.grid-2,.stat-row,.mini-grid{grid-template-columns:1fr;}.container,.header .inner,.footer .inner{padding-left:18px;padding-right:18px;}table{display:block;overflow-x:auto;white-space:nowrap;}}
"""


def generate_multi_condition_report(data: dict, output_path: Path):
    summary = data["summary"]
    results = data["results"]
    provider = summary.get("provider", "cursor")
    native_tokens = provider == "openrouter"
    token_key = "total_tokens" if native_tokens else "total_tokens_est"
    avg_token_key = "avg_total_tokens" if native_tokens else "avg_total_tokens_est"
    conditions = sorted(
        summary["conditions"],
        key=lambda c: CONDITION_ORDER.index(c["key"]) if c["key"] in CONDITION_ORDER else len(CONDITION_ORDER),
    )
    valid_results = [r for r in results if r.get("valid", r.get("scores") is not None)]
    tiers = sorted({r["tier"] for r in valid_results})

    # ----- derive / backfill per-condition metrics -----
    for condition in conditions:
        key = condition["key"]
        metric = summary[key]
        score_key = f"{key}_score"
        correct_count = metric.get("correct_count")
        if correct_count is None:
            correct_count = sum(1 for r in valid_results if (r.get("scores") or {}).get(score_key) == 2)
            metric["correct_count"] = correct_count
        total_tokens_est = metric.get("total_tokens_est")
        if total_tokens_est is None:
            total_tokens_est = sum(r.get(key, {}).get("total_tokens_est", 0) for r in valid_results)
            metric["total_tokens_est"] = total_tokens_est
        total_tokens = metric.get("total_tokens")
        if total_tokens is None:
            total_tokens = sum(r.get(key, {}).get("total_tokens", r.get(key, {}).get("total_tokens_est", 0)) for r in valid_results)
            metric["total_tokens"] = total_tokens
        if "tokens_per_correct_answer_est" not in metric:
            metric["tokens_per_correct_answer_est"] = round(total_tokens_est / correct_count, 2) if correct_count else None
        if "tokens_per_correct_answer" not in metric:
            metric["tokens_per_correct_answer"] = round(total_tokens / correct_count, 2) if correct_count else None
        if "openrouter_cost_per_correct_answer" not in metric:
            cost = metric.get("openrouter_cost", 0)
            metric["openrouter_cost_per_correct_answer"] = round(cost / correct_count, 8) if correct_count else None
        if "tier_normalized_avg_score" not in metric:
            tier_scores = []
            for tier in tiers:
                tier_rows = [r for r in valid_results if r["tier"] == tier]
                if not tier_rows:
                    continue
                scores = [(r.get("scores") or {}).get(score_key, 0) for r in tier_rows]
                tier_scores.append(_avg(scores))
            metric["tier_normalized_avg_score"] = round(_avg(tier_scores), 2) if tier_scores else 0

    from collections import defaultdict

    tier_data = defaultdict(lambda: {c["key"]: {"times": [], "scores": [], "tokens": []} for c in conditions})
    for r in valid_results:
        tier = r["tier"]
        for condition in conditions:
            key = condition["key"]
            tier_data[tier][key]["scores"].append((r.get("scores") or {}).get(f"{key}_score", 0))
            if r.get(key, {}).get("ok", True):
                tier_data[tier][key]["times"].append(r.get(key, {}).get("elapsed_s", 0))
                tier_data[tier][key]["tokens"].append(r.get(key, {}).get(token_key, 0))

    def cost_of(metric):
        return metric.get("tokens_per_correct_answer") if native_tokens else metric.get("tokens_per_correct_answer_est")

    styles = [_cond_style(c, i) for i, c in enumerate(conditions)]

    # ----- headline takeaway stats -----
    pct = {c["key"]: summary[c["key"]]["accuracy"]["pct_correct"] for c in conditions}
    baseline_key = conditions[0]["key"]
    best_acc_key = max(pct, key=lambda k: pct[k])
    acc0, acc_best = pct[baseline_key], pct[best_acc_key]
    costs = {c["key"]: cost_of(summary[c["key"]]) for c in conditions}
    valid_costs = [v for v in costs.values() if v]
    winner_key = max(conditions, key=lambda c: summary[c["key"]].get("tier_normalized_avg_score", 0))["key"]
    cheapest_key = min((k for k, v in costs.items() if v), key=lambda k: costs[k], default=None)
    dearest_key = max((k for k, v in costs.items() if v), key=lambda k: costs[k], default=None)

    stat1 = f"{acc0:.0f}% <span class='arrow'>&rarr;</span> {acc_best:.0f}%"
    stat2 = f"{(max(valid_costs) / min(valid_costs)):.1f}&times;" if len(valid_costs) >= 2 and min(valid_costs) else "&mdash;"
    stat3 = f"{(acc_best / acc0):.1f}&times;" if acc0 else "&mdash;"

    # ----- access-layer cards -----
    layer_cards = ""
    for i, (condition, (label, _short, color)) in enumerate(zip(conditions, styles)):
        key = condition["key"]
        is_winner = key == winner_key
        step = f"Layer {i + 1}"
        if i == 0:
            step += " &middot; Baseline"
        if is_winner:
            step = f"Layer {i + 1} &middot; Best overall"
        pill = ' <span class="pill">winner</span>' if is_winner else (' <span class="pill orange">via MCP</span>' if key == "mintlify" else "")
        notes = [f"{pct[key]:.0f}% correct"]
        if key == dearest_key:
            notes.append("most expensive")
        elif key == cheapest_key:
            notes.append("cheapest per answer")
        layer_cards += f"""
      <div class="layer{' is-winner' if is_winner else ''}" style="--lc:{color}">
        <div class="step">{step}</div>
        <div class="name"><span class="swatch"></span>{label}{pill}</div>
        <div class="meta">{' &middot; '.join(notes)}</div>
      </div>"""

    # ----- tier explainer cards -----
    tier_cards = ""
    for tier in tiers:
        bg, fg = TIER_BADGE.get(tier, ("#eef2f6", "#5b6b7b"))
        name = TIER_NAME.get(tier, f"Tier {tier}")
        count = sum(1 for r in valid_results if r["tier"] == tier)
        tier_cards += f"""
      <div class="tcard">
        <span class="badge" style="background:{bg};color:{fg};">Tier {tier}</span>
        <div class="name">{name}</div>
        <div class="count"><b>{count} question{'s' if count != 1 else ''}</b></div>
      </div>"""

    # ----- headline charts (accuracy % + cost per correct) -----
    legend = "".join(
        f'<div class="item"><span class="sw" style="background:{color}"></span>{label}</div>'
        for (label, _s, color) in styles
    )
    acc_bars = ""
    for condition, (label, _s, color) in zip(conditions, styles):
        p = pct[condition["key"]]
        acc_bars += f'<div class="bar"><div class="lab"><span class="n"><span class="sw" style="background:{color}"></span>{label}</span><span class="v">{p:.1f}%</span></div><div class="track"><div class="fill" style="width:{p:.1f}%;background:{color}"></div></div></div>'
    max_cost = max(valid_costs, default=1)
    cost_bars = ""
    for condition, (label, _s, color) in zip(conditions, styles):
        c = costs[condition["key"]]
        w = (c / max_cost * 100) if c and max_cost else 0
        disp = f"{'' if native_tokens else '~'}{c:,.0f}" if c else "n/a"
        cost_bars += f'<div class="bar"><div class="lab"><span class="n"><span class="sw" style="background:{color}"></span>{label}</span><span class="v">{disp}</span></div><div class="track"><div class="fill" style="width:{w:.1f}%;background:{color}"></div></div></div>'

    # ----- per-tier detail blocks -----
    results_by_tier = defaultdict(list)
    for r in results:
        results_by_tier[r["tier"]].append(r)

    tier_blocks = ""
    for tier in tiers:
        chip_color = TIER_CHIP.get(tier, "#0684bc")
        name = TIER_NAME.get(tier, f"Tier {tier}")
        sub = TIER_SUB.get(tier, "")
        count = sum(1 for r in valid_results if r["tier"] == tier)
        qn = f"{count} question{'s' if count != 1 else ''}" + (f" &middot; {sub}" if sub else "")

        # score + token mini-bars
        score_avgs = {c["key"]: _avg(tier_data[tier][c["key"]]["scores"]) for c in conditions}
        tok_avgs = {c["key"]: _avg(tier_data[tier][c["key"]]["tokens"]) for c in conditions}
        max_tok = max(tok_avgs.values(), default=1) or 1
        score_bars = ""
        token_bars = ""
        for condition, (label, _s, color) in zip(conditions, styles):
            sv = score_avgs[condition["key"]]
            score_bars += f'<div class="bar"><div class="lab"><span class="n"><span class="sw" style="background:{color}"></span>{label}</span><span class="v">{sv:.2f}</span></div><div class="track"><div class="fill" style="width:{max(sv / 2 * 100, 1):.1f}%;background:{color}"></div></div></div>'
            tv = tok_avgs[condition["key"]]
            token_bars += f'<div class="bar"><div class="lab"><span class="n"><span class="sw" style="background:{color}"></span>{label}</span><span class="v">{tv:,.0f}</span></div><div class="track"><div class="fill" style="width:{(tv / max_tok * 100):.1f}%;background:{color}"></div></div></div>'

        # table headers + rows
        headers = "".join(
            f'<th><span class="csw" style="background:{color}"></span>{short}</th>'
            for (_label, short, color) in styles
        )
        rows = ""
        for r in results_by_tier[tier]:
            q_full = html.escape(r["question"])
            q_short = html.escape(r["question"][:110] + ("\u2026" if len(r["question"]) > 110 else ""))
            cells = ""
            scores = r.get("scores") or {}
            for condition in conditions:
                key = condition["key"]
                elapsed = r.get(key, {}).get("elapsed_s", 0)
                tok = r.get(key, {}).get(token_key, 0)
                chip = _score_chip(scores.get(f"{key}_score"))
                cells += f'<td class="cell"><div class="t">{elapsed:.1f}s</div><div class="tok">{"" if native_tokens else "~"}{tok:,.0f} tok</div>{chip}</td>'
            rows += f'<tr><td class="q"><div class="qid">{html.escape(r["id"])}</div>{q_short}</td>{cells}</tr>'

        tier_blocks += f"""
    <div class="tier-block">
      <div class="tier-head">
        <span class="chip" style="background:{chip_color}">Tier {tier}</span>
        <h3>{name}</h3>
        <span class="qn">{qn}</span>
      </div>
      <div class="mini-grid">
        <div class="card panel"><h3>Average score (out of 2)</h3>{score_bars}</div>
        <div class="card panel"><h3>Average tokens used</h3>{token_bars}</div>
      </div>
      <table>
        <thead><tr><th>Question</th>{headers}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""

    date = html.escape(summary.get("experiment_date", "")[:10])
    model = html.escape(summary.get("model", "—"))
    cost_unit = "tokens" if native_tokens else "tokens (est.)"

    rendered_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Documentation Quality vs. AI Accuracy — RingCentral Benchmark</title>
<style>{REPORT_CSS}</style>
</head>
<body>
<div class="header">
  <div class="inner">
    <div class="brand">
      <span class="logo"><span class="dot"></span>RingCentral <span class="sep">&times;</span> Mintlify</span>
      <span class="tag">AI Documentation Benchmark</span>
    </div>
    <h1>Documentation quality vs. <span class="accent">AI accuracy</span></h1>
    <div class="runmeta">
      <span>Date <b>{date}</b></span>
      <span>Model <b>{model}</b></span>
      <span>Questions <b>{summary.get('n_questions', len(results))}</b></span>
      <span>Access layers tested <b>{len(conditions)}</b></span>
      <span>Difficulty tiers <b>{len(tiers)}</b></span>
    </div>
  </div>
</div>
<div class="container">
  <section class="takeaway">
    <div class="card">
      <div class="stat-row">
        <div class="stat"><div class="big">{stat1}</div><div class="cap">Accuracy: {KEY_SHORT.get(baseline_key, baseline_key).lower()} &rarr; best layer</div></div>
        <div class="stat"><div class="big">{stat2}</div><div class="cap">Lower cost per correct answer</div></div>
        <div class="stat"><div class="big">{stat3}</div><div class="cap">More correct answers</div></div>
      </div>
    </div>
  </section>

  <section>
    <div class="eyebrow">Access layers tested</div>
    <h2 class="title">The access layers</h2>
    <div class="grid-cards">{layer_cards}
    </div>
  </section>

  <section>
    <div class="eyebrow">Question difficulty</div>
    <h2 class="title">The question tiers (easy &rarr; hard)</h2>
    <div class="grid-cards">{tier_cards}
    </div>
  </section>

  <section>
    <div class="eyebrow">Headline results</div>
    <h2 class="title">Accuracy &amp; cost by access layer</h2>
    <div class="legend">{legend}</div>
    <div class="grid-2">
      <div class="card panel"><h3>Accuracy — % of questions fully correct</h3>{acc_bars}</div>
      <div class="card panel"><h3>Cost per correct answer — {cost_unit}</h3>{cost_bars}</div>
    </div>
  </section>

  <section>
    <div class="eyebrow">Per-tier detail</div>
    <h2 class="title">Results by tier</h2>
    <p class="section-sub">Each cell: response time &middot; tokens used &middot; score — <span class="score s2">2/2</span> correct &middot; <span class="score s1">1/2</span> partial &middot; <span class="score s0">0/2</span> incorrect.</p>
    {tier_blocks}
  </section>
</div>
<div class="footer">
  <div class="inner">
    RingCentral Context Engineering Benchmark &middot; {date} &middot; {model} &middot; {summary.get('n_questions', len(results))} questions
    <div class="legal">RingCentral is a registered trademark of RingCentral, Inc.</div>
  </div>
</div>
</body>
</html>"""

    output_path.write_text(rendered_html)
    print(f"Report generated: {output_path}")



def generate_report(data: dict, output_path: Path):
    summary = data["summary"]
    if "conditions" in summary:
        return generate_multi_condition_report(data, output_path)

    # Legacy two-condition (raw vs mintlify) results: adapt to the unified design.
    if "raw" in summary and "mintlify" in summary:
        summary["conditions"] = [
            {"key": "raw", "label_friendly": "Raw source", "short_friendly": "Raw source", "color": "#5aa0ce"},
            {"key": "mintlify", "label_friendly": "Mintlify docs (MCP)", "short_friendly": "Mintlify (MCP)", "color": "#0684bc"},
        ]
        return generate_multi_condition_report(data, output_path)

    results = data["results"]
    valid_results = [r for r in results if r.get("valid", r.get("scores") is not None)]

    from collections import defaultdict
    tier_data = defaultdict(lambda: {"raw_t": [], "mint_t": [], "raw_scores": [], "mint_scores": []})
    for r in valid_results:
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
        scores = r.get("scores") or {}
        raw_score = scores.get("raw_score")
        mint_score = scores.get("mintlify_score")
        score_delta = mint_score - raw_score if raw_score is not None and mint_score is not None else None
        question = html.escape(r["question"])
        short_question = html.escape(r["question"][:65] + ("..." if len(r["question"]) > 65 else ""))
        status = html.escape(r.get("status", "ok"))
        raw_score_text = f"{raw_score}/2" if raw_score is not None else "n/a"
        mint_score_text = f"{mint_score}/2" if mint_score is not None else "n/a"
        score_delta_text = (
            f"{'+' if score_delta > 0 else ''}{score_delta}"
            if score_delta is not None
            else "n/a"
        )

        rows_html += f"""
        <tr>
          <td><span class="tier-badge tier-{r['tier']}">T{r['tier']}</span> {r['id']}</td>
          <td title="{question}">{short_question}</td>
          <td>{raw_t:.1f}s</td>
          <td>{mint_t:.1f}s</td>
          <td class="{delta_class(t_delta)}">{t_delta_pct}</td>
          <td><span class="score {score_class(raw_score)}">{raw_score_text}</span></td>
          <td><span class="score {score_class(mint_score)}">{mint_score_text}</span></td>
          <td class="{delta_class(score_delta or 0)}">{score_delta_text}</td>
          <td>{status}</td>
        </tr>
        """

    raw_t = summary["raw"]["avg_elapsed_s"]
    mint_t = summary["mintlify"]["avg_elapsed_s"]
    time_red = summary.get("time_reduction_pct", 0)
    score_imp = summary.get("score_improvement", 0)

    rendered_html = HTML_TEMPLATE.format(
        date=summary["experiment_date"][:10],
        model=summary["model"],
        n_questions=summary["n_questions"],
        n_scored=summary.get("n_scored", summary["n_questions"]),
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

    output_path.write_text(rendered_html)
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
