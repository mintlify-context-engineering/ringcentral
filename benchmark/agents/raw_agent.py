"""
Raw source agent — Condition A (baseline).

Uses the Cursor SDK to navigate a sanitized view of the RingCentral source tree.
The benchmark directory is deliberately excluded so the baseline cannot read
questions.json, optimized structured docs, prior results, or local secrets.
"""

import os
import tempfile
import time
from pathlib import Path

from agents import context_metrics

REPO_ROOT = Path(__file__).parent.parent.parent
API_KEY = os.environ.get("CURSOR_API_KEY", "")
SOURCE_ENTRIES = (
    "docs",
    "sdks",
    "chatbots",
    "embeddable",
    "integrations",
    "crm",
    "video",
    "voice",
    "infrastructure",
    "README.md",
)

QUESTION_PREFIX = (
    "You are navigating the RingCentral open-source monorepo to answer a developer question. "
    "The monorepo contains 40+ sub-repositories across docs/, sdks/, chatbots/, embeddable/, "
    "integrations/, crm/, video/, and voice/ directories. "
    "Use the files available to you to answer accurately and concisely.\n\n"
    "Question: "
)


def run(question: str, model: str = "composer-2.5", verbose: bool = False) -> dict:
    """Run the raw-source Cursor agent on a question.

    Returns:
        {
            answer: str,
            elapsed_s: float,
            response_length: int,
            ok: bool,
            error: str | None,
        }
    """
    t0 = time.time()
    answer = ""
    error = None
    metrics = context_metrics.empty_metrics()

    try:
        from cursor_sdk import Agent, LocalAgentOptions

        with tempfile.TemporaryDirectory(prefix="rc-raw-benchmark-") as tmpdir:
            workspace = Path(tmpdir)
            for entry in SOURCE_ENTRIES:
                source = REPO_ROOT / entry
                if source.exists():
                    os.symlink(source, workspace / entry, target_is_directory=source.is_dir())

            with Agent.create(
                model=model,
                api_key=API_KEY,
                local=LocalAgentOptions(cwd=str(workspace), setting_sources=[]),
            ) as agent:
                if verbose:
                    print(f"  [raw] sanitized workspace={workspace}, sending question...")
                run_result = agent.send(QUESTION_PREFIX + question)
                answer = run_result.text()
                metrics = context_metrics.metrics_from_run(run_result, answer)
    except Exception as e:
        error = str(e)
        answer = f"ERROR: {error}"

    elapsed = time.time() - t0
    if verbose:
        print(f"  [raw] done in {elapsed:.1f}s, response_len={len(answer)}")

    return {
        "answer": answer.strip(),
        "elapsed_s": round(elapsed, 2),
        "response_length": len(answer),
        "ok": error is None,
        "error": error,
        **metrics,
    }
