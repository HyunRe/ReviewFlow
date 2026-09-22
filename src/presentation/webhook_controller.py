from fastapi import APIRouter, BackgroundTasks, Header
from src.presentation.dto import GitHubWebhookPayload
from src.application.review_service import ReviewService

router = APIRouter(prefix="/webhook", tags=["Webhook"])

@router.post("/github")
async def handle_github_webhook(
    payload: GitHubWebhookPayload,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None)
):
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": "Not a pull_request event"}

    if payload.action in ["opened", "synchronize"] and payload.pull_request:
        repo_name = payload.repository["full_name"]
        pr_id = payload.pull_request.number
        commit_sha = payload.pull_request.head["sha"]

        # 지연 로딩: 함수 내부에서 생성하거나 백그라운드 태스크 내부에서 서비스 인스턴스를 생성
        review_service = ReviewService()

        background_tasks.add_task(
            review_service.process_review,
            repo_name=repo_name,
            pr_id=pr_id,
            commit_sha=commit_sha
        )
        return {"status": "queued", "repo": repo_name, "pr_id": pr_id, "sha": commit_sha}

    return {"status": "ignored", "reason": f"Unsupported action: {payload.action}"}