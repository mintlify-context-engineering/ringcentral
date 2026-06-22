"""
autoresearch_loop.py

Goal: find everything in the raw docs that isn't in the structured docs,
so that any question a developer could ask is answerable via the MCP.

Two phases — both require zero API keys:

  Phase 1  COMPREHENSIVE AUDIT
           Walk all 202 raw doc files. Extract every API endpoint, concept,
           heading, and key term. Compare to structured_docs/. Report every
           topic area and fact that's missing.

  Phase 2  BENCHMARK COVERAGE CHECK
           For the benchmark questions, measure how many chars the
           structured search needs to surface all key facts, vs raw files.
           Shows whether adding missing content closes the efficiency gap.

Run:
    python autoresearch_loop.py              # full audit + coverage check
    python autoresearch_loop.py --audit      # audit only
    python autoresearch_loop.py --coverage   # coverage check only
    python autoresearch_loop.py --verbose    # show every missing fact
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

DOCS_ROOT = Path(__file__).parent / "structured_docs"
RAW_DOCS_ROOT = Path(__file__).parent.parent / "docs"
QUESTIONS_FILE = Path(__file__).parent / "questions.json"
RESULTS_DIR = Path(__file__).parent / "results"

# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

# API paths: /restapi/v1.0/..., /rcvideo/v2/..., /webinar/v1/...
RE_API_PATH = re.compile(
    r"(?<![a-zA-Z`])((?:/restapi|/rcvideo|/webinar|/ai)[/\w\-{}~?=&]+)",
    re.IGNORECASE,
)
# Markdown headers
RE_HEADER = re.compile(r"^(#{1,3})\s+(.+)", re.MULTILINE)
# HTTP methods with paths
RE_HTTP_METHOD = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(\/[^\s`\)\"']+)", re.IGNORECASE)
# Install commands
RE_INSTALL = re.compile(
    r"(pip3?\s+install|npm\s+install|gem\s+install|composer\s+require|go\s+get|dotnet\s+add\s+package)\s+([\w@\-/\.]+)",
    re.IGNORECASE,
)
# Important inline code terms (header names, grant types, param names)
RE_INLINE_CODE = re.compile(r"`([^`\n]{3,60})`")


def extract_facts(content: str, path: Path) -> dict:
    """Extract structured facts from a markdown/mdx file."""
    facts = {
        "api_paths": [],
        "http_methods": [],   # (METHOD, path)
        "headers": [],        # markdown H1/H2/H3
        "install_cmds": [],
        "inline_terms": [],
        "char_count": len(content),
    }

    facts["api_paths"] = list(dict.fromkeys(
        m.group(1) for m in RE_API_PATH.finditer(content)
        if len(m.group(1)) > 5
    ))
    facts["http_methods"] = list(dict.fromkeys(
        f"{m.group(1).upper()} {m.group(2)}"
        for m in RE_HTTP_METHOD.finditer(content)
    ))
    facts["headers"] = [
        {"level": len(m.group(1)), "text": m.group(2).strip()}
        for m in RE_HEADER.finditer(content)
    ]
    facts["install_cmds"] = list(dict.fromkeys(
        f"{m.group(1)} {m.group(2)}"
        for m in RE_INSTALL.finditer(content)
    ))
    facts["inline_terms"] = list(dict.fromkeys(
        m.group(1).strip()
        for m in RE_INLINE_CODE.finditer(content)
        if "/" in m.group(1) or "-" in m.group(1) or len(m.group(1).split()) <= 3
    ))[:40]  # cap per file

    return facts


def topic_from_path(path: Path) -> str:
    """e.g. docs/voice/call-log.mdx → 'voice'"""
    parts = path.relative_to(RAW_DOCS_ROOT).parts
    return parts[0] if len(parts) > 1 else "root"


# ---------------------------------------------------------------------------
# Phase 1: Comprehensive audit
# ---------------------------------------------------------------------------

def build_raw_inventory() -> dict:
    """
    Walk every .md/.mdx file in docs/ and extract its facts.
    Returns a nested dict: topic → {file_path: facts}
    """
    inventory = defaultdict(dict)
    for path in sorted(RAW_DOCS_ROOT.rglob("*.md")) + sorted(RAW_DOCS_ROOT.rglob("*.mdx")):
        try:
            content = path.read_text(errors="ignore")
        except Exception:
            continue
        topic = topic_from_path(path)
        inventory[topic][str(path.relative_to(RAW_DOCS_ROOT))] = extract_facts(content, path)
    return dict(inventory)


def build_structured_content() -> str:
    """Concatenate all structured doc content for gap checking."""
    parts = []
    for path in DOCS_ROOT.glob("*.md"):
        parts.append(path.read_text(errors="ignore"))
    return "\n".join(parts).lower()


def audit_gaps(raw_inventory: dict, structured_text: str, verbose: bool = False) -> dict:
    """
    For each topic/file in the raw inventory, find facts not present in
    structured_text. Returns a gap report grouped by topic.
    """
    gaps = {}

    for topic, files in sorted(raw_inventory.items()):
        topic_gaps = {
            "file_count": len(files),
            "missing_api_paths": [],
            "missing_http_methods": [],
            "missing_headings": [],
            "missing_install_cmds": [],
            "covered_by_structured": False,
        }

        all_headings = []
        all_api_paths = []
        all_http_methods = []
        all_install_cmds = []

        for file_path, facts in files.items():
            all_headings.extend(h["text"] for h in facts["headers"] if h["level"] <= 2)
            all_api_paths.extend(facts["api_paths"])
            all_http_methods.extend(facts["http_methods"])
            all_install_cmds.extend(facts["install_cmds"])

        # Deduplicate
        all_headings   = list(dict.fromkeys(all_headings))
        all_api_paths  = list(dict.fromkeys(all_api_paths))
        all_http_methods = list(dict.fromkeys(all_http_methods))
        all_install_cmds = list(dict.fromkeys(all_install_cmds))

        # Check coverage
        for heading in all_headings:
            if heading.lower() not in structured_text:
                topic_gaps["missing_headings"].append(heading)

        for path in all_api_paths:
            if path.lower() not in structured_text:
                topic_gaps["missing_api_paths"].append(path)

        for method in all_http_methods:
            # Check just the path portion
            _, _, path_part = method.partition(" ")
            if path_part.lower() not in structured_text:
                topic_gaps["missing_http_methods"].append(method)

        for cmd in all_install_cmds:
            if cmd.lower() not in structured_text:
                topic_gaps["missing_install_cmds"].append(cmd)

        # Topic is "covered" if more than half the H1/H2 headings appear
        covered_headings = len(all_headings) - len(topic_gaps["missing_headings"])
        topic_gaps["heading_coverage_pct"] = (
            round(covered_headings / len(all_headings) * 100) if all_headings else 0
        )
        topic_gaps["covered_by_structured"] = topic_gaps["heading_coverage_pct"] >= 50

        # Summarise missing HTTP methods by unique path (drop query strings)
        clean_methods = []
        seen = set()
        for m in topic_gaps["missing_http_methods"]:
            base = m.split("?")[0]
            if base not in seen:
                seen.add(base)
                clean_methods.append(base)
        topic_gaps["missing_http_methods"] = clean_methods

        gaps[topic] = topic_gaps

    return gaps


def print_audit_report(gaps: dict, verbose: bool = False) -> None:
    # Separate fully missing vs partial vs covered
    fully_missing = {t: g for t, g in gaps.items() if g["heading_coverage_pct"] == 0}
    partial       = {t: g for t, g in gaps.items() if 0 < g["heading_coverage_pct"] < 50}
    covered       = {t: g for t, g in gaps.items() if g["heading_coverage_pct"] >= 50}

    total_raw_files = sum(g["file_count"] for g in gaps.values())
    structured_count = len(list(DOCS_ROOT.glob("*.md")))

    print(f"\n{'═'*68}")
    print("PHASE 1 — COMPREHENSIVE DOC AUDIT")
    print(f"{'═'*68}")
    print(f"  Raw source files  : {total_raw_files} files across {len(gaps)} topic areas")
    print(f"  Structured docs   : {structured_count} files")
    print()

    # ── Fully missing topics ──
    print(f"  TOPIC AREAS WITH ZERO COVERAGE  ({len(fully_missing)} of {len(gaps)})")
    print(f"  {'─'*60}")
    for topic, g in sorted(fully_missing.items(), key=lambda x: -x[1]["file_count"]):
        print(f"\n  ✗  {topic:<20}  ({g['file_count']} source files)")
        if g["missing_headings"]:
            shown = g["missing_headings"][:6 if not verbose else 99]
            for h in shown:
                print(f"       · {h}")
            if not verbose and len(g["missing_headings"]) > 6:
                print(f"       … +{len(g['missing_headings'])-6} more headings")
        if g["missing_http_methods"][:3]:
            print(f"       API endpoints not documented:")
            for m in g["missing_http_methods"][:4 if not verbose else 99]:
                print(f"         {m}")
            if not verbose and len(g["missing_http_methods"]) > 4:
                print(f"         … +{len(g['missing_http_methods'])-4} more")

    # ── Partial topics ──
    if partial:
        print(f"\n\n  PARTIALLY COVERED TOPICS  ({len(partial)} of {len(gaps)})")
        print(f"  {'─'*60}")
        for topic, g in sorted(partial.items()):
            print(f"\n  ~  {topic:<20}  {g['heading_coverage_pct']}% of headings found")
            if g["missing_headings"]:
                shown = g["missing_headings"][:4 if not verbose else 99]
                for h in shown:
                    print(f"       · {h}")
                if not verbose and len(g["missing_headings"]) > 4:
                    print(f"       … +{len(g['missing_headings'])-4} more")

    # ── Well covered ──
    print(f"\n\n  WELL COVERED TOPICS  ({len(covered)} of {len(gaps)})")
    print(f"  {'─'*60}")
    for topic, g in sorted(covered.items()):
        remaining_apis = len(g["missing_api_paths"])
        api_note = f"  ({remaining_apis} API paths not yet in structured docs)" if remaining_apis else ""
        print(f"  ✓  {topic:<20}  {g['heading_coverage_pct']}% heading coverage{api_note}")

    # ── Recommended new structured doc files ──
    print(f"\n\n{'═'*68}")
    print("RECOMMENDED NEW STRUCTURED DOC FILES")
    print(f"{'═'*68}")
    print("""
  Priority 1 — these topics have the most raw content and zero structured coverage:
