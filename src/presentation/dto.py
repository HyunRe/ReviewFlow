from pydantic import BaseModel
from typing import Optional, Dict, Any

class GitHubPullRequest(BaseModel):

    number: int
    head: Dict[str, Any]

class GitHubWebhookPayload(BaseModel):
    # 🔥 요 부분을 Optional[str] = None 으로 바꿔주셔야 ping 이벤트(action 없음)를 받습니다!
    action: Optional[str] = None
    pull_request: Optional[GitHubPullRequest] = None
    repository: Dict[str, Any]