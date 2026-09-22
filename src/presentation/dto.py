from pydantic import BaseModel
from typing import Optional, Dict, Any

class GitHubPullRequest(BaseModel):
    number: int
    head: Dict[str, Any]

class GitHubWebhookPayload(BaseModel):
    action: str
    pull_request: Optional[GitHubPullRequest] = None
    repository: Dict[str, Any]