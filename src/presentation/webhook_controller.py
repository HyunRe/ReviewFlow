from fastapi import FastAPI, BackgroundTasks, Header
from src.presentation.dto import GitHubWebhookPayload
from src.application.review_service import ReviewService

app = FastAPI(title="ReviewFlow AI Agent")
review_service = ReviewService()

@app.post("/webhook/github")
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

        background_tasks.add_task(
            review_service.process_review,
            repo_name=repo_name,
            pr_id=pr_id,
            commit_sha=commit_sha
        )
        return {"status": "queued", "repo": repo_name, "pr_id": pr_id, "sha": commit_sha}

    return {"status": "ignored", "reason": f"Unsupported action: {payload.action}"}