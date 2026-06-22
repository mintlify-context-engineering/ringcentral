# RingCentral Context Engineering Benchmark

Measures the token efficiency, accuracy, and speed gains that Mintlify's structured docs provide over raw monorepo navigation.

## What It Tests

**Condition A — Raw Monorepo**: An AI agent navigates the actual RingCentral monorepo using `list_directory`, `read_file`, and `find_files` tools. It has to discover where docs live, read scattered READMEs, and synthesize across repos.

**Condition B — Mintlify Docs**: The same Cursor model is connected to the live Mintlify-hosted RingCentral docs MCP server (`ringcentral.mintlify.app/mcp`). It runs in an empty working directory, so its only tools are the docs portal's semantic search and page-read tools. It gets directly to the answer.

Both conditions use the **same Cursor model** and the **same `CURSOR_API_KEY`** — the only variable is the toolset (raw monorepo files vs. structured docs MCP).

## Three Metrics

| Metric | What It Shows |
|--------|--------------|
| **Token reduction** | Fewer tokens to reach the same answer = lower cost |
| **Accuracy improvement** | Structured docs surface the right answer more reliably |
| **Step reduction** | Fewer tool calls = faster time-to-answer |

## Setup

Requires Python 3.10+ and a [Cursor API key](https://cursor.com/dashboard/integrations). That single key powers all three roles: the raw monorepo agent, the Mintlify-docs agent (Cursor SDK + Mintlify MCP), and the judge. No Anthropic key is needed for the main benchmark.

```bash
# Use the included venv (Python 3.11)
uv venv .venv --python 3.11
uv pip install -r requirements.txt --python .venv
source .venv/bin/activate

# Add your key to the .env file (already created, just paste your key)
cp .env.example .env   # if .env doesn't exist yet
# then edit .env and set CURSOR_API_KEY=crsr_...
```

`run_experiment.py` auto-loads `benchmark/.env`, so you don't need to `export` anything. (You still can if you prefer: `export CURSOR_API_KEY=crsr_...`.)

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

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — finds the doc structure that makes MCP lookup more token-efficient than raw monorepo navigation, for any question.

**No API keys required.** The loop is fully deterministic — it measures `chars_read` as a proxy for input tokens.

```bash
# Full audit + coverage check (no API keys needed)
python autoresearch_loop.py

# Phase 1 only: scan all 202 raw docs, find everything missing from structured_docs/
python autoresearch_loop.py --audit

# Phase 2 only: measure chars needed to cover all key facts per question
python autoresearch_loop.py --coverage

# Show all missing facts verbosely
python autoresearch_loop.py --audit --verbose
```

### Phase 1: Comprehensive Doc Audit

Walks all 202 raw doc files, extracts API endpoints/headings/concepts, compares to `structured_docs/`, and reports:
- Topic areas with zero structured coverage
- Missing API endpoints per topic
- Recommended new structured doc files to create

### Phase 2: Benchmark Coverage Check

For each of the 20 benchmark questions, measures:
- `chars_read` by structured docs agent (search → chunk)
- `chars_read` by raw monorepo agent (file scanning)
- Which key facts are still missing from structured docs

**Current results (after autoresearch optimization):**

| Metric | Before | After |
|--------|--------|-------|
| Questions fully covered | 11/20 (55%) | **20/20 (100%)** |
| Avg chars — structured | 5,125 | **3,375** |
| Avg chars — raw baseline | 30,725 | 30,725 |
| Token reduction | 83.3% | **89.0%** |
| Structured doc files | 5 | **13** |
| Topic areas covered | 5/16 | 14+/16 |

See [`DOC_STRUCTURE_GUIDE.md`](DOC_STRUCTURE_GUIDE.md) for the generalizable principles behind the winning format.

## Benchmark Questions

20 questions across 3 tiers:

| Tier | Count | What It Tests |
|------|-------|---------------|
| **Tier 1** | 7 | Single-fact lookups (base URL, status codes, install commands) |
| **Tier 2** | 7 | Multi-step how-tos (JWT auth flow, webhook creation, pagination) |
| **Tier 3** | 6 | Cross-repo synthesis (SDK matrix, auth flow choice, full implementation) |

Tier 3 is where the gap is largest — raw monorepo agents often give partial answers or get lost across repos.

## Expected Results

### Main benchmark (run_experiment.py) — Condition A vs B accuracy

| | Raw Monorepo | Mintlify Live MCP | Delta |
|--|-------------|------------------|-------|
| Avg score (0-2) | 1.85 | 1.70 | −0.15 |
| % fully correct | 85% | 70% | −15% |

> **Why Mintlify currently lags**: The live MCP at `ringcentral.mintlify.app/mcp` returns
> incomplete answers (e.g. partial base URL, missing Go SDK JWT example). The raw agent
> has the advantage of reading actual source code with ground-truth exact values.
>
> The fix: structure the hosted docs in **answer-first format** (see below). Once the MCP
> docs match the `structured_docs/` quality, Mintlify wins on both accuracy and tokens.

### Autoresearch loop (autoresearch_loop.py) — chars_read efficiency

| Condition | Avg chars/question | % vs Raw | Coverage |
|-----------|-------------------|---------|---------|
| Raw baseline (file scanning) | 30,725 | — | ~85% |
| **Structured docs (answer-first)** | **3,375** | **−89%** | **100%** |

**89% fewer chars read, 100% key-fact coverage** — structured docs win on both metrics. Tier 3 questions show the largest reduction (raw scans 5-15 files; structured hits 1-3 docs).

## File Structure

```
benchmark/
├── .env                    # CURSOR_API_KEY (gitignored — paste your key here)
├── .env.example            # Template for .env
├── questions.json          # 20 benchmark questions with ground truth
├── DOC_STRUCTURE_GUIDE.md  # Generalizable principles for AI-agent-optimized docs
├── structured_docs/        # Local docs in answer-first format (used by autoresearch_loop.py)
│   ├── index.json          # Searchable doc index with semantic tags
│   ├── authentication.md
│   ├── rate-limits.md
│   ├── webhooks.md
│   ├── api-basics.md
│   └── sdks.md
├── agents/
│   ├── raw_agent.py        # Cursor SDK + raw monorepo files (Condition A)
│   └── mintlify_agent.py   # Cursor SDK + Mintlify-hosted docs MCP (Condition B)
├── judge.py                # LLM judge (scores 0-2, uses Cursor SDK)
├── autoresearch_loop.py    # Doc structure optimizer (Anthropic SDK, tracks input_tokens)
├── report.py               # HTML dashboard generator
├── run_experiment.py       # Main orchestrator (accuracy + timing)
└── results/                # Output JSONs and HTML reports
```
