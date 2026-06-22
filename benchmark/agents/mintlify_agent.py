"""
Mintlify MCP agent — Condition B (treatment).

The run() function queries the live Mintlify search MCP server at
ringcentral.mintlify.app/mcp, representing what a developer / AI agent
experiences with a proper documentation portal: semantic search over
deployed, structured docs instead of 40+ raw repositories.

Module-level exports (TOOLS, TOOL_FUNCTIONS, _load_index, _score_doc, …)
are the local-file equivalents kept for autoresearch_loop.py compatibility.
"""

import json
import os
import re
import time
from pathlib import Path

import httpx

DOCS_ROOT = Path(__file__).parent.parent / "structured_docs"
MCP_URL = "https://ringcentral.mintlify.app/mcp"
MAX_TOOL_CALLS = 8

SYSTEM_PROMPT = (
    "You are an assistant helping developers use the RingCentral platform. "
    "You have access to the official RingCentral documentation via search and read tools. "
    "Search for relevant content, then answer accurately and concisely."
)

QUESTION_PREFIX = (
    "You are using the RingCentral documentation portal (powered by Mintlify). "
    "Use the search tools available to find documentation and answer the following question "
    "accurately and concisely.\n\nQuestion: "
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
# Mintlify MCP client (Streamable HTTP transport)
# ---------------------------------------------------------------------------

class _MCPClient:
    """Minimal MCP client over Streamable HTTP."""

    def __init__(self, url: str):
        self.url = url
        self.session_id: str | None = None
        self._req_id = 0
        self._http = httpx.Client(timeout=30.0)

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    def _post(self, method: str, params: dict) -> dict:
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params}
        resp = self._http.post(self.url, json=payload, headers=self._headers())
        resp.raise_for_status()
        if "Mcp-Session-Id" in resp.headers:
            self.session_id = resp.headers["Mcp-Session-Id"]
        ct = resp.headers.get("content-type", "")
        if "text/event-stream" in ct:
            return self._parse_sse(resp.text)
        return resp.json()

    def _notify(self, method: str, params: dict) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        try:
            self._http.post(self.url, json=payload, headers=self._headers())
        except Exception:
            pass

    @staticmethod
    def _parse_sse(text: str) -> dict:
        for line in text.splitlines():
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if "result" in data or "error" in data:
                        return data
                except json.JSONDecodeError:
                    pass
        return {}

    def initialize(self) -> None:
        self._post("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ringcentral-benchmark", "version": "1.0"},
        })
        self._notify("notifications/initialized", {})

    def list_tools(self) -> list[dict]:
        resp = self._post("tools/list", {})
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> str:
        resp = self._post("tools/call", {"name": name, "arguments": arguments})
        content = resp.get("result", {}).get("content", [])
        parts = [c["text"] for c in content if c.get("type") == "text"]
        return "\n".join(parts) if parts else str(resp.get("result", ""))

    def close(self) -> None:
        self._http.close()


def _mcp_tools_to_anthropic(mcp_tools: list[dict]) -> list[dict]:
    return [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("inputSchema", {"type": "object", "properties": {}}),
        }
        for t in mcp_tools
    ]


# ---------------------------------------------------------------------------
# Main entry point — uses live Mintlify MCP server
# ---------------------------------------------------------------------------

def run(question: str, model: str = "claude-haiku-4-5-20251001", verbose: bool = False) -> dict:
    """Run the Mintlify MCP agent on a question.

    Connects to the live Mintlify search MCP at ringcentral.mintlify.app/mcp,
    fetches available tools, and uses the Anthropic SDK to answer the question.

    Returns:
        {answer: str, elapsed_s: float, response_length: int}
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key)
    mcp = _MCPClient(MCP_URL)

    t0 = time.time()
    answer = ""
    try:
        mcp.initialize()
        mcp_tools = mcp.list_tools()
        tools = _mcp_tools_to_anthropic(mcp_tools)

        if verbose:
            print(f"  [mintlify] MCP ready — {len(tools)} tools: {[t['name'] for t in tools]}")

        messages = [{"role": "user", "content": QUESTION_PREFIX + question}]
        tool_call_count = 0

        for _ in range(MAX_TOOL_CALLS + 1):
            response = client.messages.create(
                model=model,
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                tools=tools or anthropic.NOT_GIVEN,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                answer = "".join(b.text for b in response.content if hasattr(b, "text"))
                break

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                tool_call_count += 1
                if verbose:
                    print(f"  [mintlify] → {block.name}({json.dumps(block.input)[:80]})")
                result = mcp.call_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

            if tool_call_count >= MAX_TOOL_CALLS:
                messages.append({"role": "user", "content": "Please provide your final answer now."})
                final = client.messages.create(
                    model=model, max_tokens=800, system=SYSTEM_PROMPT, messages=messages
                )
                answer = "".join(b.text for b in final.content if hasattr(b, "text"))
                break

    except Exception as e:
        answer = f"ERROR: {e}"
    finally:
        mcp.close()

    elapsed = time.time() - t0
    if verbose:
        print(f"  [mintlify] done in {elapsed:.1f}s, response_len={len(answer)}")

    return {
        "answer": answer.strip(),
        "elapsed_s": round(elapsed, 2),
        "response_length": len(answer),
    }
