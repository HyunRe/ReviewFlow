import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app, handler

client = TestClient(app)


def test_app_initialization():
    """FastAPI 앱 객체 정상 생성 여부 확인"""
    assert app is not None


def test_health_check_or_root():
    """루트 경로 또는 기본 응답 상태 확인"""
    response = client.get("/")
    # 404 라우트가 미정의 상태이거나 200 OK 상태인지 응답 코드 검증
    assert response.status_code in [200, 404]


@patch("main.ReviewService")
@patch("main.init_db")
def test_handler_background_process_review_event(mock_init_db, mock_review_service):
    """Lambda 핸들러: 비동기 자가 호출(task_type: process_review) 이벤트 분기 테스트"""
    # Given: 백그라운드 리뷰 작업을 수행하는 Lambda Event 데이터
    event = {
        "task_type": "process_review",
        "repo_name": "owner/repo",
        "pr_id": 1,
        "commit_sha": "abc1234"
    }
    context = {}

    # Mock ReviewService 인스턴스 설정
    mock_service_instance = MagicMock()
    mock_review_service.return_value = mock_service_instance

    # When: handler 실행
    response = handler(event, context)

    # Then: DB 초기화 및 ReviewService 실행 검증
    mock_init_db.assert_called_once()
    mock_review_service.assert_called_once()
    mock_service_instance.process_review.assert_called_once_with(
        repo_name="owner/repo",
        pr_id=1,
        commit_sha="abc1234"
    )
    assert response["statusCode"] == 200
    assert response["body"] == "Review process completed successfully"


@patch("main.mangum_handler")
def test_handler_http_request_routing(mock_mangum_handler):
    """Lambda 핸들러: 일반 HTTP 웹훅 요청이 Mangum으로 정상 프록시되는지 테스트"""
    # Given: API Gateway HTTP 요청 Event
    event = {
        "httpMethod": "POST",
        "path": "/webhook/github",
        "headers": {"x-github-event": "ping"}
    }
    context = {}
    mock_mangum_handler.return_value = {"statusCode": 200, "body": '{"status":"success"}'}

    # When: handler 실행
    response = handler(event, context)

    # Then: Mangum 핸들러로 전달되었는지 검증
    mock_mangum_handler.assert_called_once_with(event, context)
    assert response["statusCode"] == 200