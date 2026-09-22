from abc import ABC, abstractmethod

class AbstractReviewRepository(ABC):
    @abstractmethod
    def create_history(self, repo_name: str, pr_id: int, commit_sha: str) -> int:
        pass

    @abstractmethod
    def update_status(self, history_id: int, status: str, total_tokens: int = 0, cost: float = 0.0, summary: str = None, error: str = None):
        pass

class AbstractLLMClient(ABC):
    @abstractmethod
    def generate_review(self, prompt: str) -> str:
        pass