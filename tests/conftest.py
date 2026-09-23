import os

# pytest 실행 시 로컬/CI 환경에 상관없이 SQLite 인메모리 DB를 사용하도록 설정
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_HOST"] = "localhost"

# pytest 실행 시 boto3 클라이언트 초기화 에러 방지용 가상 AWS 환경변수 설정
os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-2"
os.environ["AWS_REGION"] = "ap-northeast-2"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"