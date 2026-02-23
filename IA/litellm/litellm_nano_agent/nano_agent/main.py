#!/usr/bin/env python3
"""
CLI entry point for the nano-agent.

Usage:
  python -m nano_agent "Trova tutti i file nella cartella"
  python -m nano_agent -v "Leggi il file agent.py e spiegamelo"
  python -m nano_agent -v "Nel file sum.py aggiungi una funzione Crea un file python che calcola la somma di due numeri"
  python -m nano_agent -v "Crea un file sum4.py python che calcola la somma di quattro numeri"

Environment variables (configured in .env):
    LLM_PROVIDER   - Provider name: local | openai | anthropic | perplexity | github_copilot
    LOCAL_BASE_URL  - Base URL for local server  (default: http://localhost:8080/v1)
    LOCAL_MODEL     - Model name for local server (default: local-model)
    OPENAI_API_KEY  - API key for OpenAI
    ANTHROPIC_API_KEY - API key for Anthropic
    PERPLEXITY_API_KEY - API key for Perplexity
    GITHUB_COPILOT_API_KEY - API key for GitHub Copilot (not needed if using GitHub Copilot provider)
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from .agent import run_agent

# Provider → (litellm model string, api_base override, env var for api_key)
_PROVIDER_MAP: dict[str, tuple[str, str | None, str | None]] = {
    "local":      ("openai/{model}",                 "{base_url}", None),
    "openai":     ("openai/{model}",                 None,         "OPENAI_API_KEY"),
    "anthropic":  ("anthropic/{model}",              None,         "ANTHROPIC_API_KEY"),
    "perplexity": ("perplexity/{model}",             None,         "PERPLEXITY_API_KEY"),
    "github_copilot": ("github_copilot/{model}", None,         "GITHUB_COPILOT_API_KEY"),
}

_DEFAULT_MODELS: dict[str, str] = {
    "local":      "local-model",
    "openai":     "gpt-4o",
    "anthropic":  "claude-sonnet-4-20250514",
    "perplexity": "sonar-pro",
    "github_copilot": "gpt-4",
}


def _resolve_provider() -> tuple[str, str | None, str | None]:
    """
    Read env vars and return (litellm_model, api_base, api_key).
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider not in _PROVIDER_MAP:
        sys.exit(
            f"Error: unknown LLM_PROVIDER='{provider}'. "
            f"Supported: {', '.join(_PROVIDER_MAP)}"
        )

    template, base_tpl, key_env = _PROVIDER_MAP[provider]

    # Determine model name
    model_name = os.getenv("LOCAL_MODEL") or os.getenv("LLM_MODEL") or _DEFAULT_MODELS[provider]
    litellm_model = template.format(model=model_name)

    # Determine api base
    api_base: str | None = None
    if base_tpl:
        raw_base = os.getenv("LOCAL_BASE_URL", "http://localhost:8080/v1")
        api_base = base_tpl.format(base_url=raw_base)

    # Determine api key
    api_key: str | None = None
    if provider == "local":
        api_key = "not-needed"
    elif key_env:
        api_key = os.getenv(key_env)
        if not api_key:
            sys.exit(f"Error: {key_env} not set. Add it to your .env file.")

    return litellm_model, api_base, api_key


def main() -> None:
    load_dotenv()  # load .env from cwd (or parent dirs)

    parser = argparse.ArgumentParser(
        prog="nano-agent",
        description="Mini coding agent – works with OpenAI, Anthropic, Perplexity, GitHubCopilot and local GGUF models",
    )
    parser.add_argument(
        "prompt",
        nargs="+",
        help="The prompt to send to the agent",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed tool call information",
    )
    args = parser.parse_args()
    prompt = " ".join(args.prompt)

    litellm_model, api_base, api_key = _resolve_provider()

    if args.verbose:
        print(f"[Config] model={litellm_model}  api_base={api_base}")

    run_agent(
        prompt,
        model=litellm_model,
        api_base=api_base,
        api_key=api_key,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
