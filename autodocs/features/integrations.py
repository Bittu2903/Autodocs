import httpx
from typing import List, Dict, Any, Optional

class GitHubIntegration:
    """GitHub API integration"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=self.headers
            )
            return response.json()
    
    async def get_recent_commits(self, owner: str, repo: str, limit: int = 100) -> List[Dict]:
        """Get recent commits"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits",
                headers=self.headers,
                params={"per_page": limit}
            )
            return response.json()
    
    async def get_pull_requests(self, owner: str, repo: str, state: str = "all") -> List[Dict]:
        """Get pull requests"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                headers=self.headers,
                params={"state": state, "per_page": 50}
            )
            return response.json()
    
    async def get_pr_comments(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """Get PR comments and reviews"""
        async with httpx.AsyncClient() as client:
            comments = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers=self.headers
            )
            reviews = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                headers=self.headers
            )
            
            all_comments = comments.json() + reviews.json()
            return all_comments

class SlackIntegration:
    """Slack API integration"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://slack.com/api"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def get_channel_messages(self, channel_id: str, limit: int = 100) -> List[Dict]:
        """Get messages from a channel"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/conversations.history",
                headers=self.headers,
                params={"channel": channel_id, "limit": limit}
            )
            data = response.json()
            return data.get("messages", [])
    
    async def search_messages(self, query: str) -> List[Dict]:
        """Search for messages containing keywords"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/search.messages",
                headers=self.headers,
                params={"query": query}
            )
            data = response.json()
            return data.get("messages", {}).get("matches", [])