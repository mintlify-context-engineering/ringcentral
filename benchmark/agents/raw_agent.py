"""
Raw monorepo agent — Condition A (baseline).

Uses the Cursor SDK to navigate the full RingCentral monorepo.
Represents what a developer / AI agent experiences without a structured docs portal:
a sprawling repo of 40+ sub-repos, scattered READMEs, no unified search.
"""

import os
import time
from pathlib import Path

MONOREPO_ROOT = str(Path(__file__).parent.parent.parent)
API_KEY = os.environ.get("CURSOR_API_KEY", "")

QUESTION_PREFIX = (
    "You are navigating the RingCentral open-source monorepo to answer a developer question. "
    "The monorepo contains 40+ sub-repositories across docs/, sdks/, chatbots/, embeddable/, "
    "integrations/, crm/, video/, and voice/ directories. "
    "Use the files available to you to answer accurately and concisely.\n\n"
    "Question: "
)


def run(question: str, model: str = "composer-2.5", verbose: bool = False) -> dict:
    """
    Run the raw-monorepo Cursor agent on a question.

    Returns:
        {
            answer: str,
            elapsed_s: float,
            response_length: int,
        }
    """
    from cursor_sdk import Agent, LocalAgentOptions

    t0 = time.time()
    try:
        with Agent.create(
            model=model,
            api_key=API_KEY,
            local=LocalAgentOptions(cwd=MONOREPO_ROOT),
        ) as agent:
            if verbose:
                print(f"  [raw] agent created in {time.time()-t0:.1f}s, sending question...")
            run_result = agent.send(QUESTION_PREFIX + question)
            answer = run_result.text()
    except Exception as e:
        answer = f"ERROR: {e}"

    elapsed = time.time() - t0
    if verbose:
        print(f"  [raw] done in {elapsed:.1f}s, response_len={len(answer)}")

    return {
        "answer": answer.strip(),
        "elapsed_s": round(elapsed, 2),
        "response_length": len(answer),
    }
