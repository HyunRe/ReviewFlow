import os
from typing import Optional, Union
import redis

class RedisCacheManager:
    def __init__(self):
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        self.client = redis.Redis(host=host, port=port, db=0, decode_responses=True)

    def get_cached_review(self, commit_sha: str) -> Optional[Union[str, bytes]]:
        try:
            return self.client.get(f"review:{commit_sha}")
        except Exception:
            return None

    def set_review_cache(self, commit_sha: str, summary: str, ttl_seconds: int = 86400):
        try:
            self.client.setex(f"review:{commit_sha}", ttl_seconds, summary)
        except Exception:
            pass