""")
    priority = sorted(fully_missing.items(), key=lambda x: -x[1]["file_count"])
    for topic, g in priority:
        # Suggest a doc filename and key things to include
        endpoints = g["missing_http_methods"][:3]
        ep_str = ", ".join(endpoints) if endpoints else "no REST endpoints detected"
        print(f"  structured_docs/{topic}.md")
        print(f"    Source: docs/{topic}/ ({g['file_count']} files)")
        print(f"    Key endpoints: {ep_str}")
        if g["missing_headings"]:
            print(f"    Topics to cover: {', '.join(g['missing_headings'][:4])}")
        print()

    print("""  Priority 2 — fill gaps in existing structured docs:
""")
    for topic, g in sorted(partial.items()):
        print(f"  structured_docs/{topic}.md  (extend with: {', '.join(g['missing_headings'][:3])})")


# ---------------------------------------------------------------------------
# Phase 2: Benchmark coverage check (same as before, no API keys)
# ---------------------------------------------------------------------------

def load_index() -> list[dict]:
    with open(DOCS_ROOT / "index.json") as f:
        return json.load(f)["docs"]


def score_doc(doc: dict, query: str) -> float:
    query_lower = query.lower()
    score = 0.0
    for tag in doc.get("tags", []):
        if tag.lower() in query_lower:
            score += 10
    for word in query_lower.split():
        if word in doc["title"].lower():
            score += 5
        if word in doc.get("summary", "").lower():
            score += 2
    return score


def measure_coverage(question: str, key_facts: list[str], chunk_size: int = 2500, max_results: int = 3) -> dict:
    docs = load_index()
    scored = sorted(
        [(d, score_doc(d, question)) for d in docs],
        key=lambda x: x[1], reverse=True,
    )
    facts_remaining = set(f.lower() for f in key_facts)
    chars_read = 0

    for doc, _ in scored[:max_results]:
        content = (DOCS_ROOT / doc["file"]).read_text(errors="ignore") if (DOCS_ROOT / doc["file"]).exists() else ""
        chunk = content[:chunk_size]
        chars_read += len(chunk)
        for fact in list(facts_remaining):
            if fact in chunk.lower():
                facts_remaining.discard(fact)
        if not facts_remaining:
            break

    return {
        "chars_read": chars_read,
        "facts_covered": len(key_facts) - len(facts_remaining),
        "facts_total": len(key_facts),
        "missing": sorted(facts_remaining),
        "complete": not facts_remaining,
    }


def raw_monorepo_measure(question: str, key_facts: list[str], max_files: int = 12) -> dict:
    query_words = set(question.lower().split())
    candidates = []
    for path in RAW_DOCS_ROOT.rglob("*.md"):
        path_lower = str(path).lower()
        relevance = sum(1 for w in query_words if w in path_lower)
        candidates.append((path, relevance))
    for path in RAW_DOCS_ROOT.rglob("*.mdx"):
        path_lower = str(path).lower()
        relevance = sum(1 for w in query_words if w in path_lower)
        candidates.append((path, relevance))
    candidates.sort(key=lambda x: -x[1])

    facts_remaining = set(f.lower() for f in key_facts)
    chars_read = 0
    files_read = 0

    for path, _ in candidates[:max_files]:
        try:
            content = path.read_text(errors="ignore")[:8_000]
        except Exception:
            continue
        chars_read += len(content)
        files_read += 1
        for fact in list(facts_remaining):
            if fact in content.lower():
                facts_remaining.discard(fact)
        if not facts_remaining:
            break

    return {
        "chars_read": chars_read,
        "files_read": files_read,
        "facts_covered": len(key_facts) - len(facts_remaining),
        "missing": sorted(facts_remaining),
        "complete": not facts_remaining,
    }


def run_coverage_check(questions: list[dict]) -> None:
    print(f"\n{'═'*68}")
    print("PHASE 2 — BENCHMARK COVERAGE CHECK")
    print(f"{'═'*68}")
    print(f"  Metric: chars surfaced before all literal key-fact strings appear in context")
    print()

    structured_totals = []
    raw_totals = []
    gaps_by_question = []

    print(f"  {'ID':<8} {'Structured':>12} {'Raw':>12}  {'Coverage':>10}  Missing facts")
    print(f"  {'─'*64}")

    for q in questions:
        s = measure_coverage(q["question"], q["key_facts"])
        r = raw_monorepo_measure(q["question"], q["key_facts"])
        structured_totals.append(s["chars_read"])
        raw_totals.append(r["chars_read"])

        cov = f"{s['facts_covered']}/{s['facts_total']}"
        flag = "✓" if s["complete"] else "✗"
        missing_str = ", ".join(f'"{m}"' for m in s["missing"][:2])
        if len(s["missing"]) > 2:
            missing_str += f" +{len(s['missing'])-2}"

        print(f"  {flag} {q['id']:<6}  {s['chars_read']:>10,}  {r['chars_read']:>10,}  {cov:>10}  {missing_str}")

        if s["missing"]:
            gaps_by_question.append({"id": q["id"], "missing": s["missing"]})

    avg_s = sum(structured_totals) / len(structured_totals)
    avg_r = sum(raw_totals) / len(raw_totals)
    reduction = (1 - avg_s / avg_r) * 100 if avg_r else 0
    complete = sum(1 for q in questions if not measure_coverage(q["question"], q["key_facts"])["missing"])

    print(f"\n  {'─'*64}")
    print(f"  Avg structured  : {avg_s:>8,.0f} chars")
    print(f"  Avg raw         : {avg_r:>8,.0f} chars")
    print(f"  Context reduction : {reduction:>5.1f}%  (structured vs raw)")
    print(f"  Literal coverage: {complete}/{len(questions)} questions with all key-fact strings present")

    if gaps_by_question:
        print(f"\n  MISSING FACTS TO ADD TO STRUCTURED DOCS")
        print(f"  {'─'*48}")
        for item in gaps_by_question:
            print(f"\n  {item['id']}")
            for fact in item["missing"]:
                print(f"    ✗  \"{fact}\"")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Audit structured docs completeness — no API keys required"
    )
    parser.add_argument("--audit",    action="store_true", help="Run Phase 1 only")
    parser.add_argument("--coverage", action="store_true", help="Run Phase 2 only")
    parser.add_argument("--verbose",  action="store_true", help="Show all missing facts, not just top N")
    parser.add_argument("--questions", nargs="+", default=None)
    args = parser.parse_args()

    run_audit    = args.audit    or not args.coverage
    run_coverage = args.coverage or not args.audit

    if run_audit:
        print("Scanning raw docs...")
        raw_inventory  = build_raw_inventory()
        structured_txt = build_structured_content()
        gaps           = audit_gaps(raw_inventory, structured_txt, verbose=args.verbose)
        print_audit_report(gaps, verbose=args.verbose)

    if run_coverage:
        with open(QUESTIONS_FILE) as f:
            all_q = json.load(f)["questions"]
        questions = [q for q in all_q if q["id"] in args.questions] if args.questions else all_q
        run_coverage_check(questions)


if __name__ == "__main__":
    main()
