import abc
import subprocess

class AbstractCLIProvider(abc.ABC):
    @abc.abstractmethod
    def execute(self, prompt: str, log_cb, cwd: str = None) -> dict:
        pass
    
    @abc.abstractmethod
    def check_rate_limit(self, response: str) -> bool:
        pass

class ClaudeCLIProvider(AbstractCLIProvider):
    def __init__(self, model_name: str = None):
        self.model_name = model_name

    def execute(self, prompt: str, log_cb, cwd: str = None) -> dict:
        cmd = ['claude']
        # Use --model if a specific one is provided
        if self.model_name and self.model_name.lower() not in ['claude', '']:
            cmd.extend(['--model', self.model_name])
        cmd.extend(['-p', prompt])
        
        log_cb(f"EXEC CMD: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=cwd)
            if result.stdout: log_cb(f"STDOUT: {result.stdout.strip()[:300]}...")
            if result.stderr: log_cb(f"STDERR: {result.stderr.strip()[:300]}...")
            return {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}
        except Exception as e:
            log_cb(f"EXEC ERROR: {str(e)}")
            return {"stdout": f"Error executing Claude: {str(e)}", "stderr": str(e), "code": 1}

    def check_rate_limit(self, response: str) -> bool:
        resp = str(response).lower()
        return "limit" in resp or "rate" in resp or "quota" in resp

class GeminiCLIProvider(AbstractCLIProvider):
    def __init__(self, model_name: str = None):
        self.model_name = model_name

    def execute(self, prompt: str, log_cb, cwd: str = None) -> dict:
        cmd = ['gemini']
        if self.model_name and self.model_name.lower() not in ['gemini', '']:
            cmd.extend(['--model', self.model_name])
        cmd.extend(['-p', prompt])
        
        log_cb(f"EXEC CMD: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=cwd)
            if result.stdout: log_cb(f"STDOUT: {result.stdout.strip()[:300]}...")
            if result.stderr: log_cb(f"STDERR: {result.stderr.strip()[:300]}...")
            return {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}
        except Exception as e:
            log_cb(f"EXEC ERROR: {str(e)}")
            return {"stdout": f"Error executing Gemini: {str(e)}", "stderr": str(e), "code": 1}

    def check_rate_limit(self, response: str) -> bool:
        resp = str(response).lower()
        return "limit" in resp or "rate" in resp or "quota" in resp

class CopilotCLIProvider(AbstractCLIProvider):
    def __init__(self, model_name: str = None):
        self.model_name = model_name

    def execute(self, prompt: str, log_cb, cwd: str = None) -> dict:
        # Syntax: copilot -p "<prompt>" -s --model <modello>
        cmd = ['copilot', '-s', '--allow-all', '--yolo']
        if self.model_name:
            cmd.extend(['--model', self.model_name])
        cmd.extend(['-p', prompt])
        
        log_cb(f"EXEC CMD: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=cwd)
            if result.stdout: log_cb(f"STDOUT: {result.stdout.strip()[:300]}...")
            if result.stderr: log_cb(f"STDERR: {result.stderr.strip()[:300]}...")
            return {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}
        except Exception as e:
            log_cb(f"EXEC ERROR: {str(e)}")
            return {"stdout": f"Error executing Copilot: {str(e)}", "stderr": str(e), "code": 1}

    def check_rate_limit(self, response: str) -> bool:
        resp = str(response).lower()
        return "limit" in resp or "rate" in resp or "quota" in resp

class CLIProviderFactory:
    @staticmethod
    def get_provider(model_name: str) -> AbstractCLIProvider:
        # Handle new syntax "provider:model"
        if ":" in model_name:
            provider, model = model_name.split(":", 1)
            if provider == "copilot":
                return CopilotCLIProvider(model)
            if provider == "claude":
                return ClaudeCLIProvider(model)
            if provider == "gemini":
                return GeminiCLIProvider(model)

        m = model_name.lower()
        if "copilot" in m or "gpt-5" in m or "gpt-4" in m:
            return CopilotCLIProvider(model_name)
        elif "claude" in m or "opus" in m or "sonnet" in m or "haiku" in m:
            return ClaudeCLIProvider(model_name)
        elif "gemini" in m:
            return GeminiCLIProvider(model_name)
        return ClaudeCLIProvider(model_name)
