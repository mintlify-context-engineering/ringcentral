"""
No-Markdown source agent — Condition B.

Uses the Cursor SDK to navigate the RingCentral source tree after removing the
Markdown documentation layer. The agent still gets source code, examples,
package metadata, JSON/YAML configs, tests, and inline code comments, but it
does not get docs/ or Markdown-like files such as README.md.
"""

import os
import tempfile
import time
from pathlib import Path

from agents import context_metrics

REPO_ROOT = Path(__file__).parent.parent.parent
API_KEY = os.environ.get("CURSOR_API_KEY", "")

SOURCE_ENTRIES = (
    "sdks",
    "chatbots",
    "embeddable",
    "integrations",
    "crm",
    "video",
    "voice",
    "infrastructure",
)

MARKDOWN_SUFFIXES = {".md", ".mdx", ".markdown"}
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "benchmark", "results"}

QUESTION_PREFIX = (
    "You are navigating the RingCentral open-source monorepo to answer a developer question. "
    "The Markdown documentation layer has been removed: docs/ is unavailable, and README.md, "
    "*.md, *.mdx, and other Markdown files are absent. You still have access to source code, "
    "examples, package metadata, configs, tests, and inline code comments. Use the files "
    "available to you to answer accurately and concisely.\n\n"
    "Question: "
)


def _is_markdown_file(path: Path) -> bool:
    return path.suffix.lower() in MARKDOWN_SUFFIXES


def _populate_workspace(workspace: Path) -> None:
    for entry in SOURCE_ENTRIES:
        source_root = REPO_ROOT / entry
        if not source_root.exists():
            continue

        if source_root.is_file():
            if not _is_markdown_file(source_root):
                os.symlink(source_root, workspace / entry)
            continue

        dest_root = workspace / entry
        dest_root.mkdir(parents=True, exist_ok=True)

        for current_root, dirs, files in os.walk(source_root):
            current = Path(current_root)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            rel_dir = current.relative_to(source_root)
            dest_dir = dest_root / rel_dir
            dest_dir.mkdir(parents=True, exist_ok=True)

            for filename in files:
                source_file = current / filename
                if _is_markdown_file(source_file):
                    continue
                os.symlink(source_file, dest_dir / filename)


def run(question: str, model: str = "composer-2.5", verbose: bool = False) -> dict:
    """Run the source-without-Markdown Cursor agent on a question."""
    t0 = time.time()
    answer = ""
    error = None
    metrics = context_metrics.empty_metrics()

    try:
        from cursor_sdk import Agent, LocalAgentOptions

        with tempfile.TemporaryDirectory(prefix="rc-no-markdown-benchmark-") as tmpdir:
            workspace = Path(tmpdir)
            _populate_workspace(workspace)

            with Agent.create(
                model=model,
                api_key=API_KEY,
                local=LocalAgentOptions(cwd=str(workspace), setting_sources=[]),
            ) as agent:
                if verbose:
                    print(f"  [no-markdown] filtered workspace={workspace}, sending question...")
                run_result = agent.send(QUESTION_PREFIX + question)
                answer = run_result.text()
                metrics = context_metrics.metrics_from_run(run_result, answer)
    except Exception as e:
        error = str(e)
        answer = f"ERROR: {error}"

    elapsed = time.time() - t0
    if verbose:
        print(f"  [no-markdown] done in {elapsed:.1f}s, response_len={len(answer)}")

    return {
        "answer": answer.strip(),
        "elapsed_s": round(elapsed, 2),
        "response_length": len(answer),
        "ok": error is None,
        "error": error,
        **metrics,
    }
