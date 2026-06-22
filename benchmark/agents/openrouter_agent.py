"""OpenRouter-backed benchmark helpers.

This module provides a small OpenAI-compatible tool loop for running the same
benchmark access layers without the Cursor SDK. It is intentionally limited to
read-only tools so the OpenRouter path can be compared with the existing Cursor
path while routing spend through OPENROUTER_API_KEY.
"""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import httpx

from agents import context_metrics

OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_TIMEOUT_S = 120
MAX_TOOL_CALL_ROUNDS = 8
MAX_TOOL_RESULT_CHARS = 20000
SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "benchmark",
    "results",
    "build",
    "coverage",
    "dist",
    ".next",
    "storybook-static",
}
BINARY_SUFFIXES = {
    ".aac",
    ".aiff",
    ".bmp",
    ".class",
    ".dll",
    ".exe",
    ".flac",
    ".gif",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lockb",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".pdf",
    ".png",
    ".so",
    ".wav",
    ".webm",
    ".webp",
    ".zip",
}


class OpenRouterError(RuntimeError):
    pass


def default_model() -> str:
    return os.environ.get("OPENROUTER_MODEL", "~openai/gpt-latest")


def default_judge_model() -> str:
    return os.environ.get("OPENROUTER_JUDGE_MODEL") or default_model()


def _api_key() -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY not set")
    return api_key


def _headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        "X-OpenRouter-Title": "RingCentral Context Engineering Benchmark",
    }
    referer = os.environ.get("OPENROUTER_HTTP_REFERER")
    if referer:
        headers["HTTP-Referer"] = referer
    return headers


def _chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=DEFAULT_TIMEOUT_S) as client:
        response = client.post(url, headers=_headers(), json=payload)
    if response.status_code >= 400:
        raise OpenRouterError(f"OpenRouter {response.status_code}: {response.text[:500]}")
    return response.json()


