import os
from typing import Optional, cast
import redis

class RedisCacheManager:
    def __init__(self):
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        self.client = redis.Redis(host=host, port=port, db=0, decode_responses=True)

    def get_cached_review(self, commit_sha: str) -> Optional[str]:
        try:
            res = self.client.get(f"review:{commit_sha}")
            return cast(Optional[str], res)
        except Exception:
            return None

    #  이 메서드를 추가하세요
    def set_review_cache(self, commit_sha: str, summary: str, ex: int = 86400) -> None:
        """리뷰 결과를 Redis에 저장 (기본 TTL: 24시간)"""
        try:
            self.client.set(f"review:{commit_sha}", summary, ex=ex)
        except Exception as e:
            # Redis 저장 실패 시에도 전체 프로세스가 중단되지 않도록 예외 처리
            print(f"[REDIS WARN] Failed to set review cache: {e}")