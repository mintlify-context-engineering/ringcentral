# RingCentral Context Engineering Benchmark

Measures the token efficiency, accuracy, and speed gains that Mintlify's structured docs provide over raw monorepo navigation.

## What It Tests

**Condition A — Raw Monorepo**: An AI agent navigates the actual RingCentral monorepo using `list_directory`, `read_file`, and `find_files` tools. It has to discover where docs live, read scattered READMEs, and synthesize across repos.

**Condition B — Mintlify Docs**: The same agent uses a structured documentation portal — `search_docs` (semantic search) and `read_doc` (clean, cross-linked pages). It gets directly to the answer.

## Three Metrics

| Metric | What It Shows |
|--------|--------------|
| **Token reduction** | Fewer tokens to reach the same answer = lower cost |
| **Accuracy improvement** | Structured docs surface the right answer more reliably |
| **Step reduction** | Fewer tool calls = faster time-to-answer |

## Setup

Requires Python 3.10+ and a [Cursor API key](https://cursor.com/settings).

```bash
# Use the included venv (Python 3.11 + cursor-sdk)
uv venv .venv --python 3.11
uv pip install cursor-sdk --python .venv
source .venv/bin/activate

export CURSOR_API_KEY=crsr_...
```

## Run the Experiment

```bash
# Full benchmark (all 20 questions, ~30-45 min)
python run_experiment.py

# Quick smoke test — Tier 1 only (7 questions, ~10 min)
python run_experiment.py --tier 1

# Specific questions
python run_experiment.py --ids T1-01 T2-01 T3-05

# Verbose mode (shows agent progress in real time)
python run_experiment.py --tier 1 --verbose

# Dry run (no API calls, just show the plan)
python run_experiment.py --dry-run
```

## Generate the Dashboard

```bash
python report.py results/experiment_20240101_120000.json --open
```

This creates an HTML dashboard at the same path showing:
- Three headline KPIs (token reduction, accuracy improvement, step reduction)
- Per-tier bar charts
- Per-question breakdown table

## Optimize Doc Structure (autoresearch loop)

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — iterates over different doc structure configs to find the optimal balance of accuracy vs. token cost.

```bash
python autoresearch_loop.py

# With specific questions and multiple rounds
python autoresearch_loop.py --questions T1-02 T2-01 T3-01 --rounds 2
```

Tests four configs:
- **minimal**: Small chunks, no code examples — lowest token cost, potentially lower accuracy
- **standard**: Medium chunks with examples — balanced default
- **full**: Full doc content — highest accuracy, most tokens
- **summary-first**: Summaries only, let the agent decide to read_doc — depends on agent behavior

Outputs the Pareto-optimal config for the accuracy/token tradeoff.

## Benchmark Questions

20 questions across 3 tiers:

| Tier | Count | What It Tests |
|------|-------|---------------|
| **Tier 1** | 7 | Single-fact lookups (base URL, status codes, install commands) |
| **Tier 2** | 7 | Multi-step how-tos (JWT auth flow, webhook creation, pagination) |
| **Tier 3** | 6 | Cross-repo synthesis (SDK matrix, auth flow choice, full implementation) |

Tier 3 is where the gap is largest — raw monorepo agents often give partial answers or get lost across repos.

## Expected Results

Based on the doc structure quality difference:

| | Raw | Mintlify | Delta |
|--|-----|---------|-------|
| Avg tokens/request | ~4000-6000 | ~800-1500 | −70-80% |
| Avg score (0-2) | ~1.0-1.3 | ~1.6-1.9 | +0.5-0.7 |
| Avg tool calls | ~6-9 | ~2-3 | −60-70% |

Tier 3 questions will show the biggest gap in both accuracy and token cost.

## File Structure

```
benchmark/
├── questions.json          # 20 benchmark questions with ground truth
├── structured_docs/        # Mintlify condition — clean structured docs
│   ├── index.json          # Searchable doc index
│   ├── authentication.md
│   ├── rate-limits.md
│   ├── webhooks.md
│   ├── api-basics.md
│   └── sdks.md
├── agents/
│   ├── raw_agent.py        # Navigates raw monorepo
│   └── mintlify_agent.py   # Uses structured docs
├── judge.py                # LLM judge (scores 0-2)
├── autoresearch_loop.py    # Doc structure optimizer
├── report.py               # HTML dashboard generator
├── run_experiment.py       # Main orchestrator
└── results/                # Output JSONs and HTML reports
```
