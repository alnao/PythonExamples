from python.providers.abstract_cli_provider import AbstractCLIProvider
import subprocess

# Poiché la CLI di agy (alla versione 1.0.4) non supporta flag a riga di comando per forzare il 
# modello su singola chiamata, il modello effettivamente utilizzato sarà quello attivo o configurato 
# a livello globale nel client agy (es. tramite la TUI o in ~/.gemini/antigravity-cli/settings.json). 
# Censirli in .env ti servirà per la corretta visualizzazione e selezione formale all'interno dell'interfaccia dell'orchestrator.


class AntigravityCLIProvider(AbstractCLIProvider):
    def __init__(self, model_name: str = None):
        self.model_name = model_name

    def execute(self, prompt: str, log_cb, cwd: str = None) -> dict:
        # Using agy CLI (version 1.0.4) instead of legacy gemini-cli.
        # agy uses the model active in settings/TUI and runs non-interactively with --dangerously-skip-permissions -p.
        cmd = ['agy', '--dangerously-skip-permissions', '-p', prompt]
        
        log_cb(f"EXEC CMD: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=cwd)
            if result.stdout: log_cb(f"STDOUT: {result.stdout.strip()[:300]}...")
            if result.stderr: log_cb(f"STDERR: {result.stderr.strip()[:300]}...")
            return {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}
        except Exception as e:
            log_cb(f"EXEC ERROR: {str(e)}")
            return {"stdout": f"Error executing Gemini via agy: {str(e)}", "stderr": str(e), "code": 1}

    def check_rate_limit(self, response: str) -> bool:
        resp = str(response).lower()
        keywords = [
            "rate limit", 
            "rate_limit", 
            "quota exceeded", 
            "quota_exceeded", 
            "exhausted", 
            "429", 
            "out of credits", 
            "insufficient credits", 
            "limit exceeded"
        ]
        return any(k in resp for k in keywords)
