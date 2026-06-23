# RingCentral Context Engineering Benchmark

Measures answer accuracy, response time, and response length for agents answering RingCentral developer questions under four information-access conditions: raw source without Markdown, raw source with Markdown, Mintlify docs MCP, and a hybrid Raw + Markdown + Mintlify MCP condition.

## What It Tests

**Condition A — Raw + Markdown**: An AI agent navigates a sanitized source workspace containing the public source/doc directories (`docs/`, `sdks/`, `chatbots/`, `embeddable/`, `integrations/`, `crm/`, `video/`, `voice/`, and `infrastructure/`). The workspace excludes `benchmark/`, prior results, local secrets, nested `.git` directories, dependency caches, generated build output, and optimized structured docs so the baseline cannot read the answer key or irrelevant generated artifacts.

**Condition B — Raw without Markdown**: The same model navigates a sanitized source workspace where the Markdown layer has been removed. `docs/` is unavailable, and Markdown-like files such as `README.md`, `*.md`, `*.mdx`, and `*.markdown` are omitted. Source code, examples, package metadata, JSON/YAML/config files, tests, and inline code comments remain available.

**Condition C — Mintlify MCP**: The same model is connected to the live Mintlify-hosted RingCentral docs MCP server (`ringcentral.mintlify.app/mcp`). In Cursor mode this is wired through Cursor's MCP support; in OpenRouter mode the benchmark exposes the live MCP tools to the OpenRouter tool loop and routes each tool call back to the same MCP endpoint.

**Condition D — Raw + Markdown + Mintlify MCP**: The same model gets both the sanitized Raw + Markdown workspace and the live Mintlify MCP. This tests whether structured docs improve answers when the agent can still fall back to source, examples, package metadata, tests, and repo-specific details.

By default, all conditions use the **same Cursor model** and the **same `CURSOR_API_KEY`**. You can also run through OpenRouter with `--provider openrouter`, where all conditions use the same OpenRouter model and `OPENROUTER_API_KEY`; in that mode the raw conditions use OpenRouter tool-calling over read-only local file tools, and both MCP conditions use the live Mintlify MCP through the local MCP bridge. The main variable remains the information layer: no Markdown, local Markdown, hosted structured docs through MCP, or combined local + MCP access.

## Main Runner Metrics

| Metric | What It Shows |
|--------|--------------|
| **Accuracy improvement** | Blind judge score delta against ground truth |
| **Response time** | Elapsed wall-clock time per answer |
| **Response length** | Output verbosity in characters |
| **Token spend** | Cursor mode: estimated tokens per question — context (tool-result bytes ÷ 4) + output (answer chars ÷ 4). OpenRouter mode: native usage totals and cost returned by OpenRouter |
| **Cost per correct answer** | Total condition tokens divided by fully correct answers; lower means the access layer produces correct answers more efficiently |
| **Tier-normalized score** | Average of per-tier accuracy scores, giving each tier equal weight regardless of question count |

Token estimates are captured automatically in Cursor mode: each agent measures the bytes of tool results (file reads, grep, MCP search results) returned by the **same** run it already makes, so there is no extra API cost. In OpenRouter mode, the runner stores OpenRouter's native `prompt_tokens`, `completion_tokens`, `total_tokens`, `openrouter_cost`, and `openrouter_generation_ids` in the result JSON. The standalone `measure_context.py` reports the exact byte breakdown by tool type for the Cursor SDK path. For deterministic structured-doc literal key-fact coverage and character-count checks, run `autoresearch_loop.py`.

## Setup

