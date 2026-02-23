"""
Coding agent loop.

Uses litellm for a unified interface across providers:
  - OpenAI:     model = "openai/gpt-4o"
  - Anthropic:  model = "anthropic/claude-sonnet-4-20250514"
  - Perplexity: model = "perplexity/sonar-pro"
  - Local GGUF: model = "openai/codellama"  + api_base = "http://localhost:8080/v1"
"""

from __future__ import annotations

import json
import sys
from typing import Any

import litellm

from .tools import TOOLS, TOOL_EXECUTORS

# Suppress litellm's own verbose logging by default
litellm.suppress_debug_info = True

SYSTEM_PROMPT = """\
You are a codebase exploration agent. You help users understand, navigate, and modify codebases.

Your capabilities:
- Read file contents to understand code
- Search for patterns across files using grep
- Find files using glob patterns
- Edit files by replacing specific strings

Guidelines:
- When exploring, start with glob to understand the structure
- Use grep to find specific patterns, functions, or variables
- Always read a file before editing it
- When editing, include enough context in oldString to make it unique
- Provide clear, concise responses about what you found or changed
- If you're unsure about something, ask for clarification\
"""

MAX_STEPS = 20


def _run_tool(name: str, arguments: str) -> str:
    """Look up and execute a tool by name, returning the result string."""
    executor = TOOL_EXECUTORS.get(name)
    if executor is None:
        return json.dumps({"success": False, "error": f"Unknown tool: {name}"})
    try:
        args = json.loads(arguments)
    except json.JSONDecodeError as exc:
        return json.dumps({"success": False, "error": f"Invalid JSON arguments: {exc}"})
    return executor(args)


def run_agent(
    prompt: str,
    *,
    model: str,
    api_base: str | None = None,
    api_key: str | None = None,
    verbose: bool = False,
) -> None:
    """
    Run the agent loop: send messages → receive tool calls → execute → repeat.
    Streams text output to stdout in real-time.
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    if verbose:
        print(f'[Agent] Starting with prompt: "{prompt}"\n')

    # Build common kwargs for litellm
    kwargs: dict[str, Any] = {
        "model": model,
        "tools": TOOLS,
        "stream": True,
    }
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    for step in range(1, MAX_STEPS + 1):
        kwargs["messages"] = messages

        # ── Streaming call ──────────────────────────────────────
        tool_calls_accum: dict[int, dict[str, str]] = {}  # index → {id, name, arguments}
        assistant_content = ""

        try:
            response = litellm.completion(**kwargs)
        except Exception as exc:
            print(f"\n[Error] LLM call failed: {exc}", file=sys.stderr)
            return

        for chunk in response:
            delta = chunk.choices[0].delta  # type: ignore[union-attr]

            # Stream text tokens
            if delta.content:
                sys.stdout.write(delta.content)
                sys.stdout.flush()
                assistant_content += delta.content

            # Accumulate tool calls across chunks
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_accum:
                        tool_calls_accum[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name or "",
                            "arguments": "",
                        }
                    if tc.id:
                        tool_calls_accum[idx]["id"] = tc.id
                    if tc.function.name:
                        tool_calls_accum[idx]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls_accum[idx]["arguments"] += tc.function.arguments

        # ── If no tool calls, we're done ────────────────────────
        if not tool_calls_accum:
            break

        # Build the assistant message with tool_calls for the history
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": assistant_content or None}
        assistant_msg["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            }
            for tc in tool_calls_accum.values()
        ]
        messages.append(assistant_msg)

        # ── Execute each tool call ──────────────────────────────
        for tc in tool_calls_accum.values():
            name = tc["name"]
            print(f"\n[calling {name}] {tc['arguments']}")

            result = _run_tool(name, tc["arguments"])

            if verbose:
                # Print a compact version of the result
                try:
                    parsed = json.loads(result)
                    summary = {k: v for k, v in parsed.items() if k != "content"}
                    print(f"[{name} done] {json.dumps(summary)}")
                except Exception:
                    print(f"[{name} done]")
            else:
                print(f"[{name} done]")

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })
    else:
        print(f"\n[Agent] Reached maximum steps ({MAX_STEPS}), stopping.")

    print()  # final newline
