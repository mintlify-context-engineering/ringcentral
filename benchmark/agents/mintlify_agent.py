"""
Mintlify-structured docs agent — Condition B.

Uses the Cursor SDK pointed at the structured_docs/ directory only.
Represents what a developer / AI agent experiences with a Mintlify documentation portal:
5 clean, cross-linked, semantic docs instead of 40+ raw repositories.
"""

import os
import time
from pathlib import Path

STRUCTURED_DOCS_ROOT = str(Path(__file__).parent.parent / "structured_docs")
API_KEY = os.environ.get("CURSOR_API_KEY", "")

QUESTION_PREFIX = (
    "You are using the RingCentral documentation portal (powered by Mintlify). "
    "The portal contains well-organized, cross-linked reference documentation. "
    "Use the documentation files available to you to answer accurately and concisely.\n\n"
    "Question: "
)


def run(question: str, model: str = "composer-2.5", verbose: bool = False) -> dict:
    """
    Run the Mintlify-structured-docs Cursor agent on a question.

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
            local=LocalAgentOptions(cwd=STRUCTURED_DOCS_ROOT),
        ) as agent:
            if verbose:
                print(f"  [mintlify] agent created in {time.time()-t0:.1f}s, sending question...")
            run_result = agent.send(QUESTION_PREFIX + question)
            answer = run_result.text()
    except Exception as e:
        answer = f"ERROR: {e}"

    elapsed = time.time() - t0
    if verbose:
        print(f"  [mintlify] done in {elapsed:.1f}s, response_len={len(answer)}")

    return {
        "answer": answer.strip(),
        "elapsed_s": round(elapsed, 2),
        "response_length": len(answer),
    }
