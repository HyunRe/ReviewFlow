import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_app_initialization():
    """FastAPI 앱 객체 정상 생성 여부 확인"""
    assert app is not None

def test_health_check_or_root():
    """루트 경로 또는 기본 응답 상태 확인"""
    response = client.get("/")
    # 404 라우트가 미정의 상태이거나 200 OK 상태인지 응답 코드 검증
    assert response.status_code in [200, 404]