Requires Python 3.10+ and either a [Cursor API key](https://cursor.com/dashboard/integrations) or an OpenRouter API key. No Anthropic key is needed for the main benchmark.

```bash
# Use the included venv (Python 3.11)
uv venv .venv --python 3.11
uv pip install -r requirements.txt --python .venv
source .venv/bin/activate

# Add your key(s) to the .env file (already created, just paste your key)
cp .env.example .env   # if .env doesn't exist yet
# then edit .env and set CURSOR_API_KEY=crsr_... and/or OPENROUTER_API_KEY=sk-or-...
```

`run_experiment.py` auto-loads `benchmark/.env`, so you don't need to `export` anything. (You still can if you prefer.)

## Run the Experiment

```bash
# Full benchmark (all questions, ~30-60 min)
python run_experiment.py

# Run through OpenRouter for native token/cost tracking
python run_experiment.py --provider openrouter --model "~openai/gpt-latest"

# Cursor explicitly, matching the default behavior
python run_experiment.py --provider cursor --model composer-2.5

# Quick smoke test — Tier 1 only (20 questions)
python run_experiment.py --tier 1

# Quick OpenRouter smoke test
python run_experiment.py --provider openrouter --ids T1-01

# Source-only cross-repo questions — Tier 4 only
python run_experiment.py --tier 4

# Specific questions
python run_experiment.py --ids T1-01 T2-01 T3-05 T4-02

# Verbose mode (shows agent progress in real time)
python run_experiment.py --tier 1 --verbose

# Dry run (no API calls, just show the plan)
python run_experiment.py --dry-run
```

## Local Side-by-Side Demo

The demo runs a single prompt through two live OpenRouter tool loops in parallel:

- **Without MCP**: sanitized local RingCentral repo tools (`list_files`, `search_files`, `read_file`, etc.)
- **With MCP**: live Mintlify RingCentral docs MCP tools

It streams output, tool calls, tool-result previews, elapsed time, and token/cost counters into a localhost UI.

```bash
# From the repo root
benchmark/.venv/bin/python benchmark/demo/server.py

# Then open:
# http://127.0.0.1:8787
```

The server loads `benchmark/.env`, so make sure `OPENROUTER_API_KEY` is set there. You can optionally set `OPENROUTER_MODEL`; otherwise the demo defaults to `~openai/gpt-latest`.

## Generate the Dashboard

```bash
python report.py results/experiment_20240101_120000.json --open
```

This creates an HTML dashboard at the same path showing:
- Accuracy, response time, and correctness KPIs
- Tier-normalized score and token cost per correct answer
- Per-tier bar charts
- Per-question breakdown table

## Optimize Doc Structure (autoresearch loop)

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — finds the doc structure that makes MCP lookup use less retrieved context than raw source navigation, for any question.

**No API keys required.** The loop is fully deterministic — it measures `chars_read` as a rough proxy for tool-result context size and checks literal key-fact strings, not semantic answer quality or exact model input tokens.

```bash
# Full audit + coverage check (no API keys needed)
python autoresearch_loop.py

# Phase 1 only: scan all 202 raw docs, find everything missing from structured_docs/
python autoresearch_loop.py --audit

# Phase 2 only: measure chars needed to surface literal key facts per question
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

For each benchmark question, measures:
- `chars_read` by structured docs agent (search → chunk)
- `chars_read` by raw monorepo agent (file scanning)
- Which literal key-fact strings are still missing from structured docs

**Historical 20-question result (before the question set was expanded):**

| Metric | Before | After |
|--------|--------|-------|
| Questions with literal key-fact coverage | 11/20 (55%) | 20/20 (100%) |
| Avg chars — structured | 5,125 | **3,375** |
| Avg chars — raw baseline | 30,725 | 30,725 |
| Context reduction | 83.3% | **89.0%** |
| Structured doc files | 5 | **13** |
| Topic areas covered | 5/16 | 14+/16 |

See [`DOC_STRUCTURE_GUIDE.md`](DOC_STRUCTURE_GUIDE.md) for the generalizable principles behind the winning format.

## Benchmark Questions

80 questions across 4 tiers:

| Tier | Count | What It Tests |
|------|-------|---------------|
| **Tier 1** | 20 | Single-fact lookups (base URLs, status codes, install commands, endpoint paths, limits) |
| **Tier 2** | 20 | Multi-step how-tos (JWT/auth flows, webhook creation, pagination, messaging, video, webinar, bot setup) |
| **Tier 3** | 20 | Cross-repo and cross-doc synthesis (SDK matrix, auth flow choice, full implementation, product/API comparisons) |
| **Tier 4** | 20 | Source-only cross-repo questions whose answers live in package manifests, source modules, tests, or config rather than docs |

Tier 3 is where the gap is largest — raw monorepo agents often give partial answers or get lost across repos.
Tier 4 is intentionally harder for docs-only retrieval: it asks implementation and repo-composition questions that are not expected to be present in the public docs layer.

## Results

### Main benchmark (run_experiment.py) — three-condition accuracy

There is no hard-coded expected result. Use the newest valid `results/experiment_*.json` file produced by your own run. Runs with agent or judge failures are saved as `failed_experiment_*.json` and excluded from normal result naming.

### Autoresearch loop (autoresearch_loop.py) — chars_read efficiency

| Condition | Avg chars/question | % vs Raw | Coverage |
|-----------|-------------------|---------|---------|
| Raw baseline (file scanning) | 30,725 | — | ~85% |
| **Structured docs (answer-first)** | **3,375** | **−89%** | **100%** |

The current `questions.json` has more questions than the historical 20-question table above. Re-run `python autoresearch_loop.py --coverage` after changing the question set or structured docs.

## File Structure

```
benchmark/
├── .env                    # CURSOR_API_KEY (gitignored — paste your key here)
├── .env.example            # Template for .env
├── questions.json          # Benchmark questions with ground truth
├── DOC_STRUCTURE_GUIDE.md  # Generalizable principles for AI-agent-optimized docs
├── structured_docs/        # Local docs in answer-first format (used by autoresearch_loop.py)
│   ├── index.json          # Searchable doc index with semantic tags
│   ├── authentication.md
│   ├── rate-limits.md
│   ├── webhooks.md
│   ├── api-basics.md
│   └── ...
├── agents/
│   ├── raw_agent.py          # Cursor SDK + sanitized source workspace with Markdown (Condition A)
│   ├── no_markdown_agent.py  # Cursor SDK + source workspace with Markdown removed (Condition B)
│   └── mintlify_agent.py     # Cursor SDK + Mintlify-hosted docs MCP (Condition C)
├── judge.py                # LLM judge (scores 0-2, uses Cursor SDK)
├── autoresearch_loop.py    # Deterministic doc coverage optimizer (chars_read proxy)
├── report.py               # HTML dashboard generator
├── run_experiment.py       # Main orchestrator (accuracy + timing)
└── results/                # Output JSONs and HTML reports
```
