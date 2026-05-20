from python.providers.abstract_cli_provider import AbstractCLIProvider
import subprocess

class ClaudeCLIProvider(AbstractCLIProvider):
    def __init__(self, model_name: str = None):
        self.model_name = model_name

    def execute(self, prompt: str, log_cb, cwd: str = None) -> dict:
        cmd = ['claude']
        # Use --model if a specific one is provided
        if self.model_name and self.model_name.lower() not in ['claude', '']:
            cmd.extend(['--model', self.model_name])
        cmd.extend(['-w', '-p', prompt])
        
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
        keywords = [
            #"rate limit", 
            "rate_limit", 
            #"quota exceeded", 
            "quota_exceeded", 
            #"exhausted", 
            #"429", 
            #"out of credits", 
            "insufficient credits", 
            #"limit exceeded"
        ]
        return any(k in resp for k in keywords)
