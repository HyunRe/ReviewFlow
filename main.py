import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from mangum import Mangum

from src.infrastructure.persistence.database import init_db
from src.presentation.webhook_controller import router as webhook_router
from src.application.review_service import ReviewService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시점에 DB 초기화 실행 (import 시점 연결 방지)
    init_db()
    yield


app = FastAPI(title="ReviewFlow Agent", lifespan=lifespan, root_path="/default")

# 라우터 및 컨트롤러 연결
app.include_router(webhook_router)

# FastAPI / API Gateway용 Mangum 핸들러
mangum_handler = Mangum(app)


def handler(event, context):
    """
    AWS Lambda 엔트리포인트:
    1. 비동기 자가 호출(task_type: process_review)인 경우 -> ReviewService 직접 실행
    2. 일반 HTTP 웹훅 요청인 경우 -> Mangum(FastAPI) 전달
    """
    # 1. 비동기 백그라운드 작업 요청인지 확인
    if isinstance(event, dict) and event.get("task_type") == "process_review":
        repo_name = event.get("repo_name")
        pr_id = event.get("pr_id")
        commit_sha = event.get("commit_sha")

        # [타입 방어 및 유효성 검증]
        # pr_id가 str로 넘어올 가능성까지 대비해 int 변환 시도
        if isinstance(pr_id, str) and pr_id.isdigit():
            pr_id = int(pr_id)

        # 필수값 및 타입 가드 (이 조건문을 통과하면 IDE가 repo_name: str, pr_id: int, commit_sha: str 로 인식함)
        if not isinstance(repo_name, str) or not isinstance(pr_id, int) or not isinstance(commit_sha, str):
            return {"statusCode": 400, "body": "Invalid or missing parameters (repo_name, pr_id, commit_sha)"}

        # DB 연결 초기화
        init_db()

        # 리뷰 로직 실행 (asyncio.run으로 비동기 코루틴 실행)
        review_service = ReviewService()
        asyncio.run(
            review_service.process_review(
                repo_name=repo_name,
                pr_id=pr_id,
                commit_sha=commit_sha
            )
        )
        return {"statusCode": 200, "body": "Review process completed successfully"}

    # 2. 일반 API Gateway / HTTP 웹훅 요청 처리 (try-except 방어막 추가)
    try:
        return mangum_handler(event, context)
    except Exception as e:
        print(f"[ERROR] Webhook processing failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": f"Internal Server Error: {str(e)}"
        }