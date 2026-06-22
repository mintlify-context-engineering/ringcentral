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
    "the live RingCentral documentation portal via Mintlify MCP. Prefer the docs "
    "portal for official API/documentation facts, use local files when source, "
    "examples, package metadata, tests, or repository details are needed, and answer "
    "accurately and concisely.\n\nQuestion: "
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
