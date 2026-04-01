import asyncio
import logging
from typing import List, Dict, Any
from src.ado_client import AdoClient
from src.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)

class Crawler:
    """Orchestrates the crawling of ADO projects, repos, and files."""
    def __init__(self, ado_client: AdoClient, analyzers: List[BaseAnalyzer]):
        self.client = ado_client
        self.analyzers = analyzers
    
    async def crawl_all(self) -> Dict[str, Any]:
        """
        Crawls the entire organization and returns a nested dictionary of results.
        Keys: project_name -> repository_name -> language -> list of module results
        """
        results = {}
        
        # 1. Get all projects
        logger.info("Fetching projects...")
        projects = await self.client.get_projects()
        logger.info(f"Found {len(projects)} projects.")
        
        # Fetch repos for all projects concurrently
        project_repo_tasks = [
            self.crawl_project(proj['id'], proj['name']) for proj in projects
        ]
        
        project_results_list = await asyncio.gather(*project_repo_tasks)
        
        for project_name, proj_res in project_results_list:
            if proj_res:
                 results[project_name] = proj_res
                 
        return results

    async def crawl_project(self, project_id: str, project_name: str) -> tuple[str, Dict]:
        logger.info(f"Fetching repos for project: {project_name}")
        repos = await self.client.get_repositories(project_id)
        
        repo_tasks = [
            self.crawl_repository(project_id, repo['id'], repo['name']) for repo in repos
        ]
        repo_results_list = await asyncio.gather(*repo_tasks)
        
        proj_res = {}
        for repo_name, rep_res in repo_results_list:
            if rep_res:
                proj_res[repo_name] = rep_res
                
        return project_name, proj_res
        
    async def crawl_repository(self, project_id: str, repo_id: str, repo_name: str) -> tuple[str, Dict]:
        logger.debug(f"Fetching file tree for repo: {repo_name}")
        file_tree = await self.client.get_file_tree(project_id, repo_id)
        
        if not file_tree:
            return repo_name, {}
            
        analyzer_tasks = [
            self.run_analyzer(analyzer, project_id, repo_id, repo_name, file_tree)
            for analyzer in self.analyzers
        ]
        
        analyzer_results = await asyncio.gather(*analyzer_tasks)
        
        rep_res = {}
        for analyzer_name, findings in analyzer_results:
            if findings:
                rep_res[analyzer_name] = findings
                
        return repo_name, rep_res

    async def run_analyzer(self, analyzer: BaseAnalyzer, project_id: str, repo_id: str, repo_name: str, file_tree: List[Dict]) -> tuple[str, List[Dict]]:
        try:
            findings = await analyzer.analyze(self.client, project_id, repo_id, file_tree)
            return analyzer.name, findings
        except Exception as e:
            logger.error(f"Error running analyzer {analyzer.name} on {repo_name}: {e}", exc_info=True)
            return analyzer.name, []
