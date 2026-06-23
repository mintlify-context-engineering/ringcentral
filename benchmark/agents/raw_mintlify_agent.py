"""
Hybrid source + Mintlify MCP agent — Condition D.

Gives the agent both the sanitized Raw + Markdown workspace and the live
Mintlify-hosted RingCentral docs MCP. This measures whether structured docs help
when the agent can still fall back to source files, examples, package metadata,
and repository-specific details.
"""

import os
import tempfile
import time
from pathlib import Path

from agents import context_metrics, openrouter_agent, raw_agent
from agents.mintlify_agent import MCP_URL

API_KEY = os.environ.get("CURSOR_API_KEY", "")

QUESTION_PREFIX = (
    "You are answering a RingCentral developer question with two information sources: "
    "a sanitized local RingCentral source workspace that includes Markdown docs and "
    "the live RingCentral documentation portal via Mintlify MCP.\n\n"
    "Routing rules:\n"
    "- For public API behavior, endpoint paths, auth flows, limits, current defaults, "
    "and developer how-to questions, prefer the Mintlify documentation portal.\n"
    "- For package names, versions, dependencies, peerDependencies, workspaces, build/test "
    "scripts, Jest config, Swift tools/platforms, source modules, tests, examples, and "
    "repo composition, use the local source workspace as the source of truth. Inspect the "
    "actual manifest/config/source files before answering; do not infer these details from docs.\n"
    "- When a question asks for a default, production URL, current endpoint, or base path, "
    "return the single current canonical value unless the question asks for historical variants.\n"
    "- If docs and source disagree, state which source you used for the specific fact.\n\n"
    "Answer accurately and concisely.\n\nQuestion: "
)


def run(
    question: str,
    model: str = "composer-2.5",
    verbose: bool = False,
    provider: str = "cursor",
) -> dict:
    """Run the hybrid Raw + Markdown plus Mintlify MCP agent on a question."""
    t0 = time.time()
    answer = ""
    error = None
    metrics = context_metrics.empty_metrics()

    try:
        with tempfile.TemporaryDirectory(prefix="rc-raw-mintlify-benchmark-") as tmpdir:
            workspace = Path(tmpdir)
            raw_agent._populate_workspace(workspace)

            if provider == "openrouter":
                if verbose:
                    print(f"  [raw+mintlify:openrouter] workspace={workspace}, MCP={MCP_URL}, sending question...")
                result = openrouter_agent.run_with_workspace_and_mcp(
                    prompt=QUESTION_PREFIX + question,
                    workspace=workspace,
                    model=model,
                    mcp_url=MCP_URL,
                    verbose=verbose,
                )
                answer = result["answer"]
                metrics = {k: v for k, v in result.items() if k != "answer"}
            elif provider == "cursor":
                from cursor_sdk import Agent, AgentOptions, HttpMcpServerConfig, LocalAgentOptions

                if verbose:
                    print(f"  [raw+mintlify] workspace={workspace}, MCP={MCP_URL}, sending question...")
                with Agent.create(
                    AgentOptions(
                        model=model,
                        api_key=API_KEY,
                        local=LocalAgentOptions(cwd=str(workspace), setting_sources=[]),
                        mcp_servers={"ringcentral-docs": HttpMcpServerConfig(url=MCP_URL)},
                    )
                ) as agent:
                    run_result = agent.send(QUESTION_PREFIX + question)
                    answer = run_result.text()
                    metrics = context_metrics.metrics_from_run(run_result, answer)
            else:
                raise ValueError(f"Unknown provider: {provider}")
    except Exception as e:
        error = str(e)
        answer = f"ERROR: {error}"

    elapsed = time.time() - t0
    if verbose:
        print(f"  [raw+mintlify] done in {elapsed:.1f}s, response_len={len(answer)}")

    return {
        "answer": answer.strip(),
        "elapsed_s": round(elapsed, 2),
        "response_length": len(answer),
        "ok": error is None,
        "error": error,
        **metrics,
    }
