import os
import json
import boto3
from fastapi import APIRouter, Header, HTTPException, status
from src.presentation.dto import GitHubWebhookPayload

router = APIRouter(prefix="/webhook", tags=["Webhook"])

# AWS Lambda 클라이언트 생성
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
lambda_client = boto3.client("lambda", region_name=AWS_REGION)

# 백그라운드 작업을 수행할 Worker Lambda 함수명 (환경 변수 또는 기본값)
WORKER_LAMBDA_NAME = os.getenv("WORKER_LAMBDA_NAME", "reviewflow-agent")


@router.post("/github")
async def handle_github_webhook(
    payload: GitHubWebhookPayload,
    x_github_event: str = Header(None)
):
    # 1. GitHub 연결 확인용 ping 이벤트 처리
    if x_github_event == "ping":
        return {"status": "success", "message": "pong"}

    # 2. PR 이벤트가 아닌 경우 무시
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": "Not a pull_request event"}

    # 3. Target 액션(opened, synchronize) 처리
    if payload.action in ["opened", "synchronize"] and payload.pull_request:
        repo_name = payload.repository["full_name"]
        pr_id = payload.pull_request.number
        commit_sha = payload.pull_request.head["sha"]

        # Worker Lambda에 전달할 이벤트 페이로드 구성
        worker_payload = {
            "task_type": "process_review",
            "repo_name": repo_name,
            "pr_id": pr_id,
            "commit_sha": commit_sha,
        }

        try:
            # InvocationType='Event' 옵션으로 비동기 호출 (응답을 기다리지 않고 즉시 리턴)
            lambda_client.invoke(
                FunctionName=WORKER_LAMBDA_NAME,
                InvocationType="Event",
                Payload=json.dumps(worker_payload),
            )
        except Exception as e:
            # Lambda 트리거 실패 시 예외 처리
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to trigger worker lambda: {str(e)}",
            )

        # 4. GitHub 측에 즉시 200 OK 응답 반환 (타임아웃 방지)
        return {
            "status": "queued",
            "repo": repo_name,
            "pr_id": pr_id,
            "sha": commit_sha,
        }

    return {"status": "ignored", "reason": f"Unsupported action: {payload.action}"}