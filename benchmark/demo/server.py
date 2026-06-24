from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import unquote

import httpx

BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BENCHMARK_ROOT.parent
STATIC_ROOT = Path(__file__).resolve().parent / "static"
RC_LOGO = REPO_ROOT / "docs/logo/ringcentral.png"

sys.path.insert(0, str(BENCHMARK_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(BENCHMARK_ROOT / ".env")
except ImportError:
    pass

from agents import raw_agent
from agents.mintlify_agent import MCP_URL
from agents.openrouter_agent import (
    DEFAULT_TIMEOUT_S,
    MAX_TOOL_CALL_ROUNDS,
    OpenRouterError,
    _headers,
    _mcp_tools,
    _tool_payload,
    _truncate,
    _workspace_tools,
)
from agents.context_metrics import estimate_tokens

DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MAX_PREVIEW_CHARS = 1800

Emit = Callable[[str, dict[str, Any]], None]

# The MCP tool list is static for the lifetime of the server, but discovering it
# costs three sequential round-trips to the remote Mintlify endpoint
# (initialize -> notifications/initialized -> tools/list). Doing that on every
# request adds fixed latency to each "With MCP" run, so cache it per URL.
_MCP_TOOLS_CACHE: dict[str, tuple[list[dict[str, Any]], dict[str, Any]]] = {}


def _cached_mcp_tools(mcp_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cached = _MCP_TOOLS_CACHE.get(mcp_url)
    if cached is None:
        cached = _mcp_tools(mcp_url)
        _MCP_TOOLS_CACHE[mcp_url] = cached
    return cached


def _chat_stream(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    url = f"{OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=DEFAULT_TIMEOUT_S) as client:
        with client.stream("POST", url, headers=_headers(), json=payload) as response:
            if response.status_code >= 400:
                body = response.read().decode("utf-8", errors="replace")
                raise OpenRouterError(f"OpenRouter {response.status_code}: {body[:500]}")

            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line.removeprefix("data:").strip()
                if not raw or raw == "[DONE]":
                    continue
                yield json.loads(raw)


def _merge_usage(total: dict[str, Any], chunk: dict[str, Any]) -> None:
    usage = chunk.get("usage") or {}
    if not usage:
        return
    total["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
    total["completion_tokens"] += int(usage.get("completion_tokens") or 0)
    total["total_tokens"] += int(usage.get("total_tokens") or 0)
    total["cost"] += float(usage.get("cost") or 0)


def _usage_payload(
    usage_total: dict[str, Any],
    *,
    output_chars: int,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    tool_result_bytes = sum(call["bytes"] for call in tool_calls)
    tool_breakdown: dict[str, int] = {}
    for call in tool_calls:
        tool_breakdown[call["type"]] = tool_breakdown.get(call["type"], 0) + call["bytes"]

    has_native_usage = usage_total["total_tokens"] > 0
    if has_native_usage:
        prompt_tokens = usage_total["prompt_tokens"]
        completion_tokens = usage_total["completion_tokens"]
        total_tokens = usage_total["total_tokens"]
        token_source = "openrouter_native_usage"
    else:
        prompt_tokens = estimate_tokens(tool_result_bytes)
        completion_tokens = estimate_tokens(output_chars)
        total_tokens = prompt_tokens + completion_tokens
        token_source = "estimate_while_streaming"

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "token_source": token_source,
        "cost": round(usage_total["cost"], 8),
        "tool_calls": len(tool_calls),
        "tool_result_bytes": tool_result_bytes,
        "tool_breakdown": tool_breakdown,
    }


def _normalize_tool_calls(call_acc: dict[int, dict[str, Any]], round_index: int) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for index in sorted(call_acc):
        call = call_acc[index]
        call_id = call.get("id") or f"call_{round_index}_{index}"
        function = call.get("function") or {}
        calls.append(
            {
                "id": call_id,
                "type": call.get("type") or "function",
                "function": {
                    "name": function.get("name") or "",
                    "arguments": function.get("arguments") or "{}",
                },
            }
        )
    return calls


def _run_tool_loop_stream(
    *,
    prompt: str,
    model: str,
    tools: list[dict[str, Any]],
    tool_functions: dict[str, Any],
    system_prompt: str,
    emit: Emit,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0.0}
    tool_calls: list[dict[str, Any]] = []
    answer_parts: list[str] = []
    generation_ids: set[str] = set()

    def emit_usage() -> None:
        emit(
            "usage",
            _usage_payload(usage_total, output_chars=sum(len(part) for part in answer_parts), tool_calls=tool_calls),
        )

    for round_index in range(MAX_TOOL_CALL_ROUNDS + 1):
        is_final_round = round_index == MAX_TOOL_CALL_ROUNDS
        if is_final_round:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You can no longer call tools. Using only the information gathered above, "
                        "answer the original question now. Be concrete and concise."
                    ),
                }
            )

        emit(
            "status",
            {
                "message": "Writing final answer" if is_final_round else "Thinking",
                "round": round_index + 1,
            },
        )
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        # On the final round the model is forbidden from calling tools, so there
        # is no reason to pay to re-send the (large, MCP-inflated) tool schema.
        if not is_final_round:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        call_acc: dict[int, dict[str, Any]] = {}
        round_content: list[str] = []
        for chunk in _chat_stream(payload):
            if chunk.get("id"):
                generation_ids.add(chunk["id"])
            _merge_usage(usage_total, chunk)
            if chunk.get("usage"):
                emit_usage()

            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                content = delta.get("content") or ""
                if content:
                    round_content.append(content)
                    answer_parts.append(content)
                    emit("content", {"text": content})
                    emit_usage()

                for streamed_call in delta.get("tool_calls") or []:
                    index = int(streamed_call.get("index") or 0)
                    call = call_acc.setdefault(
                        index,
                        {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                    )
                    if streamed_call.get("id") and not call["id"]:
                        call["id"] = streamed_call["id"]
                    if streamed_call.get("type"):
                        call["type"] = streamed_call["type"]
                    function_delta = streamed_call.get("function") or {}
                    if function_delta.get("name"):
                        call["function"]["name"] += function_delta["name"]
                    if function_delta.get("arguments"):
                        call["function"]["arguments"] += function_delta["arguments"]

        calls = _normalize_tool_calls(call_acc, round_index)
        if not calls:
            final_answer = "".join(answer_parts).strip()
            return {
                "answer": final_answer,
                "ok": True,
                "error": None,
                "openrouter_generation_ids": sorted(generation_ids),
                **_usage_payload(usage_total, output_chars=len(final_answer), tool_calls=tool_calls),
            }

        if is_final_round:
            raise OpenRouterError("OpenRouter returned tool calls during the final no-tools round.")

        messages.append(
            {
                "role": "assistant",
                "content": "".join(round_content) or None,
                "tool_calls": calls,
            }
        )

        for call in calls:
            fn = call.get("function") or {}
            name = fn.get("name") or ""
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}

            emit(
                "tool_call",
                {
                    "name": name,
                    "arguments": args,
                    "round": round_index + 1,
                },
            )
            try:
                result = tool_functions[name](args)
            except Exception as exc:
                result = f"Tool error: {exc}"
            result = _truncate(str(result))
            result_bytes = len(json.dumps(result))
            tool_calls.append({"type": name, "bytes": result_bytes})
            emit(
                "tool_result",
                {
                    "name": name,
                    "bytes": result_bytes,
                    "preview": result[:MAX_PREVIEW_CHARS],
                },
            )
            emit_usage()
            messages.append({"role": "tool", "tool_call_id": call["id"], "name": name, "content": result})

    raise OpenRouterError("Tool loop exhausted before a final answer.")


def _raw_tools() -> tuple[tempfile.TemporaryDirectory[str], list[dict[str, Any]], dict[str, Any]]:
    tempdir = tempfile.TemporaryDirectory(prefix="rc-demo-raw-")
    workspace = Path(tempdir.name)
    raw_agent._populate_workspace(workspace)
    tools, functions = _workspace_tools(workspace)
    return tempdir, tools, functions


def _demo_prompt(user_prompt: str, mode: str) -> str:
    if mode == "raw":
        return (
            "Use the local RingCentral monorepo tools to answer this developer question. "
            "Do not use MCP or external documentation. Include exact package names, commands, "
            "endpoints, status codes, and file-backed details when they matter.\n\n"
            f"Question: {user_prompt}"
        )
    return (
        "Use the RingCentral Mintlify MCP documentation tools together with the local monorepo "
        "tools to answer this developer question. Prefer official documentation facts, and back "
        "them with local source when helpful. Include exact package names, commands, endpoints, "
        "status codes, and header names when they matter.\n\n"
        f"Question: {user_prompt}"
    )


def stream_demo_run(*, prompt: str, mode: str, model: str, emit: Emit) -> dict[str, Any]:
    if mode not in {"raw", "mcp"}:
        raise ValueError("mode must be 'raw' or 'mcp'")
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise OpenRouterError("OPENROUTER_API_KEY is not set. Add it to benchmark/.env.")

    started = time.time()
    emit("status", {"message": "Preparing tools", "round": 0})
    tempdir: tempfile.TemporaryDirectory[str] | None = None
    try:
        if mode == "raw":
            tempdir, tools, functions = _raw_tools()
            system_prompt = (
                "You are a read-only RingCentral source agent. Use the local file tools to inspect "
                "the sanitized repository and answer accurately. Do not mention tools unless the "
                "tool evidence is relevant."
            )
        else:
            tempdir, workspace_tools, workspace_functions = _raw_tools()
            mcp_tools, mcp_functions = _cached_mcp_tools(MCP_URL)
            tools = [*mcp_tools, *workspace_tools]
            functions = {**workspace_functions, **mcp_functions}
            system_prompt = (
                "You are a read-only RingCentral docs agent. You have the live Mintlify MCP tools "
                "for the documentation portal and local file tools over a sanitized copy of the "
                "RingCentral monorepo. Prefer the documentation portal for API/documentation facts, "
                "and use the local files for source, examples, package metadata, tests, or "
                "repository details. Then answer accurately. Do not mention tools unless the tool "
                "evidence is relevant."
            )

        emit(
            "ready",
            {
                "mode": mode,
                "model": model,
                "tools": [tool["function"]["name"] for tool in tools],
                "mcp_url": MCP_URL if mode == "mcp" else None,
            },
        )
        result = _run_tool_loop_stream(
            prompt=_demo_prompt(prompt, mode),
            model=model,
            tools=tools,
            tool_functions=functions,
            system_prompt=system_prompt,
            emit=emit,
        )
        result["elapsed_s"] = round(time.time() - started, 2)
        return result
    finally:
        if tempdir is not None:
            tempdir.cleanup()


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "RingCentralMcpDemo/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write(f"[demo] {self.address_string()} - {fmt % args}\n")

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse_headers(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._send_file(STATIC_ROOT / "index.html")
            return
        if self.path == "/api/config":
            self._send_json(
                {
                    "default_model": DEFAULT_MODEL,
                    "mcp_url": MCP_URL,
                    "has_openrouter_key": bool(os.environ.get("OPENROUTER_API_KEY")),
                }
            )
            return
        if self.path == "/assets/rc-logo.png":
            self._send_file(RC_LOGO)
            return
        if self.path.startswith("/static/"):
            rel = Path(unquote(self.path.removeprefix("/static/")))
            if rel.is_absolute() or ".." in rel.parts:
                self.send_error(400)
                return
            self._send_file(STATIC_ROOT / rel)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/api/run":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            prompt = str(payload.get("prompt") or "").strip()
            mode = str(payload.get("mode") or "").strip()
            model = str(payload.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
            if not prompt:
                raise ValueError("Prompt is required.")
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        self._send_sse_headers()

        def emit(event: str, data: dict[str, Any]) -> None:
            body = json.dumps(data, ensure_ascii=False)
            self.wfile.write(f"event: {event}\n".encode("utf-8"))
            for line in body.splitlines() or ["{}"]:
                self.wfile.write(f"data: {line}\n".encode("utf-8"))
            self.wfile.write(b"\n")
            self.wfile.flush()

        try:
            result = stream_demo_run(prompt=prompt, mode=mode, model=model, emit=emit)
            emit("done", result)
        except BrokenPipeError:
            return
        except Exception as exc:
            try:
                emit("error", {"message": str(exc)})
            except BrokenPipeError:
                return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RingCentral MCP side-by-side demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    server.daemon_threads = True
    print(f"RingCentral MCP demo running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()
