from contextlib import asynccontextmanager
from fastapi import FastAPI
from mangum import Mangum

from src.infrastructure.persistence.database import init_db
from src.presentation.webhook_controller import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시점에 DB 초기화 실행 (import 시점 연결 방지)
    init_db()
    yield


app = FastAPI(title="ReviewFlow Agent", lifespan=lifespan)

# 라우터 및 컨트롤러 연결
app.include_router(webhook_router)

# AWS Lambda용 Mangum 핸들러
handler = Mangum(app)