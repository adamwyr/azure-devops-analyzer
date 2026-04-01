import aiohttp
import asyncio
import base64
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class AdoClient:
    """Async client for Azure DevOps REST API with resiliency mechanisms."""
    def __init__(self, org_url: str, pat: str, max_retries: int = 3, backoff_factor: float = 1.0):
        # Ensure the org url does not end with a slash
        self.org_url = org_url.rstrip('/')
        self.pat = pat
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Build Authorization header
        b64_pat = base64.b64encode(f":{self.pat}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {b64_pat}",
            "Accept": "application/json"
        }

    async def __aenter__(self):
        # We use a connection pool to avoid opening too many connections simultaneously
        connector = aiohttp.TCPConnector(limit_per_host=20)
        self.session = aiohttp.ClientSession(connector=connector, headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _get(self, url: str, params: Optional[Dict[str, Any]] = None, return_json: bool = True) -> Any:
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with AdoClient(...) as client:'")
        
        retry_statuses = {429, 500, 502, 503, 504}
        attempt = 0
        
        while attempt <= self.max_retries:
            try:
                async with self.session.get(url, params=params) as response:
                    # Check if we should retry based on status code
                    if response.status in retry_statuses and attempt < self.max_retries:
                        sleep_time = self.backoff_factor * (2 ** attempt)
                        logger.warning(f"Request {url} returned HTTP {response.status}. Retrying in {sleep_time}s (Attempt {attempt + 1}/{self.max_retries})...")
                        await asyncio.sleep(sleep_time)
                        attempt += 1
                        continue

                    if response.status != 200:
                        logger.error(f"Error fetching {url}: {response.status} {await response.text()}")
                        response.raise_for_status()
                    
                    if return_json:
                        return await response.json()
                    else:
                        return await response.text()
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                # Handle connection errors and timeouts with retries as well
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    logger.warning(f"Request {url} encountered {type(e).__name__}: {e}. Retrying in {sleep_time}s (Attempt {attempt + 1}/{self.max_retries})...")
                    await asyncio.sleep(sleep_time)
                    attempt += 1
                else:
                    logger.error(f"Request {url} failed completely after {self.max_retries} retries due to {e}.")
                    raise
                    
        raise Exception(f"Failed to fetch {url} after {self.max_retries} retries.")

    async def get_projects(self) -> List[Dict]:
        """Fetch all projects from the organization."""
        url = f"{self.org_url}/_apis/projects"
        params = {"api-version": "7.1"}
        data = await self._get(url, params=params)
        return data.get("value", [])

    async def get_repositories(self, project_id: str) -> List[Dict]:
        """Fetch all repositories within a given project."""
        url = f"{self.org_url}/{project_id}/_apis/git/repositories"
        params = {"api-version": "7.1"}
        try:
            data = await self._get(url, params=params)
            return data.get("value", [])
        except aiohttp.ClientResponseError as e:
            logger.warning(f"Could not load repositories for project {project_id}: {e}")
            return []

    async def get_file_tree(self, project_id: str, repository_id: str) -> List[Dict]:
        """Fetch the recursive file tree for the default branch of a repository."""
        url = f"{self.org_url}/{project_id}/_apis/git/repositories/{repository_id}/items"
        params = {
            "recursionLevel": "Full",
            "api-version": "7.1"
        }
        try:
            data = await self._get(url, params=params)
            # Filter out folders so we just return files
            items = data.get("value", [])
            return [item for item in items if not item.get("isFolder", False)]
        except aiohttp.ClientResponseError as e:
            logger.warning(f"Could not load items for repo {repository_id}: {e}")
            return []

    async def get_file_content(self, project_id: str, repository_id: str, file_path: str) -> str:
        """Fetch the text content of a single file."""
        url = f"{self.org_url}/{project_id}/_apis/git/repositories/{repository_id}/items"
        params = {
            "path": file_path,
            "$format": "text",
            "api-version": "7.1"
        }
        try:
            return await self._get(url, params=params, return_json=False)
        except aiohttp.ClientResponseError as e:
            logger.warning(f"Could not get content of {file_path} in {repository_id}: {e}")
            return ""
