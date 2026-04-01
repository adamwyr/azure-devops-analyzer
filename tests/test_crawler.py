import pytest
from unittest.mock import AsyncMock
from src.crawler import Crawler
from src.analyzers.base import BaseAnalyzer

class DummyAnalyzer(BaseAnalyzer):
    @property
    def name(self):
        return "Dummy"
        
    async def analyze(self, ado_client, project_id, repo_id, file_tree):
        if any('dummy' in f['path'] for f in file_tree):
            return [{"module_path": "/dummy", "is_api": True}]
        return []

@pytest.fixture
def crawler(mock_ado_client):
    analyzer = DummyAnalyzer()
    return Crawler(mock_ado_client, [analyzer])

@pytest.mark.asyncio
async def test_crawl_all(crawler, mock_ado_client):
    mock_ado_client.get_projects.return_value = [{"id": "p1", "name": "Project1"}]
    mock_ado_client.get_repositories.return_value = [{"id": "r1", "name": "Repo1"}, {"id": "r2", "name": "Repo2"}]
    
    # Setup repo1 to trigger dummy analyzer, repo2 to not
    async def get_tree_mock(project_id, repo_id):
        if repo_id == "r1":
             return [{"path": "dummy.txt"}]
        return [{"path": "empty.txt"}]
        
    mock_ado_client.get_file_tree.side_effect = get_tree_mock
    
    results = await crawler.crawl_all()
    
    assert "Project1" in results
    proj1 = results["Project1"]
    
    assert "Repo1" in proj1
    assert "Dummy" in proj1["Repo1"]
    assert len(proj1["Repo1"]["Dummy"]) == 1
    
    # Repo 2 should not exist because dummy analyzer returned []
    assert "Repo2" not in proj1
