from src.application.review_graph import review_graph
from src.infrastructure.cache.redis_client import RedisCacheManager
from src.infrastructure.clients.github_client import GitHubClient
from src.infrastructure.persistence.database import ReviewRepository


class ReviewService:
    def __init__(self):
        self.redis_cache = RedisCacheManager()
        self.github_client = GitHubClient()

    async def process_review(self, repo_name: str, pr_id: int, commit_sha: str):
        # 1. PostgreSQL DB에 시작 상태(PENDING) 기록
        history_id = ReviewRepository.create_history(repo_name, pr_id, commit_sha)

        try:
            # 2. Redis 캐시 확인 (Commit SHA)
            cached_summary = self.redis_cache.get_cached_review(commit_sha)
            if cached_summary:
                ReviewRepository.update_status(history_id, status="SUCCESS", summary=cached_summary)
                await self.github_client.post_comment(repo_name, pr_id, f"*(Cached Review)*\n\n{cached_summary}")
                return

            # 3. GitHub에서 Raw Diff 추출
            raw_diff = await self.github_client.get_pr_diff(repo_name, pr_id)
            ReviewRepository.update_status(history_id, status="IN_PROGRESS")

            # 4. LangGraph 실행
            state = {
                "review_history_id": history_id,
                "pr_id": pr_id,
                "repo_name": repo_name,
                "commit_sha": commit_sha,
                "raw_diff": raw_diff,
                "filtered_diff": "",
                "file_list": [],
                "has_security_risk": False,
                "has_performance_risk": False,
                "security_review": None,
                "performance_review": None,
                "style_review": None,
                "final_summary": "",
                "total_tokens": 0,
                "estimated_cost": 0.0
            }

            result = review_graph.invoke(state)
            final_summary = result.get("final_summary", "")

            # 5. GitHub PR 댓글 게시
            if final_summary:
                await self.github_client.post_comment(repo_name, pr_id, final_summary)

        except Exception as e:
            ReviewRepository.update_status(history_id, status="FAILED", error=str(e))
            raise e