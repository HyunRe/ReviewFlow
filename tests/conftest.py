import os

# pytest 실행 시 로컬/CI 환경에 상관없이 SQLite 인메모리 DB를 사용하도록 설정
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_HOST"] = "localhost"