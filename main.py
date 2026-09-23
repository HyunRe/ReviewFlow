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

        # DB 연결 초기화
        init_db()

        # 리뷰 로직 실행 (최대 Lambda 타임아웃 시간까지 수행)
        review_service = ReviewService()
        review_service.process_review(
            repo_name=repo_name,
            pr_id=pr_id,
            commit_sha=commit_sha
        )
        return {"statusCode": 200, "body": "Review process completed successfully"}

    # 2. 일반 API Gateway / HTTP 웹훅 요청 처리
    return mangum_handler(event, context)