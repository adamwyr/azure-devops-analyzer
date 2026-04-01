import pytest
from aioresponses import aioresponses
from src.ado_client import AdoClient
import asyncio
import aiohttp

@pytest.fixture
def mock_resp():
    with aioresponses() as m:
        yield m

@pytest.mark.asyncio
async def test_get_projects_success(mock_resp):
    mock_resp.get(
        "https://dev.azure.com/testorg/_apis/projects?api-version=7.1", 
        payload={"value": [{"id": "1", "name": "proj1"}]}
    )
    
    async with AdoClient("https://dev.azure.com/testorg", "pat") as client:
        projects = await client.get_projects()
        
    assert len(projects) == 1
    assert projects[0]['name'] == 'proj1'

@pytest.mark.asyncio
async def test_resiliency_backoff_success(mock_resp):
    # Setup the mock to fail with 429 twice, then succeed on the third attempt
    # We will set backoff factor to a very small number for speedy tests
    url = "https://dev.azure.com/testorg/p1/_apis/git/repositories?api-version=7.1"
    
    mock_resp.get(url, status=429, payload={"error": "Too Many Requests"})
    mock_resp.get(url, status=429, payload={"error": "Too Many Requests"})
    mock_resp.get(url, status=200, payload={"value": [{"name": "repo1"}]})
    
    async with AdoClient("https://dev.azure.com/testorg", "pat", max_retries=3, backoff_factor=0.01) as client:
        repos = await client.get_repositories("p1")
        
    assert len(repos) == 1
    assert repos[0]['name'] == 'repo1'

@pytest.mark.asyncio
async def test_resiliency_max_retries_exceeded(mock_resp):
    url = "https://dev.azure.com/testorg/p1/_apis/git/repositories?api-version=7.1"
    
    # Send 4 failures, when max_retries is 3
    mock_resp.get(url, status=503, payload={"error": "Service Unavailable"})
    mock_resp.get(url, status=503, payload={"error": "Service Unavailable"})
    mock_resp.get(url, status=503, payload={"error": "Service Unavailable"})
    mock_resp.get(url, status=503, payload={"error": "Service Unavailable"})
    
    async with AdoClient("https://dev.azure.com/testorg", "pat", max_retries=3, backoff_factor=0.01) as client:
        repos = await client.get_repositories("p1")
        
    assert repos == []

@pytest.mark.asyncio
async def test_get_file_tree(mock_resp):
    url = "https://dev.azure.com/testorg/p1/_apis/git/repositories/r1/items?api-version=7.1&recursionLevel=Full"
    mock_resp.get(url, payload={
        "value": [
            {"path": "folder", "isFolder": True},
            {"path": "folder/file.py", "isFolder": False}
        ]
    })
    
    async with AdoClient("https://dev.azure.com/testorg", "pat") as client:
        tree = await client.get_file_tree("p1", "r1")
        
    # Should filter out folders
    assert len(tree) == 1
    assert tree[0]['path'] == "folder/file.py"
