from python.providers.abstract_cli_provider import AbstractCLIProvider
from python.providers.claude_cli_provider import ClaudeCLIProvider
from python.providers.gemini_cli_provider import GeminiCLIProvider
from python.providers.copilot_cli_provider import CopilotCLIProvider
from python.providers.antigravity_cli_provider import AntigravityCLIProvider
from python.providers.kiro_cli_provider import KiroCLIProvider

class CLIProviderFactory:
    @staticmethod
    def get_provider(model_name: str) -> AbstractCLIProvider:
        if ":" in model_name:
            provider, model = model_name.split(":", 1)
            if provider == "copilot":
                return CopilotCLIProvider(model)
            if provider == "claude":
                return ClaudeCLIProvider(model)
            if provider == "gemini":
                return GeminiCLIProvider(model)
            if provider == "antigravity":
                return AntigravityCLIProvider(model)
            if provider == "kiro" or provider == "kiro-cli":
                return KiroCLIProvider(model)

        m = model_name.lower()
        if "copilot" in m or "gpt-5" in m or "gpt-4" in m:
            return CopilotCLIProvider(model_name)
        elif "claude" in m or "opus" in m or "sonnet" in m or "haiku" in m:
            return ClaudeCLIProvider(model_name)
        elif "gemini" in m:
            return GeminiCLIProvider(model_name)
        elif "antigravity" in m:
            return AntigravityCLIProvider(model_name)
        elif "kiro" in m:
            return KiroCLIProvider(model_name)
        return ClaudeCLIProvider(model_name)
