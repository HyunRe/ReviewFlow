import uvicorn
from mangum import Mangum
from src.presentation.webhook_controller import app
from src.infrastructure.persistence.database import init_db

# DB 테이블 자동 생성 (Lambda Cold Start 시 1회 실행)
init_db()

# AWS Lambda 핸들러
handler = Mangum(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)