import abc

class AbstractCLIProvider(abc.ABC):
    @abc.abstractmethod
    def execute(self, prompt: str, log_cb, cwd: str = None) -> dict:
        pass
    
    @abc.abstractmethod
    def check_rate_limit(self, response: str) -> bool:
        pass
