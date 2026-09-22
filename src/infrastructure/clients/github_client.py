import os
import httpx

class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def get_pr_diff(self, repo_name: str, pr_id: int) -> str:
        url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_id}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers)
            res.raise_for_status()
            return res.text

    async def post_comment(self, repo_name: str, pr_id: int, body: str):
        url = f"https://api.github.com/repos/{repo_name}/issues/{pr_id}/comments"
        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=self.headers, json={"body": body})
            res.raise_for_status()