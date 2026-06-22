"""
LLM judge for scoring agent answers against ground truth.

Uses the Cursor SDK to score both answers in a single call.
Scores on a 0-2 scale:
  0 = Wrong or missing key facts
  1 = Partially correct (has some key facts but missing important ones)
  2 = Correct and complete
"""

import json
import os
import tempfile
from pathlib import Path

JUDGE_API_KEY = os.environ.get("CURSOR_API_KEY", "")

JUDGE_PROMPT_TEMPLATE = """You are an expert judge evaluating AI agent answers about the RingCentral API.
Score each answer on a 0-2 scale based on accuracy and completeness compared to the ground truth.

Scoring rubric:
  2 = Correct and complete. All key facts present, no significant errors.
  1 = Partially correct. Has some key facts but missing important details or has minor errors.
  0 = Wrong or unhelpful. Missing most key facts, significantly incorrect, or no answer.

Question: {question}

Ground Truth: {ground_truth}

Key Facts to Check: {key_facts}

--- Answer A (Raw Monorepo Agent) ---
{answer_raw}

--- Answer B (Mintlify Docs Agent) ---
{answer_mintlify}

Score both answers. Return ONLY a JSON object (no other text, no markdown):
{{"raw_score": <0|1|2>, "raw_reasoning": "<one sentence>", "mintlify_score": <0|1|2>, "mintlify_reasoning": "<one sentence>"}}"""


def score(
    question: str,
    ground_truth: str,
    key_facts: list,
    answer_raw: str,
    answer_mintlify: str,
) -> dict:
    """
    Score both answers against ground truth using a Cursor SDK agent.

    Returns:
        {
            raw_score: 0|1|2,
            mintlify_score: 0|1|2,
            raw_reasoning: str,
            mintlify_reasoning: str,
        }
    """
    from cursor_sdk import Agent, LocalAgentOptions

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        ground_truth=ground_truth,
        key_facts=", ".join(key_facts),
        answer_raw=answer_raw or "(no answer)",
        answer_mintlify=answer_mintlify or "(no answer)",
    )

    # Use a temp dir as the cwd — the judge doesn't need any codebase
    with tempfile.TemporaryDirectory() as tmpdir:
        with Agent.create(
            model="composer-2.5",
            api_key=JUDGE_API_KEY,
            local=LocalAgentOptions(cwd=tmpdir),
        ) as agent:
            run = agent.send(prompt)
            text = run.text().strip()

    # Extract JSON from the response
    try:
        # Strip markdown code fences if present
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        # Find the JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        result = json.loads(text.strip())
        return {
            "raw_score": int(result.get("raw_score", 0)),
            "raw_reasoning": result.get("raw_reasoning", ""),
            "mintlify_score": int(result.get("mintlify_score", 0)),
            "mintlify_reasoning": result.get("mintlify_reasoning", ""),
        }
    except (json.JSONDecodeError, KeyError, ValueError):
        # Fallback: try to parse scores from plain text
        raw_score = 1 if "answer a" in text.lower() and "correct" in text.lower() else 0
        mint_score = 1 if "answer b" in text.lower() and "correct" in text.lower() else 0
        return {
            "raw_score": raw_score,
            "mintlify_score": mint_score,
            "raw_reasoning": "Parse failed",
            "mintlify_reasoning": "Parse failed",
            "raw_judge_response": text[:200],
        }
