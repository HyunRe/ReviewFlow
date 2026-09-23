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