"""
Mintlify MCP agent — Condition B (treatment).

The run() function drives a Cursor SDK agent that is connected to the live
Mintlify-hosted RingCentral docs MCP server (ringcentral.mintlify.app/mcp).
It represents what a developer / AI agent experiences with a proper
documentation portal: semantic search over deployed, structured docs instead
of navigating 40+ raw repositories. Both conditions now run on the same
Cursor model and the same CURSOR_API_KEY — the only difference is the tools:
the raw agent gets the monorepo filesystem, this agent gets the docs MCP.

Module-level exports (TOOLS, TOOL_FUNCTIONS, _load_index, _score_doc, …)
are the local-file equivalents kept for autoresearch_loop.py compatibility.
"""

import json
import os
import tempfile
import time
from pathlib import Path

DOCS_ROOT = Path(__file__).parent.parent / "structured_docs"
MCP_URL = os.environ.get("MINTLIFY_MCP_URL", "https://ringcentral.mintlify.app/mcp")
MAX_TOOL_CALLS = 8

SYSTEM_PROMPT = (
    "You are an assistant helping developers use the RingCentral platform. "
    "You have access to the official RingCentral documentation via search and read tools. "
    "Search for relevant content, then answer accurately and concisely."
)

QUESTION_PREFIX = (
    "You are using the RingCentral documentation portal (powered by Mintlify). "
    "Use the search tools available to find documentation and answer the following question "
    "accurately. Include specific package names, install commands, and exact values (URLs, "
    "error codes, header names) when they are relevant to the answer.\n\nQuestion: "
)


# ---------------------------------------------------------------------------
# Local-file helpers — used by autoresearch_loop.py
# ---------------------------------------------------------------------------

def _load_index() -> list[dict]:
    index_path = DOCS_ROOT / "index.json"
    with open(index_path) as f:
        return json.load(f)["docs"]


def _score_doc(doc: dict, query: str) -> float:
    query_words = set(query.lower().split())
    score = 0.0
    for tag in doc.get("tags", []):
        if tag.lower() in query.lower():
            score += 10
    for word in query_words:
        if word in doc["title"].lower():
            score += 5
        if word in doc.get("summary", "").lower():
            score += 2
    return score


def _search_docs(query: str, max_results: int = 3) -> str:
    docs = _load_index()
    scored = sorted([(doc, _score_doc(doc, query)) for doc in docs], key=lambda x: x[1], reverse=True)
    results = []
    for doc, score in scored[:max_results]:
        file_path = DOCS_ROOT / doc["file"]
        content = file_path.read_text() if file_path.exists() else doc.get("summary", "")
        results.append(
            f"**{doc['title']}** (doc_id: {doc['id']}, relevance: {score:.0f})\n\n{content}"
        )
    if not results:
        for doc in docs[:max_results]:
            results.append(f"**{doc['title']}** (doc_id: {doc['id']})\n{doc.get('summary', '')}")
    return "\n\n---\n\n".join(results)


def _read_doc(doc_id: str) -> str:
    docs = _load_index()
    for doc in docs:
        if doc["id"] == doc_id:
            file_path = DOCS_ROOT / doc["file"]
            return file_path.read_text() if file_path.exists() else f"Doc not found: {doc_id}"
    available = [d["id"] for d in docs]
    return f"Unknown doc_id '{doc_id}'. Available: {available}"


# Tool definitions in Anthropic format (for autoresearch_loop.py)
TOOLS = [
    {
        "name": "search_docs",
        "description": (
            "Search the RingCentral documentation for content relevant to a query. "
            "Returns the most relevant documentation sections."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results to return (default 3)", "default": 3},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_doc",
        "description": "Read the full content of a specific documentation page by its doc_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "Document ID (e.g. authentication, rate-limits, webhooks, api-basics, sdks)",
                },
            },
            "required": ["doc_id"],
        },
    },
]

TOOL_FUNCTIONS = {
    "search_docs": _search_docs,
    "read_doc": _read_doc,
}


# ---------------------------------------------------------------------------
# Main entry point — Cursor SDK agent connected to the Mintlify docs MCP
# ---------------------------------------------------------------------------

def run(question: str, model: str = "composer-2.5", verbose: bool = False) -> dict:
    """Run the Mintlify-docs agent on a question.

    Spins up a Cursor SDK agent in an empty working directory (so it has no
    monorepo to read) and wires in the live Mintlify-hosted RingCentral docs
    MCP server. The agent answers using only the docs portal's search/read
    tools — the treatment condition for the benchmark.

    Returns:
        {answer: str, elapsed_s: float, response_length: int}
    """
    from cursor_sdk import (
        Agent,
        AgentOptions,
        HttpMcpServerConfig,
        LocalAgentOptions,
    )

    api_key = os.environ.get("CURSOR_API_KEY", "")

    t0 = time.time()
    answer = ""
    try:
        # Empty temp cwd: no local files to fall back on, forcing the agent to
        # rely on the Mintlify docs MCP. setting_sources=[] keeps it from
        # picking up the user's ambient MCP / project config.
        with tempfile.TemporaryDirectory() as tmpdir:
            with Agent.create(
                AgentOptions(
                    model=model,
                    api_key=api_key,
                    local=LocalAgentOptions(cwd=tmpdir, setting_sources=[]),
                    mcp_servers={
                        "ringcentral-docs": HttpMcpServerConfig(url=MCP_URL),
                    },
                )
            ) as agent:
                if verbose:
                    print(f"  [mintlify] agent created, MCP={MCP_URL}, sending question...")
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