def _parse_sse_json_messages(text: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        raw = line.removeprefix("data:").strip()
        if not raw:
            continue
        messages.append(json.loads(raw))
    if not messages and text.strip():
        messages.append(json.loads(text))
    return messages


def _mcp_request(mcp_url: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=DEFAULT_TIMEOUT_S) as client:
        response = client.post(mcp_url, headers=headers, json=payload)
    if response.status_code == 202:
        return None
    if response.status_code >= 400:
        raise OpenRouterError(f"MCP {response.status_code}: {response.text[:500]}")

    messages = _parse_sse_json_messages(response.text)
    if not messages:
        return None
    message = messages[-1]
    if "error" in message:
        raise OpenRouterError(f"MCP error: {message['error']}")
    return message


def _usage_from_response(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage") or {}
    return {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "cost": float(usage.get("cost") or 0),
        "generation_ids": [response["id"]] if response.get("id") else [],
    }


def _merge_usage(total: dict[str, Any], response: dict[str, Any]) -> None:
    usage = _usage_from_response(response)
    total["prompt_tokens"] += usage["prompt_tokens"]
    total["completion_tokens"] += usage["completion_tokens"]
    total["total_tokens"] += usage["total_tokens"]
    total["cost"] += usage["cost"]
    total["generation_ids"].extend(usage["generation_ids"])


def _tool_payload(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def _mcp_tool_payload(tool: dict[str, Any]) -> dict[str, Any]:
    parameters = tool.get("inputSchema") or {"type": "object", "properties": {}}
    if parameters.get("type") != "object":
        parameters = {"type": "object", "properties": {}}
    parameters.setdefault("properties", {})
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description") or tool.get("title") or tool["name"],
            "parameters": parameters,
        },
    }


def _truncate(text: str, limit: int = MAX_TOOL_RESULT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[truncated {len(text) - limit} chars]"


def _safe_relpath(raw_path: str | None) -> Path:
    rel = Path(raw_path or ".")
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("path must be relative and may not contain '..'")
    return rel


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() not in BINARY_SUFFIXES


def _workspace_tools(workspace: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    def list_files(args: dict[str, Any]) -> str:
        rel = _safe_relpath(args.get("path"))
        max_results = min(int(args.get("max_results") or 200), 500)
        root = workspace / rel
        if not root.exists():
            return f"Path not found: {rel}"

        files: list[str] = []
        if root.is_file():
            files = [str(rel)]
        else:
            for current_root, dirs, names in os.walk(root, followlinks=True):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for name in names:
                    path = Path(current_root) / name
                    if not _is_text_file(path):
                        continue
                    try:
                        files.append(str(path.relative_to(workspace)))
                    except ValueError:
                        continue
                    if len(files) >= max_results:
                        break
                if len(files) >= max_results:
                    break
        return "\n".join(sorted(files)) or "(no files)"

    def find_files(args: dict[str, Any]) -> str:
        pattern = str(args.get("pattern") or "*")
        max_results = min(int(args.get("max_results") or 100), 300)
        matches: list[str] = []
        for current_root, dirs, names in os.walk(workspace, followlinks=True):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in names:
                path = Path(current_root) / name
                if not _is_text_file(path):
                    continue
                try:
                    rel = str(path.relative_to(workspace))
                except ValueError:
                    continue
                if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern) or pattern.lower() in rel.lower():
                    matches.append(rel)
                    if len(matches) >= max_results:
                        return "\n".join(sorted(matches))
        return "\n".join(sorted(matches)) or "(no matches)"

    def search_files(args: dict[str, Any]) -> str:
        query = str(args.get("query") or "").strip()
        if not query:
            return "query is required"
        rel = _safe_relpath(args.get("path"))
        max_results = min(int(args.get("max_results") or 80), 200)
        target = workspace / rel
        if not target.exists():
            return f"Path not found: {rel}"
        cmd = [
            "rg",
            "--follow",
            "--ignore-case",
            "--fixed-strings",
            "--line-number",
            "--no-heading",
            "--color",
            "never",
            "--glob",
            "!node_modules/**",
            "--glob",
            "!__pycache__/**",
            "--glob",
            "!*.lock",
            "--glob",
            "!*.png",
            "--glob",
            "!*.jpg",
            "--glob",
            "!*.jpeg",
            "--glob",
            "!*.gif",
            "--glob",
            "!*.pdf",
            query,
            str(target),
        ]
        try:
            proc = subprocess.run(cmd, cwd=workspace, text=True, capture_output=True, timeout=20)
        except FileNotFoundError:
            return "rg is not installed"
        except subprocess.TimeoutExpired:
            return "search timed out"
        lines = proc.stdout.splitlines()[:max_results]
        normalized: list[str] = []
        for line in lines:
            normalized.append(line.replace(str(workspace) + os.sep, ""))
        return "\n".join(normalized) or "(no matches)"

    def read_file(args: dict[str, Any]) -> str:
        rel = _safe_relpath(args.get("path"))
        start_line = max(int(args.get("start_line") or 1), 1)
        max_lines = min(max(int(args.get("max_lines") or 220), 1), 500)
        path = workspace / rel
        if not path.exists():
            return f"File not found: {rel}"
        if path.is_dir():
            return f"Path is a directory: {rel}"
        if not _is_text_file(path):
            return f"File appears to be binary or unsupported: {rel}"
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError as e:
            return f"Could not read {rel}: {e}"
        selected = lines[start_line - 1 : start_line - 1 + max_lines]
        numbered = [f"{i}: {line}" for i, line in enumerate(selected, start=start_line)]
        return _truncate("\n".join(numbered))

    tools = [
        _tool_payload(
            "list_files",
            "List text files under a relative path in the available workspace.",
            {
                "path": {"type": "string", "description": "Relative path to list, default '.'"},
                "max_results": {"type": "integer", "description": "Maximum files to return"},
            },
            [],
        ),
        _tool_payload(
            "find_files",
            "Find files by glob, filename substring, or relative path substring.",
            {
                "pattern": {"type": "string", "description": "Glob pattern or substring, e.g. package.json"},
                "max_results": {"type": "integer", "description": "Maximum matches to return"},
            },
            ["pattern"],
        ),
        _tool_payload(
            "search_files",
            "Search available text files for a literal string and return line matches.",
            {
                "query": {"type": "string", "description": "Literal string to search for"},
                "path": {"type": "string", "description": "Optional relative path to search within"},
                "max_results": {"type": "integer", "description": "Maximum matching lines to return"},
            },
            ["query"],
        ),
        _tool_payload(
            "read_file",
            "Read a slice of a text file with line numbers.",
            {
                "path": {"type": "string", "description": "Relative file path"},
                "start_line": {"type": "integer", "description": "1-based starting line"},
                "max_lines": {"type": "integer", "description": "Maximum lines to read"},
            },
            ["path"],
        ),
    ]
    return tools, {
        "list_files": list_files,
        "find_files": find_files,
        "search_files": search_files,
        "read_file": read_file,
    }


def _mcp_result_to_text(result: dict[str, Any]) -> str:
    content = result.get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(json.dumps(item, ensure_ascii=False))
        return "\n\n".join(part for part in parts if part)
    return json.dumps(result, ensure_ascii=False)


def _mcp_tools(mcp_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    init = _mcp_request(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "ringcentral-context-benchmark-openrouter",
                    "version": "1.0.0",
                },
            },
        },
    )
    if not init or "result" not in init:
        raise OpenRouterError("MCP initialize returned no result")
    _mcp_request(mcp_url, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    listed = _mcp_request(mcp_url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    raw_tools = (((listed or {}).get("result") or {}).get("tools")) or []
    if not raw_tools:
        capabilities_tools = (((init or {}).get("result") or {}).get("capabilities") or {}).get("tools")
        raw_tools = list(capabilities_tools.values()) if isinstance(capabilities_tools, dict) else []
    if not raw_tools:
        raise OpenRouterError("MCP server did not advertise any tools")

    functions = {}
    for raw_tool in raw_tools:
        name = raw_tool["name"]

        def call_tool(args: dict[str, Any], tool_name: str = name) -> str:
            response = _mcp_request(
                mcp_url,
                {
                    "jsonrpc": "2.0",
                    "id": 100,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": args},
                },
            )
            result = ((response or {}).get("result")) or {}
            return _mcp_result_to_text(result)

        functions[name] = call_tool

    return [_mcp_tool_payload(tool) for tool in raw_tools], functions


def run_with_workspace(
    *,
    prompt: str,
    workspace: Path,
    model: str,
    verbose: bool = False,
) -> dict[str, Any]:
    tools, tool_functions = _workspace_tools(workspace)
    return _run_tool_loop(prompt=prompt, model=model, tools=tools, tool_functions=tool_functions, verbose=verbose)


def run_with_mcp(
    *,
    prompt: str,
    model: str,
    mcp_url: str,
    verbose: bool = False,
) -> dict[str, Any]:
    tools, tool_functions = _mcp_tools(mcp_url)
    return _run_tool_loop(
        prompt=prompt,
        model=model,
        tools=tools,
        tool_functions=tool_functions,
        verbose=verbose,
        system_prompt=(
            "You are a read-only benchmark agent. Use the live RingCentral Mintlify MCP "
            "tools to search and read the documentation portal, then answer accurately "
            "and concisely. Do not mention tool names unless needed for the answer."
        ),
    )


def run_with_workspace_and_mcp(
    *,
    prompt: str,
    workspace: Path,
    model: str,
    mcp_url: str,
    verbose: bool = False,
) -> dict[str, Any]:
    workspace_tools, workspace_functions = _workspace_tools(workspace)
    mcp_tools, mcp_functions = _mcp_tools(mcp_url)
    return _run_tool_loop(
        prompt=prompt,
        model=model,
        tools=[*workspace_tools, *mcp_tools],
        tool_functions={**workspace_functions, **mcp_functions},
        verbose=verbose,
        system_prompt=(
            "You are a read-only benchmark agent. You have both a sanitized local "
            "RingCentral source workspace and the live RingCentral Mintlify MCP docs "
            "tools. Prefer the documentation portal for API/documentation facts, use "
            "local files when source, examples, package metadata, tests, or repository "
            "details are needed, then answer accurately and concisely."
        ),
    )


def run_plain_json(prompt: str, *, model: str) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    response = _chat_completion(payload)
    message = response["choices"][0]["message"]
    return (message.get("content") or "").strip(), _usage_from_response(response)


def _run_tool_loop(
    *,
    prompt: str,
    model: str,
    tools: list[dict[str, Any]],
    tool_functions: dict[str, Any],
    verbose: bool = False,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": system_prompt
            or (
                "You are a read-only benchmark agent. Use tools to inspect the available "
                "information layer, then answer accurately and concisely. Do not mention "
                "tool names unless needed for the answer."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0.0, "generation_ids": []}
    tool_calls: list[dict[str, Any]] = []
    answer = ""
    ok = True
    error = None

    for round_index in range(MAX_TOOL_CALL_ROUNDS + 1):
        response = _chat_completion(
            {
                "model": model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0,
            }
        )
        _merge_usage(usage_total, response)
        message = response["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        if not calls:
            answer = (message.get("content") or "").strip()
            break

        messages.append(message)
        if verbose:
            names = ", ".join(call.get("function", {}).get("name", "unknown") for call in calls)
            print(f"  [openrouter] tool round {round_index + 1}: {names}")

        for call in calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            try:
                result = tool_functions[name](args)
            except Exception as e:
                result = f"Tool error: {e}"
            result = _truncate(str(result))
            result_bytes = len(json.dumps(result))
            tool_calls.append({"type": name, "bytes": result_bytes})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "name": name,
                    "content": result,
                }
            )
    else:
        ok = False
        error = "OpenRouter tool loop exhausted before a final answer."
        answer = f"ERROR: {error}"

    tool_breakdown: dict[str, int] = {}
    for call in tool_calls:
        tool_breakdown[call["type"]] = tool_breakdown.get(call["type"], 0) + call["bytes"]

    has_native_usage = usage_total["total_tokens"] > 0
    total_tokens = usage_total["total_tokens"]
    if not has_native_usage:
        total_tokens = context_metrics.estimate_tokens(sum(tool_breakdown.values()) + len(answer))

    return {
        "answer": answer.strip(),
        "ok": ok,
        "error": error,
        "tool_result_bytes": sum(tool_breakdown.values()),
        "tool_calls": len(tool_calls),
        "tool_breakdown": tool_breakdown,
        "context_tokens_est": usage_total["prompt_tokens"],
        "output_tokens_est": usage_total["completion_tokens"],
        "total_tokens_est": total_tokens,
        "prompt_tokens": usage_total["prompt_tokens"],
        "completion_tokens": usage_total["completion_tokens"],
        "total_tokens": total_tokens,
        "token_source": "openrouter_native_usage" if has_native_usage else "estimate_fallback",
        "token_count_is_estimate": not has_native_usage,
        "openrouter_prompt_tokens": usage_total["prompt_tokens"],
        "openrouter_completion_tokens": usage_total["completion_tokens"],
        "openrouter_total_tokens": total_tokens,
        "openrouter_cost": round(usage_total["cost"], 8),
        "openrouter_generation_ids": usage_total["generation_ids"],
    }
